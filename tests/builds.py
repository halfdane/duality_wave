"""Cases that several tests share. Each distinct case is built once per test process."""

from functools import cache
from unittest.mock import patch

from duality_wave.case import WaveCase
from duality_wave.models.case_dimensions import CaseDimensions, CompactCaseDimensions
from duality_wave.models.choc import Choc
from duality_wave.models.keys import ErgoKeys, get_points
from duality_wave.models.outline import Outline
from tests import COMPACT_LAYOUT, WAVE_LAYOUT

PARTS = ("keywell", "keyplate", "bottom")


@cache
def build_case(debug: bool, both_sides: bool = True, compact: bool = False):
    """Build a case once per test run. Returns the case and the mock that received its viewer pushes."""
    switch = Choc()
    if compact:
        keys = ErgoKeys(get_points(COMPACT_LAYOUT))
        outline = Outline(
            switch=switch, keys=keys, wall_thickness=CompactCaseDimensions.wall_thickness, additional_top_space=22)
        dims = CompactCaseDimensions(switch=switch, outline=outline, keys=keys)
    else:
        keys = ErgoKeys(get_points(WAVE_LAYOUT))
        outline = Outline(switch=switch, keys=keys, wall_thickness=CaseDimensions.wall_thickness)
        dims = CaseDimensions(switch=switch, outline=outline, keys=keys)
    with patch("ocp_vscode.push_object") as push_object:
        case = WaveCase(switch, keys, dims, outline, debug=debug, both_sides=both_sides)
    return case, push_object
