"""The case that the integration tests share. It is built once per test process."""

from functools import cache
from unittest.mock import patch

from duality_wave.builders.common import CaseContext
from duality_wave.case import WaveCase
from duality_wave.case_dimensions import CaseDimensions, CompactCaseDimensions
from duality_wave.models.choc import Choc
from duality_wave.models.heat_set_insert import HeatSetInsert
from duality_wave.models.keys import ErgoKeys, get_points
from duality_wave.models.outline import Outline, OutlineSpec
from duality_wave.print_profile import PrintProfile
from duality_wave.models.rubber_bumper import RubberBumper
from duality_wave.models.screw import LowProfileScrew
from duality_wave.paths import WIRING_FILE
from duality_wave.wiring.plan import WiringPlan
from tests import COMPACT_LAYOUT, WAVE_LAYOUT

PARTS = ("keywell", "keyplate", "bottom")


def make_outline(compact: bool = False, spec: OutlineSpec = OutlineSpec(), points: dict | None = None) -> Outline:
    """The outline of the full or the compact variant. Points replace the layout of the variant."""
    dimensions = CompactCaseDimensions if compact else CaseDimensions
    keys = ErgoKeys(points if points is not None else get_points(COMPACT_LAYOUT if compact else WAVE_LAYOUT))
    return Outline(
        Choc(), keys, wall_thickness=dimensions.wall_thickness, additional_top_space=dimensions.additional_top_space, spec=spec)


def make_inputs(compact: bool = False, profile: PrintProfile | None = None):
    """Switch, keys, dimensions and outline of the full or the compact variant. The default print profile is the standard one."""
    outline = make_outline(compact)
    dimensions = CompactCaseDimensions if compact else CaseDimensions
    extra = {} if profile is None else {"print_profile": profile}
    return outline.switch, outline.keys, dimensions(switch=outline.switch, outline=outline, keys=outline.keys, **extra), outline


def make_context(compact: bool = False, profile: PrintProfile | None = None) -> CaseContext:
    """The context for one part builder. This builds no case."""
    switch, keys, dims, outline = make_inputs(compact, profile)
    return CaseContext(switch, keys, dims, outline, RubberBumper(), HeatSetInsert(), LowProfileScrew())


@cache
def full_case():
    """The full variant, both halves, with debug. This is what `task view` shows. It is built once per test process."""
    switch, keys, dims, outline = make_inputs()
    with patch("ocp_viewer.push_object"), patch("ocp_viewer.status", return_value={}):
        return WaveCase(switch, keys, dims, outline, debug=True, both_sides=True, wiring=WiringPlan.load(WIRING_FILE))
