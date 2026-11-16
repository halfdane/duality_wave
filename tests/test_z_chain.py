"""The Z chain: the levels of the case stack up from the table."""

import pytest
from duality_wave.cli import z_chain
from duality_wave.models.rubber_bumper import BumperDimensions
from tests.builds import make_inputs


@pytest.mark.parametrize("compact", [False, True])
def test_the_levels_stack_up_from_the_table(compact):
    switch, _, dims, _ = make_inputs(compact)
    bumper = BumperDimensions()
    chain = z_chain.ZChain.of(switch, dims, bumper)

    assert chain.bed_face == pytest.approx(bumper.dome_z)
    assert chain.cap_top == pytest.approx(bumper.dome_z + dims.below_z + switch.above.d.Z)
    assert chain.wall_top == pytest.approx(bumper.dome_z + dims.below_z + dims.above_z)
    assert chain.case_height == pytest.approx(dims.below_z + dims.above_z)
    assert chain.plate_top - chain.bed_face == pytest.approx(dims.bottom_plate_z)
    assert chain.keyplate_top - chain.plate_top == pytest.approx(dims.keyplate_z)
    levels = [chain.bed_face, chain.plate_top, chain.housing_bottom, chain.keyplate_top, chain.flange_top,
              chain.upper_housing_top, chain.stem_top, chain.cap_top, chain.wall_top]
    assert levels == sorted(levels)
