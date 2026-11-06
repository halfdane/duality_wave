"""Cases that several tests share. Each distinct case is built once per test process."""

from functools import cache
from unittest.mock import patch

from duality_wave.builders.common import CaseContext
from duality_wave.case import WaveCase
from duality_wave.models.case_dimensions import CaseDimensions, CompactCaseDimensions
from duality_wave.models.choc import Choc
from duality_wave.models.heat_set_insert import HeatSetInsert
from duality_wave.models.keys import ErgoKeys, get_points
from duality_wave.models.outline import Outline
from duality_wave.models.rubber_bumper import RubberBumper
from duality_wave.models.screw import LowProfileScrew
from tests import COMPACT_LAYOUT, WAVE_LAYOUT

PARTS = ("keywell", "keyplate", "bottom")


def make_inputs(compact: bool = False):
    """Switch, keys, dimensions and outline of the full or the compact variant."""
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
    return switch, keys, dims, outline


def make_context(compact: bool = False) -> CaseContext:
    """The context for one part builder. This builds no case."""
    switch, keys, dims, outline = make_inputs(compact)
    return CaseContext(
        switch, keys, dims, outline, RubberBumper(), HeatSetInsert(dims.print_profile.insert_pilot_radius), LowProfileScrew())


@cache
def build_case(debug: bool, both_sides: bool = True, compact: bool = False):
    """Build a case once per test run. Returns the case and the mock that received its viewer pushes."""
    switch, keys, dims, outline = make_inputs(compact)
    with patch("ocp_vscode.push_object") as push_object:
        case = WaveCase(switch, keys, dims, outline, debug=debug, both_sides=both_sides)
    return case, push_object
