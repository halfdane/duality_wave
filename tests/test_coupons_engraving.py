import pytest
from build123d import Vector

from duality_wave.builders.wall_engraving import emblem_z
from duality_wave.coupons import BED_SIZE, create_wiring_coupon_parts
from duality_wave.coupons_engraving import (
    MARGIN, engraving_coupon_slabs, wall_engraving_coupon)
from duality_wave.models.space_invader import PATTERN, SpaceInvader
from tests.builds import make_context

SMALL_PRINT_BED = 180
NO_GAP_ONLY = (0.0,)


@pytest.fixture(scope="module")
def ctx():
    return make_context()


def pixel_center(ctx, row: int, column: int) -> tuple[float, float]:
    """The center of a pixel of the first invader in coupon coordinates (x, z).

    The coupon is printed like the keywell, so the top row of an emblem is next to the bed.
    """
    dims = ctx.dims
    pitch = dims.print_profile.snap_up(dims.print_profile.engraving_pitch)
    x = MARGIN + SpaceInvader.columns * pitch / 2 + (column - (SpaceInvader.columns - 1) / 2) * pitch
    middle = dims.above_z + dims.below_z - (emblem_z(dims) + dims.below_z)
    return x, middle - ((SpaceInvader.rows - 1) / 2 - row) * pitch


def test_the_roof_is_the_side_that_prints_last_and_slopes_when_asked(ctx):
    profile = ctx.dims.print_profile
    depth = profile.engraving_depth
    row = SpaceInvader.rows - 1
    column = PATTERN[row].index(1)
    x, z = pixel_center(ctx, row, column)
    pitch = profile.snap_up(profile.engraving_pitch)
    # with gap 0 the pixel fills one pitch. Look just below its upper end, which prints last.
    roof = z + pitch / 2 - 0.1
    sloped = wall_engraving_coupon(ctx.dims, profile, lines=1, roof_slope=True, gaps=NO_GAP_ONLY)
    straight = wall_engraving_coupon(ctx.dims, profile, lines=1, roof_slope=False, gaps=NO_GAP_ONLY)
    assert not sloped.is_inside(Vector(x, -0.05, roof))
    assert sloped.is_inside(Vector(x, -depth + 0.05, roof))
    assert not straight.is_inside(Vector(x, -depth + 0.05, roof))


@pytest.mark.integration
def test_the_wiring_plate_has_a_slab_for_every_depth_and_roof_and_fits_on_a_small_bed(ctx):
    slabs = engraving_coupon_slabs(ctx.dims)
    assert len(slabs) == 4
    assert all(slab.is_valid and len(slab.solids()) == 1 for slab in slabs.values())
    parts = create_wiring_coupon_parts(ctx.dims, extra=slabs)
    assert set(slabs) < set(parts)
    boxes = [part.bounding_box() for part in parts.values()]
    assert max(max(box.max.X, box.max.Y) for box in boxes) <= BED_SIZE < SMALL_PRINT_BED
    assert all(box.min.Z == pytest.approx(0, abs=1e-6) for box in boxes)
    for index, a in enumerate(boxes):
        for b in boxes[index + 1:]:
            assert (a.max.X + 5 <= b.min.X or b.max.X + 5 <= a.min.X
                    or a.max.Y + 5 <= b.min.Y or b.max.Y + 5 <= a.min.Y)
