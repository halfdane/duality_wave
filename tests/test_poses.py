"""The poses and the colours of the part groups."""

import colorsys
from types import SimpleNamespace

import pytest
from build123d import Box, Plane, Pos, mirror

from duality_wave.builders.parts import GHOST_ALPHA, GROUPS, SIDE_TINT, alpha, colour, side_parts
from duality_wave.builders.poses import EXPLODE_STEP, exploded, pose_scene, transported
from tests.builds import PARTS

DIMS = SimpleNamespace(right_side_offset=200.0, above_z=9.0)


def hls(hex_colour: str):
    return colorsys.rgb_to_hls(*(int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)))


def test_the_transport_turns_a_point_of_the_right_half_to_its_mirror_image_above_the_left_half():
    probe = Pos(170, 12, 3) * Box(2, 4, 6)
    moved = transported(probe, DIMS).bounding_box()
    expected = Pos(DIMS.right_side_offset - 170, 12, 2 * DIMS.above_z - 3) * Box(2, 4, 6)
    for got, want in zip((moved.min, moved.max), (expected.bounding_box().min, expected.bounding_box().max)):
        assert tuple(got) == pytest.approx(tuple(want), abs=1e-6)


def test_a_mirrored_right_half_lies_on_the_left_half_when_transported():
    left = Pos(30, 10, 2) * Box(5, 8, 4)
    right = mirror(left, about=Plane.YZ.offset(DIMS.right_side_offset / 2))
    flipped = transported(right, DIMS).bounding_box()
    # the left half mirrored at z = above_z
    below = left.bounding_box()
    assert flipped.min.X == pytest.approx(below.min.X)
    assert flipped.max.X == pytest.approx(below.max.X)
    assert flipped.min.Y == pytest.approx(below.min.Y)
    assert flipped.min.Z == pytest.approx(2 * DIMS.above_z - below.max.Z)
    assert flipped.max.Z == pytest.approx(2 * DIMS.above_z - below.min.Z)


def test_the_transport_is_a_pure_move_that_keeps_the_volume():
    box = Pos(150, 3, 1) * Box(3, 5, 7)
    assert transported(box, DIMS).volume == pytest.approx(box.volume)


def test_each_group_drops_by_its_level_times_the_step():
    parts = {name: Box(1, 1, 1) for name in GROUPS}
    for step in (EXPLODE_STEP, 10.0):
        for name, shape in exploded(parts, step).items():
            assert shape.center().Z == pytest.approx(-GROUPS[name].level * step)


def test_the_layers_of_the_exploded_view_follow_the_stack_from_top_to_bottom():
    levels = {name: group.level for name, group in GROUPS.items()}
    assert levels["keywell"] < levels["keyplate"] < levels["bottom"] < levels["screws"]
    assert levels["keyplate"] == levels["switches"] == levels["keycaps"]
    assert levels["magnets"] < levels["keyplate"]


@pytest.mark.parametrize("group", list(GROUPS))
def test_the_right_half_has_a_slightly_different_tint_of_the_same_colour(group):
    left, right = colour(group, "left"), colour(group, "right")
    assert left == GROUPS[group].color
    assert len(right) == 7 and right.startswith("#")
    (hue_left, light_left, _), (hue_right, light_right, _) = hls(left), hls(right)
    assert right != left
    assert abs(light_left - light_right) == pytest.approx(SIDE_TINT, abs=0.02)
    if 0.1 < light_left < 0.9:
        assert abs(hue_left - hue_right) < 0.02


def test_an_unknown_pose_is_refused():
    with pytest.raises(ValueError):
        pose_scene(None, "upside_down")


@pytest.mark.integration
def test_every_part_of_a_half_has_a_registered_group(full):
    assert set(side_parts(full.left)) == set(GROUPS)
    assert set(side_parts(full.right)) == set(GROUPS)


