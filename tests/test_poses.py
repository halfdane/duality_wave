"""The transport position: the right half lies upside down on the left half."""

from types import SimpleNamespace

import pytest
from build123d import Box, Plane, Pos, mirror

from duality_wave.builders.parts import GROUPS
from duality_wave.builders.poses import pose_scene, transported
from tests.geometry import overlap_volume, solids_with_boxes

DIMS = SimpleNamespace(right_side_offset=200.0, above_z=9.0)


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


def collisions(scene: dict) -> dict:
    parts = {name: solids_with_boxes(shape) for name, shape in scene.items()}
    left = [name for name in scene if name.endswith("_left")]
    right = [name for name in scene if name.endswith("_right")]
    found = {}
    for a in left:
        for b in right:
            volume = overlap_volume(parts[a], parts[b])
            if volume >= 1e-6:
                found[(a, b)] = volume
    return found


@pytest.mark.integration
def test_no_part_of_one_half_overlaps_a_part_of_the_other_in_the_transport_position(full):  # R-35
    scene = pose_scene(full, "transport")
    assert len(scene) == 2 * len(GROUPS)
    assert collisions(scene) == {}


def test_the_collision_test_finds_parts_that_overlap_and_ignores_parts_that_only_touch():  # R-35
    scene = {
        "keywell_left": Box(10, 10, 10),
        "keywell_right": Pos(0.3, 0, 9) * Box(10, 10, 10),
        "bottom_right": Pos(0, 0, 10) * Box(10, 10, 10),
    }
    assert set(collisions(scene)) == {("keywell_left", "keywell_right")}
