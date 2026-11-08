"""Export the poses of the case as meshes for the Blender renders (render_blender.py).

Run `task render` to export the meshes and render the images in docs/images.
Every pose gets a folder with one mesh per part and the file scene.json, which lists the meshes with their colours.
"""
import argparse
import json
import os
from pathlib import Path

from build123d import export_stl

from duality_wave.builders.parts import GROUPS, alpha, colour
from duality_wave.builders.poses import POSES, pose_scene
from duality_wave.builders.viewer import SilentViewer
from duality_wave.cli.common import build_case
from duality_wave.paths import BUILD_DIR


def manifest_entry(name: str) -> dict:
    group, side = name.rsplit("_", 1)
    return {
        "stem": name, "group": group, "side": side, "color": colour(group, side), "metallic": GROUPS[group].metallic,
        "ghost_alpha": alpha(group, ghost=True),
    }


def export_pose(case, pose: str, out_dir: Path) -> None:
    scene = pose_scene(case, pose)
    pose_dir = out_dir / pose
    os.makedirs(pose_dir, exist_ok=True)
    for name, shape in scene.items():
        export_stl(shape, str(pose_dir / f"{name}.stl"))
    (pose_dir / "scene.json").write_text(json.dumps([manifest_entry(name) for name in scene], indent=2))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="render", description=__doc__.splitlines()[0])
    parser.add_argument("out_dir", nargs="?", default=str(BUILD_DIR / "render"), help="where the meshes go")
    out_dir = Path(parser.parse_args(argv).out_dir)

    case = build_case(viewer=SilentViewer())
    for pose in POSES:
        export_pose(case, pose, out_dir)
    print(f"Exported meshes to {out_dir}")
