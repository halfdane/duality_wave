import pytest
from build123d import Vector

from duality_wave.builders.wall_engraving import emblem_z
from duality_wave.coupons_engraving import MARGIN, wall_engraving_coupon
from duality_wave.models.space_invader import PATTERN, SpaceInvader
from tests.builds import make_context

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
