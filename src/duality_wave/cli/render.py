"""Export the assembled case as meshes for the Blender renders (render_blender.py).

Run `task render` to export the meshes and render the images in docs/images.
"""
import os
import sys

from build123d import *

from duality_wave.case import WaveCase
from duality_wave.models.case_dimensions import CaseDimensions
from duality_wave.models.choc import Choc
from duality_wave.models.keys import ErgoKeys, get_points
from duality_wave.models.outline import Outline
from duality_wave.paths import BUILD_DIR, LAYOUT_DIR

OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else str(BUILD_DIR / "render")


def main():
    switch = Choc()
    config_path = LAYOUT_DIR / "wave.points.yaml"
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

    # two stacked magnets fill each recess, flush with the top of the keywell
    left_magnets = Compound([
        Pos(position.X, position.Y, dims.above_z) * Cylinder(
            dims.magnet_d.radius, 2 * dims.magnet_d.Z, align=(Align.CENTER, Align.CENTER, Align.MAX))
        for position in dims.magnet_positions
    ])

    os.makedirs(OUT_DIR, exist_ok=True)
    for built in (case.left, case.right):
        side = built.side
        for name in ("keywell", "keyplate", "bottom"):
            export_stl(getattr(built, name), os.path.join(OUT_DIR, f"{name}_{side.name}.stl"))
        export_stl(built.xiao.model - built.xiao.usb_connector, os.path.join(OUT_DIR, f"xiao_{side.name}.stl"))
        export_stl(built.xiao.usb_connector, os.path.join(OUT_DIR, f"usb_{side.name}.stl"))
        export_stl(side.mirrored(left_magnets), os.path.join(OUT_DIR, f"magnets_{side.name}.stl"))
        export_stl(Compound([bodies.moved(loc) for loc in side.switch_locations]), os.path.join(OUT_DIR, f"switches_{side.name}.stl"))
        export_stl(Compound([caps.moved(loc) for loc in side.switch_locations]), os.path.join(OUT_DIR, f"caps_{side.name}.stl"))
    print(f"Exported meshes to {OUT_DIR}")


if __name__ == "__main__":
    main()
