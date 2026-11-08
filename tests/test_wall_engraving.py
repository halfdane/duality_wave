"""R-34."""

from dataclasses import replace

import pytest
from build123d import Vector

from duality_wave.builders.keywell import build_keywell
from duality_wave.builders.side import Side
from duality_wave.builders.thumb_cut import ThumbCutSpec
from duality_wave.builders.wall_engraving import (
    emblem_height, emblem_z, engrave_emblem, find_wall_spot)
from duality_wave.models.space_invader import PATTERN, SpaceInvader
from tests.builds import make_context

PIXELS = sum(map(sum, PATTERN))


@pytest.fixture(scope="module")
def ctx():
    return make_context()


@pytest.fixture(scope="module")
def blank(ctx):
    return build_keywell(ctx)


@pytest.fixture(scope="module")
def spot(ctx):
    return find_wall_spot(ctx.outline.sketch)


def local_bounds(shape, plane):
    """The bounding box of a shape in the coordinates of the wall plane: x along the wall, y up, z out of the wall."""
    points = [plane.to_local_coords(Vector(v.X, v.Y, v.Z)) for v in shape.vertices()]
    xs, ys, zs = zip(*((p.X, p.Y, p.Z) for p in points))
    return (min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs))


@pytest.mark.parametrize("compact", [False, True])
def test_the_spot_is_on_a_straight_wall_that_faces_the_front(compact):  # R-34
    ctx = make_context(compact)
    spot = find_wall_spot(ctx.outline.sketch)
    assert spot.outward.Y < -0.9
    outer = ctx.outline.sketch.faces()[0].outer_wire()
    assert outer.distance_to(spot.origin) < 1e-6


def test_the_wall_is_wider_than_the_invader(ctx, spot):  # R-34
    width = SpaceInvader.columns * ctx.dims.print_profile.snap_up(ctx.dims.print_profile.engraving_pitch)
    wall = max(e.length for e in ctx.outline.sketch.faces()[0].outer_wire().edges() if abs(e.position_at(0.5).X - spot.origin.X) < 1e-6)
    assert wall >= width + 2 * ctx.dims.print_profile.min_wall


def test_the_right_spot_is_the_left_spot_mirrored(ctx):  # R-34
    left = Side.left(ctx)
    right = Side.right(ctx, left)
    offset = ctx.dims.right_side_offset
    assert right.emblem_spot.origin.X == pytest.approx(offset - left.emblem_spot.origin.X)
    assert right.emblem_spot.origin.Y == pytest.approx(left.emblem_spot.origin.Y)
    assert right.emblem_spot.outward.X == pytest.approx(-left.emblem_spot.outward.X)
    assert (left.emblem, right.emblem) == ("symbol", "invader")


def test_the_emblem_ends_its_rows_on_layer_boundaries_and_clears_the_rim_chamfers(ctx):  # R-34
    dims, profile = ctx.dims, ctx.dims.print_profile
    half = emblem_height(profile) / 2
    top, bottom = emblem_z(dims) + half, emblem_z(dims) - half
    for edge in (top, bottom):
        layers = (dims.above_z - edge) / profile.layer_height
        assert layers == pytest.approx(round(layers), abs=1e-6)
    margin = ThumbCutSpec().rim_chamfer
    assert top <= dims.above_z - margin
    assert bottom >= -dims.below_z + margin


@pytest.mark.parametrize("name", ["symbol", "invader"])
def test_the_pocket_is_in_the_wall_and_as_deep_as_asked(ctx, blank, spot, name):  # R-34
    dims, profile = ctx.dims, ctx.dims.print_profile
    engraved = engrave_emblem(blank, dims, spot, name)
    assert engraved.is_valid and len(engraved.solids()) == 1
    removed = blank.cut(engraved)
    assert removed.volume > 1
    (_, _), (y0, y1), (z0, z1) = local_bounds(removed, spot.plane(emblem_z(dims)))
    assert z1 == pytest.approx(0, abs=1e-6)
    assert z0 == pytest.approx(-profile.engraving_depth, abs=1e-6)
    half = emblem_height(profile) / 2
    assert y0 >= -half - 1e-6 and y1 <= half + 1e-6


def test_the_pixels_are_one_line_apart(ctx):  # R-34
    profile = ctx.dims.print_profile
    pitch = profile.snap_up(profile.engraving_pitch)
    pixels = SpaceInvader(pitch, profile.engraving_gap).sketch.faces()
    assert len(pixels) == PIXELS
    assert all(face.area == pytest.approx((pitch - profile.line_width) ** 2) for face in pixels)


@pytest.mark.parametrize("slope", [True, False])
def test_the_roof_slopes_at_45_degrees(ctx, blank, spot, slope):  # R-34
    dims, profile = ctx.dims, ctx.dims.print_profile
    dims = type("Dims", (), {"print_profile": replace(profile, engraving_roof_slope=slope),
                             "above_z": dims.above_z, "below_z": dims.below_z, "snap_z": dims.snap_z})()
    removed = blank.cut(engrave_emblem(blank, dims, spot, "invader"))
    side = profile.snap_up(profile.engraving_pitch) - profile.engraving_gap
    depth = profile.engraving_depth
    straight = side * side * depth
    wedge = 0.5 * depth * depth * side
    expected = PIXELS * (straight - (wedge if slope else 0))
    assert removed.volume == pytest.approx(expected, rel=1e-3)


def test_the_wall_behind_a_pocket_keeps_the_minimum_wall(ctx, blank, spot):  # R-34
    dims, profile = ctx.dims, ctx.dims.print_profile
    engraved = engrave_emblem(blank, dims, spot, "invader")
    plane = spot.plane(emblem_z(dims))
    behind = profile.engraving_depth + profile.min_wall
    assert engraved.is_inside(plane.from_local_coords(Vector(0, 0, -behind)))
    assert not engraved.is_inside(plane.from_local_coords(Vector(0, 0, 0.05)))
