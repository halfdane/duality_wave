"""Export the assembled case as meshes for the Blender renders (render_blender.py).

Run `task render` to export the meshes and render the images in docs/images.
"""
import os
import sys

from build123d import *

from duality_wave import CaseDimensions
from models.choc import Choc
from models.keys import ErgoKeys, get_points
from models.outline import Outline
from wave_generator import WaveCase

OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join("build", "render")


def main():
    switch = Choc()
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ergogen", "wave.yml")
    keys = ErgoKeys(points=get_points(file_path=config_path))
    outline = Outline(switch=switch, keys=keys, wall_thickness=CaseDimensions.wall_thickness)
    dims = CaseDimensions(switch=switch, outline=outline, keys=keys)
    case = WaveCase(switch=switch, keys=keys, caseDimensions=dims, outline=outline, debug=False, both_sides=True)

    # the keycap stand-in starts where the stem ends, everything above that is cap
    cap_start = switch.base.d.Z + switch.upper_housing.d.Z + switch.stem.d.Z - switch.cap_model_overlap
    switch_part = switch.model.part
    cap_cutter = Box(40, 40, 20, align=(Align.CENTER, Align.CENTER, Align.MIN)).translate((0, 0, cap_start))
    caps = switch_part & cap_cutter
    bodies = switch_part - cap_cutter

    placements = {
        "left": [Location(key.p, (0, 0, key.r)) for key in keys.keys],
        "right": [
            Location((dims.right_side_offset - key.p.X, key.p.Y, key.p.Z), (0, 0, -key.r))
            for key in keys.keys
        ],
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    for side, locations in placements.items():
        for name in ("keywell", "keyplate", "bottom"):
            export_stl(getattr(case, f"{name}_{side}"), os.path.join(OUT_DIR, f"{name}_{side}.stl"))
        export_stl(Compound([bodies.moved(loc) for loc in locations]), os.path.join(OUT_DIR, f"switches_{side}.stl"))
        export_stl(Compound([caps.moved(loc) for loc in locations]), os.path.join(OUT_DIR, f"caps_{side}.stl"))
    print(f"Exported meshes to {OUT_DIR}")


if __name__ == "__main__":
    main()
