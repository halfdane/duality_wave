"""Show the case in a pose, or a coupon plate, in the OCP CAD Viewer.

Run `task view -- transport`. This exports nothing and replaces what the viewer shows.
"""
import argparse

from duality_wave.builders.parts import colour
from duality_wave.builders.poses import POSES, pose_scene
from duality_wave.builders.viewer import OcpViewer, SilentViewer, show_in_viewer
from duality_wave.cli.common import COUPON_TARGETS, build_case, coupon_parts


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="view", description=__doc__.splitlines()[0])
    parser.add_argument("what", nargs="?", default="assembled", choices=[*POSES, *COUPON_TARGETS],
                        help="a pose of the case or a coupon plate (default: assembled)")
    parser.add_argument("--compact", action="store_true", help="the compact variant of the case")
    parser.add_argument("--debug", action="store_true", help="add the intermediate shapes in a hidden group (assembled only)")
    args = parser.parse_args(argv)

    is_pose = args.what in POSES
    if not is_pose and args.compact:
        parser.error("--compact applies to the poses of the case only")
    if args.debug and args.what != "assembled":
        parser.error("--debug applies to the assembled pose only")

    viewer = OcpViewer()
    if is_pose:
        silent = SilentViewer(collect_debug=args.debug)
        scene = pose_scene(build_case(compact=args.compact, viewer=silent), args.what)
        colours = {name: colour(*name.rsplit("_", 1)) for name in scene}
    else:
        scene = coupon_parts(args.what)
        colours = {}
    viewer.clear()
    for name, shape in scene.items():
        viewer.push(shape, name=name, color=colours.get(name))
    if args.debug:
        viewer.debug = silent.debug
        viewer.push_debug()
    show_in_viewer()

