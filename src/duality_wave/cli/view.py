"""Show the full case in a pose in the OCP CAD Viewer: assembled, transport or exploded.

Run `task view -- transport`. This exports nothing and replaces what the viewer shows.
"""
import argparse

from duality_wave.builders.parts import colour
from duality_wave.builders.poses import POSES, pose_scene
from duality_wave.builders.viewer import OcpViewer, SilentViewer, show_in_viewer
from duality_wave.cli.common import build_full_case


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pose", choices=POSES, help="the pose to show")
    pose = parser.parse_args(argv).pose

    scene = pose_scene(build_full_case(viewer=SilentViewer()), pose)
    viewer = OcpViewer()
    viewer.clear()
    for name, shape in scene.items():
        group, side = name.rsplit("_", 1)
        viewer.push(shape, name=name, color=colour(group, side))
    show_in_viewer()


if __name__ == "__main__":
    main()
