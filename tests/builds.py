"""Cases that several tests share. Each distinct case is built once per test process.

The integration tests use only three builds: full_case, compact_case and quiet_case.
"""

from functools import cache
from unittest.mock import patch

from duality_wave.builders.common import CaseContext
from duality_wave.case import WaveCase
from duality_wave.models.case_dimensions import CaseDimensions, CompactCaseDimensions
from duality_wave.models.choc import Choc
from duality_wave.models.heat_set_insert import HeatSetInsert
from duality_wave.models.keys import ErgoKeys, get_points
from duality_wave.models.outline import Outline, OutlineSpec
from duality_wave.models.rubber_bumper import RubberBumper
from duality_wave.models.screw import LowProfileScrew
from tests import COMPACT_LAYOUT, WAVE_LAYOUT

PARTS = ("keywell", "keyplate", "bottom")


def make_outline(compact: bool = False, spec: OutlineSpec = OutlineSpec(), points: dict | None = None) -> Outline:
    """The outline of the full or the compact variant. Points replace the layout of the variant."""
    dimensions = CompactCaseDimensions if compact else CaseDimensions
    keys = ErgoKeys(points if points is not None else get_points(COMPACT_LAYOUT if compact else WAVE_LAYOUT))
    return Outline(
        Choc(), keys, wall_thickness=dimensions.wall_thickness, additional_top_space=22 if compact else 10, spec=spec)


def make_inputs(compact: bool = False):
    """Switch, keys, dimensions and outline of the full or the compact variant."""
    outline = make_outline(compact)
    dimensions = CompactCaseDimensions if compact else CaseDimensions
    return outline.switch, outline.keys, dimensions(switch=outline.switch, outline=outline, keys=outline.keys), outline


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


def full_case():
    """The full variant, both halves, with debug. This is what `task build` builds."""
    return build_case(debug=True)[0]


def compact_case():
    """The compact variant, left half only, with debug."""
    return build_case(debug=True, both_sides=False, compact=True)[0]


def quiet_case():
    """The full variant, left half only, without debug."""
    return build_case(debug=False, both_sides=False)
