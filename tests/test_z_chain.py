"""The picture of the Z chain: its levels come from the case dimensions and the SVG shows the two headline heights."""

import xml.etree.ElementTree as ET

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


def test_the_svg_shows_the_two_headline_heights_that_the_chain_computes():
    switch, _, dims, _ = make_inputs()
    bumper = BumperDimensions()
    chain = z_chain.ZChain.of(switch, dims, bumper)

    svg = z_chain.render_svg(switch, dims, bumper)

    texts = {element.text for element in ET.fromstring(svg).iter("{http://www.w3.org/2000/svg}text")}
    assert f"Table to keycap top: {z_chain.mm(chain.cap_top)} mm" in texts
    assert f"Bottom plate to top of keywell: {z_chain.mm(chain.case_height)} mm" in texts


def test_the_command_writes_the_svg(tmp_path, capsys):
    out = tmp_path / "chain.svg"
    z_chain.main([str(out)])
    assert ET.parse(out).getroot().tag.endswith("svg")
    assert capsys.readouterr().out.strip() == str(out)
