"""R-18."""

import pytest

from tests.builds import make_inputs


@pytest.mark.parametrize("compact", [False, True])
def test_the_z_levels_derive_from_one_chain(compact):  # R-18
    switch, _, dims, _ = make_inputs(compact)
    assert dims.above_z == pytest.approx(8.3)
    assert dims.keyplate_z == pytest.approx(switch.bottom_housing.d.Z + dims.keyplate_under_housing)
    assert dims.below_z == pytest.approx(switch.below.d.Z + dims.floor_under_pins)
    assert dims.bottom_plate_z == pytest.approx(dims.below_z - dims.keyplate_z)
    assert dims.keyplate_z == pytest.approx(2.9)
    assert dims.below_z == pytest.approx(5.9)
    assert dims.bottom_plate_z == pytest.approx(3.0)