@pytest.mark.integration
def test_the_quiet_case_has_no_accessories_to_pose(quiet):
    case, _ = quiet
    with pytest.raises(ValueError):
        pose_scene(case, "assembled")


@pytest.mark.integration
def test_the_assembled_pose_keeps_both_halves_where_they_are(full):
    scene = pose_scene(full, "assembled")
    assert scene["keywell_left"].bounding_box().min.X == pytest.approx(full.left.keywell.bounding_box().min.X)
    assert scene["keywell_right"].bounding_box().max.X == pytest.approx(full.right.keywell.bounding_box().max.X)
    assert {name.rsplit("_", 1)[1] for name in scene} == {"left", "right"}


@pytest.mark.integration
def test_the_transport_pose_leaves_the_left_half_and_flips_the_right_half_onto_it(full):
    scene = pose_scene(full, "transport")
    left, right = full.left.keywell.bounding_box(), scene["keywell_right"].bounding_box()
    assert scene["keywell_left"].bounding_box().min.X == pytest.approx(left.min.X)
    assert right.min.X == pytest.approx(left.min.X, abs=1e-3)
    assert right.max.X == pytest.approx(left.max.X, abs=1e-3)
    # the keywell tops meet
    assert right.min.Z == pytest.approx(left.max.Z, abs=1e-3)
    assert left.max.Z == pytest.approx(full.ctx.dims.above_z, abs=1e-3)


@pytest.mark.integration
def test_the_exploded_pose_shows_only_the_left_half_with_the_bottom_below_the_keywell(full):
    scene = pose_scene(full, "exploded")
    assert all(name.endswith("_left") for name in scene)
    assert scene["keywell_left"].bounding_box().max.Z == pytest.approx(full.left.keywell.bounding_box().max.Z)
    assert scene["bottom_left"].bounding_box().max.Z < scene["keywell_left"].bounding_box().min.Z


def overlap_volume(first, second, tolerance=1e-6) -> float:
    """The volume that two shapes share. The bounding boxes decide first, so that shapes that cannot meet cost nothing."""
    a, b = first.bounding_box(), second.bounding_box()
    if any(
        getattr(a.min, axis) >= getattr(b.max, axis) - tolerance or getattr(b.min, axis) >= getattr(a.max, axis) - tolerance
        for axis in "XYZ"
    ):
        return 0.0
    shared = first & second
    return sum(solid.volume for solid in shared.solids()) if shared else 0.0


def collisions(scene: dict) -> dict:
    left = {name: shape for name, shape in scene.items() if name.endswith("_left")}
    right = {name: shape for name, shape in scene.items() if name.endswith("_right")}
    found = {}
    for a, first in left.items():
        for b, second in right.items():
            volume = overlap_volume(first, second)
            if volume >= 1e-6:
                found[(a, b)] = volume
    return found


@pytest.mark.integration
def test_no_part_of_one_half_overlaps_a_part_of_the_other_in_the_transport_position(full):  # R-35
    scene = pose_scene(full, "transport")
    assert len(scene) == 2 * len(GROUPS)
    assert collisions(scene) == {}


@pytest.mark.integration
def test_the_collision_test_notices_a_half_that_sinks_into_the_other(full):  # R-35
    scene = pose_scene(full, "transport")
    # a sideways offset as well, because two identical shapes on top of each other confuse the boolean operation
    scene["keywell_right"] = scene["keywell_right"].moved(Pos(0.3, 0, -0.5))
    assert ("keywell_left", "keywell_right") in collisions(scene)


def test_only_the_printed_case_parts_are_see_through_and_only_in_the_ghost_style():
    assert {name for name, group in GROUPS.items() if group.shell} == set(PARTS)
    for name, group in GROUPS.items():
        assert alpha(name) == 1.0
        assert alpha(name, ghost=True) == (GHOST_ALPHA if group.shell else 1.0)
    assert 0 < GHOST_ALPHA < 1
