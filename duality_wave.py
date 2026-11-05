import os

from build123d import *

from builders.export import export_steps
from builders.viewer import show_in_viewer
from models.case_dimensions import CaseDimensions
from models.choc import Choc
from models.keys import ErgoKeys, get_points
from models.outline import Outline
from wave_generator import WaveCase


if __name__ == "__main__":
    switch = Choc()
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ergogen', 'wave.yml')
    keys = ErgoKeys(points=get_points(file_path=config_path))
    outline = Outline(switch=switch, keys=keys, wall_thickness=CaseDimensions.wall_thickness)
    dims = CaseDimensions(switch=switch, outline=outline, keys=keys)
    case = WaveCase(switch=switch, keys=keys, caseDimensions=dims, outline=outline, debug=True, both_sides=True)
    show_in_viewer()
    export_steps(case)
