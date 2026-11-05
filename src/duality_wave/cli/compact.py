from duality_wave.builders.export import export_steps
from duality_wave.builders.viewer import show_in_viewer
from duality_wave.case import WaveCase
from duality_wave.models.case_dimensions import CompactCaseDimensions
from duality_wave.models.choc import Choc
from duality_wave.models.keys import ErgoKeys, get_points
from duality_wave.models.outline import Outline
from duality_wave.paths import LAYOUT_DIR


if __name__ == "__main__":
    switch = Choc()
    config_path = LAYOUT_DIR / "compact.yml"
    keys = ErgoKeys(points=get_points(file_path=config_path))
    outline = Outline(switch=switch, keys=keys, wall_thickness=CompactCaseDimensions.wall_thickness, additional_top_space=22)
    dims = CompactCaseDimensions(switch=switch, outline=outline, keys=keys)
    case = WaveCase(switch=switch, keys=keys, caseDimensions=dims, outline=outline, debug=True, both_sides=False)
    show_in_viewer()
    export_steps(case, suffix="_compact")
