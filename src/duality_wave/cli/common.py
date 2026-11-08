from build123d import Shape

from duality_wave.case import WaveCase
from duality_wave.coupons import create_coupon_parts
from duality_wave.coupons_engraving import create_engraving_coupon_parts
from duality_wave.models.case_dimensions import CaseDimensions, CompactCaseDimensions
from duality_wave.models.choc import Choc
from duality_wave.models.keys import ErgoKeys, get_points
from duality_wave.models.outline import Outline
from duality_wave.paths import LAYOUT_DIR

COUPON_TARGETS = ("coupons", "coupons-engraving")


def build_case(compact: bool = False, viewer=None) -> WaveCase:
    """The full variant with both halves, or the compact variant with the left half.

    Without a viewer nothing is shown and only the printable parts are built.
    """
    dimensions = CompactCaseDimensions if compact else CaseDimensions
    layout = "compact.points.yaml" if compact else "wave.points.yaml"
    switch = Choc()
    keys = ErgoKeys(points=get_points(file_path=LAYOUT_DIR / layout))
    outline = Outline(switch=switch, keys=keys, wall_thickness=dimensions.wall_thickness,
                      additional_top_space=dimensions.additional_top_space)
    dims = dimensions(switch=switch, outline=outline, keys=keys)
    return WaveCase(switch=switch, keys=keys, caseDimensions=dims, outline=outline, both_sides=not compact, viewer=viewer)


def coupon_parts(target: str) -> dict[str, Shape]:
    """The parts of a coupon plate by name, arranged on one print bed."""
    switch = Choc()
    keys = ErgoKeys(points=get_points(file_path=LAYOUT_DIR / "wave.points.yaml"))
    outline = Outline(switch=switch, keys=keys, wall_thickness=CaseDimensions.wall_thickness)
    dims = CaseDimensions(switch=switch, outline=outline, keys=keys)
    if target == "coupons":
        return create_coupon_parts(switch, dims)
    if target == "coupons-engraving":
        return create_engraving_coupon_parts(dims)
    raise ValueError(f"Unknown coupon target {target!r}. Use one of {COUPON_TARGETS}.")
