from duality_wave.case import WaveCase
from duality_wave.models.case_dimensions import CaseDimensions
from duality_wave.models.choc import Choc
from duality_wave.models.keys import ErgoKeys, get_points
from duality_wave.models.outline import Outline
from duality_wave.paths import LAYOUT_DIR


def build_full_case(viewer=None, debug: bool = False) -> WaveCase:
    """The full variant with both halves. A viewer replaces the default one, which depends on debug."""
    switch = Choc()
    keys = ErgoKeys(points=get_points(file_path=LAYOUT_DIR / "wave.points.yaml"))
    outline = Outline(switch=switch, keys=keys, wall_thickness=CaseDimensions.wall_thickness,
                      additional_top_space=CaseDimensions.additional_top_space)
    dims = CaseDimensions(switch=switch, outline=outline, keys=keys)
    return WaveCase(switch=switch, keys=keys, caseDimensions=dims, outline=outline, debug=debug, both_sides=True, viewer=viewer)
