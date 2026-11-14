"""The picture of the Z chain: its levels come from the case dimensions and the SVG shows the two headline heights."""

import xml.etree.ElementTree as ET

import pytest
import re
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


def test_the_svg_names_every_part_and_shows_the_two_headline_heights():
    switch, _, dims, _ = make_inputs()
    svg = z_chain.render_svg(switch, dims, BumperDimensions())

    texts = {element.text for element in ET.fromstring(svg).iter("{http://www.w3.org/2000/svg}text")}

    table_to_keycap_pattern = re.compile(r"Table to keycap top: \d\d.\d mm")
    assert any(table_to_keycap_pattern.search(s) for s in texts), (
        f"Expected at least one string matching {table_to_keycap_pattern.pattern!r}, "
        f"but none matched in: {texts!r}"
    )

    bottom_plate_to_keywell_pattern = re.compile(r"Bottom plate to top of keywell: \d\d.\d mm")
    assert any(bottom_plate_to_keywell_pattern.search(s) for s in texts), (
        f"Expected at least one string matching {bottom_plate_to_keywell_pattern.pattern!r}, "
        f"but none matched in: {texts!r}"
    )


def test_the_command_writes_the_svg(tmp_path, capsys):
    out = tmp_path / "chain.svg"
    z_chain.main([str(out)])
    assert ET.parse(out).getroot().tag.endswith("svg")
    assert capsys.readouterr().out.strip() == str(out)
