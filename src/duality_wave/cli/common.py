from build123d import Shape

from duality_wave.builders.common import CaseContext
from duality_wave.case import WaveCase
from duality_wave.models.heat_set_insert import HeatSetInsert
from duality_wave.models.rubber_bumper import RubberBumper
from duality_wave.models.screw import LowProfileScrew
from duality_wave.coupons import create_coupon_parts, create_wiring_coupon_parts
from duality_wave.coupons_engraving import engraving_coupon_slabs
from duality_wave.case_dimensions import CaseDimensions, CompactCaseDimensions
from duality_wave.models.choc import Choc
from duality_wave.models.keys import ErgoKeys, get_points
from duality_wave.models.model_types import WaveDimensions
from duality_wave.models.outline import Outline
from duality_wave.paths import LAYOUT_DIR, WIRING_FILE
from duality_wave.wiring.plan import WiringPlan

COUPON_TARGETS = ("coupons-hardware", "coupons-plate-wiring-engraving")


def case_inputs(compact: bool = False) -> tuple[Choc, ErgoKeys, Outline, WaveDimensions]:
    """The switch, the keys, the outline and the dimensions of the full or the compact variant."""
    dimensions = CompactCaseDimensions if compact else CaseDimensions
    layout = "compact.points.yaml" if compact else "wave.points.yaml"
    switch = Choc()
    keys = ErgoKeys(points=get_points(file_path=LAYOUT_DIR / layout))
    outline = Outline(switch=switch, keys=keys, wall_thickness=dimensions.wall_thickness,
                      additional_top_space=dimensions.additional_top_space)
    return switch, keys, outline, dimensions(switch=switch, outline=outline, keys=keys)


def case_context(compact: bool = False) -> CaseContext:
    """What the part builders read, without building anything."""
    switch, keys, outline, dims = case_inputs(compact)
    return CaseContext(switch, keys, dims, outline, RubberBumper(), HeatSetInsert(), LowProfileScrew())


def build_case(compact: bool = False, viewer=None) -> WaveCase:
    """The full variant with both halves, or the compact variant with the left half.

    Without a viewer nothing is shown and only the printable parts are built.
    The full variant gets the wiring of ergogen/wave.wiring.yaml. The compact variant has no wiring.
    """
    switch, keys, outline, dims = case_inputs(compact)
    wiring = None if compact else WiringPlan.load(WIRING_FILE)
    return WaveCase(switch=switch, keys=keys, caseDimensions=dims, outline=outline, both_sides=not compact, viewer=viewer, wiring=wiring)


def coupon_parts(target: str) -> dict[str, Shape]:
    """The parts of a coupon plate by name, arranged on one print bed."""
    switch = Choc()
    keys = ErgoKeys(points=get_points(file_path=LAYOUT_DIR / "wave.points.yaml"))
    outline = Outline(switch=switch, keys=keys, wall_thickness=CaseDimensions.wall_thickness)
    dims = CaseDimensions(switch=switch, outline=outline, keys=keys)
    if target == "coupons-hardware":
        return create_coupon_parts(switch, dims)
    if target == "coupons-plate-wiring-engraving":
        return create_wiring_coupon_parts(dims, WiringPlan.load(WIRING_FILE).diode, extra=engraving_coupon_slabs(dims))
    raise ValueError(f"Unknown coupon target {target!r}. Use one of {COUPON_TARGETS}.")
