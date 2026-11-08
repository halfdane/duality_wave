"""Export the poses of the case as meshes for the Blender renders (render_blender.py).

Run `task render` to export the meshes and render the images in docs/images.
Every pose gets a folder with one mesh per part and the file scene.json, which lists the meshes with their colours.
"""
import json
import os
import sys
from pathlib import Path

from build123d import export_stl

from duality_wave.builders.parts import GROUPS, colour
from duality_wave.builders.poses import POSES, pose_scene
from duality_wave.builders.viewer import SilentViewer
from duality_wave.cli.common import build_full_case
from duality_wave.paths import BUILD_DIR

OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else str(BUILD_DIR / "render")


def manifest_entry(name: str) -> dict:
    group, side = name.rsplit("_", 1)
    return {"stem": name, "group": group, "side": side, "color": colour(group, side), "metallic": GROUPS[group].metallic}


def export_pose(case, pose: str, out_dir: Path) -> None:
    scene = pose_scene(case, pose)
    pose_dir = out_dir / pose
    os.makedirs(pose_dir, exist_ok=True)
    for name, shape in scene.items():
        export_stl(shape, str(pose_dir / f"{name}.stl"))
    (pose_dir / "scene.json").write_text(json.dumps([manifest_entry(name) for name in scene], indent=2))


def main():
    case = build_full_case(viewer=SilentViewer())
    for pose in POSES:
        export_pose(case, pose, Path(OUT_DIR))
    print(f"Exported meshes to {OUT_DIR}")


if __name__ == "__main__":
    main()
