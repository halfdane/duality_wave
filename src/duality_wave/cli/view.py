"""Show the case in a pose, or a coupon plate, in the OCP CAD Viewer.

Run `task view -- transport`. This exports nothing and replaces what the viewer shows.
"""
import argparse
import copy

from build123d import Color, Shape

from duality_wave.builders.parts import GROUPS, alpha, colour
from duality_wave.builders.poses import POSES, pose_scene
from duality_wave.builders.viewer import OcpViewer, SilentViewer, show_in_viewer
from duality_wave.cli.common import COUPON_TARGETS, build_case, coupon_parts


def styled(scene: dict[str, Shape], ghost: bool) -> dict[str, Shape]:
    """Copies of the parts with their colour and opacity. The viewer reads the colour of every part in a group from the part."""
    result = {}
    for name, shape in scene.items():
        group, side = name.rsplit("_", 1)
        result[name] = copy.copy(shape)
        result[name].color = Color(colour(group, side), alpha(group, ghost))
    return result


def grouped(scene: dict[str, Shape]) -> dict[str, dict]:
    """One group for each half. It holds the case parts and an accessories group with all other parts."""
    halves: dict[str, dict] = {}
    for name, shape in scene.items():
        group, side = name.rsplit("_", 1)
        half = halves.setdefault(side, {})
        if GROUPS[group].shell:
            half[group] = shape
        else:
            half.setdefault("accessories", {})[group] = shape
    return halves


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="view", description=__doc__.splitlines()[0])
    parser.add_argument("what", nargs="?", default="assembled", choices=[*POSES, *COUPON_TARGETS],
                        help="a pose of the case or a coupon plate (default: assembled)")
    parser.add_argument("--compact", action="store_true", help="the compact variant of the case")
    parser.add_argument("--ghost", action="store_true", help="make the case parts see-through, so the parts inside stand out")
    parser.add_argument("--debug", action="store_true", help="add the intermediate shapes in a hidden group (assembled only)")
    args = parser.parse_args(argv)

    is_pose = args.what in POSES
    if not is_pose and args.compact:
        parser.error("--compact applies to the poses of the case only")
    if not is_pose and args.ghost:
        parser.error("--ghost applies to the poses of the case only")
    if args.debug and args.what != "assembled":
        parser.error("--debug applies to the assembled pose only")

    viewer = OcpViewer()
    if is_pose:
        silent = SilentViewer(collect_debug=args.debug)
        scene = pose_scene(build_case(compact=args.compact, viewer=silent), args.what)
        groups = grouped(styled(scene, args.ghost))
    else:
        groups = {"coupons": coupon_parts(args.what)}
    viewer.clear()
    for name, content in groups.items():
        viewer.push(content, name=name)
    if args.debug:
        viewer.debug = silent.debug
        viewer.push_debug()
    show_in_viewer()

