from build123d import *

from duality_wave.builders.export import export_steps
from duality_wave.builders.viewer import show_in_viewer
from duality_wave.case import WaveCase
from duality_wave.models.case_dimensions import CaseDimensions
from duality_wave.models.choc import Choc
from duality_wave.models.keys import ErgoKeys, get_points
from duality_wave.models.outline import Outline
from duality_wave.paths import LAYOUT_DIR


if __name__ == "__main__":
    switch = Choc()
    config_path = LAYOUT_DIR / "wave.points.yaml"
    keys = ErgoKeys(points=get_points(file_path=config_path))
    outline = Outline(switch=switch, keys=keys, wall_thickness=CaseDimensions.wall_thickness)
    dims = CaseDimensions(switch=switch, outline=outline, keys=keys)
    case = WaveCase(switch=switch, keys=keys, caseDimensions=dims, outline=outline, debug=True, both_sides=True)
    show_in_viewer()
    export_steps(case)
