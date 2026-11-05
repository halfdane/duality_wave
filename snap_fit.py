import os

from builders.export import export_steps
from builders.viewer import show_in_viewer
from models.case_dimensions import CompactCaseDimensions
from models.choc import Choc
from models.keys import ErgoKeys, get_points
from models.outline import Outline
from wave_generator import WaveCase


if __name__ == "__main__":
    switch = Choc()
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ergogen', 'snap_fit.yml')
    keys = ErgoKeys(points=get_points(file_path=config_path))
    outline = Outline(switch=switch, keys=keys, wall_thickness=CompactCaseDimensions.wall_thickness, additional_top_space=22)
    dims = CompactCaseDimensions(switch=switch, outline=outline, keys=keys)
    case = WaveCase(switch=switch, keys=keys, caseDimensions=dims, outline=outline, debug=True, both_sides=False)
    show_in_viewer()
    export_steps(case, suffix="_snap_fit")
