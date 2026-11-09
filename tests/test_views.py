"""The viewers and the command that shows a pose."""

from unittest.mock import MagicMock, patch

import pytest
from build123d import Box, Color

from duality_wave.builders.parts import GHOST_ALPHA, colour
from duality_wave.builders.viewer import DebugScope, OcpViewer, SilentViewer
from duality_wave.cli import view


def test_the_silent_viewer_builds_accessories_but_shows_nothing():
    viewer = SilentViewer()
    with patch("ocp_viewer.push_object") as push_object:
        viewer.push(Box(1, 1, 1), name="x")
        viewer.push_debug()
        viewer.debug.note("a", Box(1, 1, 1))
        viewer.debug.scope("b").note("c", Box(1, 1, 1))
    assert viewer.enabled
    push_object.assert_not_called()


def test_the_ocp_viewer_pushes_the_object_under_its_name():
    with patch("ocp_viewer.push_object") as push_object:
        OcpViewer().push(Box(1, 1, 1), name="plain")
    assert push_object.call_args.kwargs == {"name": "plain"}


def test_a_group_leaves_the_opacity_to_the_parts_inside():
    with patch("ocp_viewer.push_object") as push_object:
        OcpViewer().push({"a": Box(1, 1, 1)}, name="group")
    assert push_object.call_args.args[0].alpha is None


def test_the_ocp_viewer_clears_the_viewer():
    with patch("ocp_viewer.show_clear") as show_clear:
        OcpViewer().clear()
    show_clear.assert_called_once()


def run_view(argv, scene, pose_scene_result=True):
    """Run the view command with a fake scene. Returns the recorded calls of the viewer and the mocks of the builders."""
    calls = MagicMock()
    with (
        patch.object(view, "build_case", return_value="case") as build,
        patch.object(view, "pose_scene", return_value=scene) as pose_scene,
        patch.object(view, "coupon_parts", return_value=scene) as coupons,
        patch("ocp_viewer.show_clear", calls.clear),
        patch("ocp_viewer.push_object", calls.push),
        patch.object(view, "show_in_viewer", calls.show),
        patch("ocp_viewer.status", return_value={}),
    ):
        view.main(argv)
    return calls, build, pose_scene, coupons


def leaves(content, path=()):
    """The parts in a pushed group by their path of group names."""
    if isinstance(content, dict):
        for key, value in content.items():
            yield from leaves(value, (*path, key))
    else:
        yield path[-1], content


def pushed_parts(calls):
    return {name: part for c in calls.push.call_args_list for name, part in leaves(c.args[0])}


def test_the_view_command_clears_the_viewer_then_pushes_every_part_in_its_colour():
    scene = {"keywell_left": Box(1, 1, 1), "power_switch_right": Box(1, 1, 1)}
    calls, build, pose_scene, _ = run_view(["transport"], scene)
    assert isinstance(build.call_args.kwargs["viewer"], SilentViewer)
    assert build.call_args.kwargs["compact"] is False
    pose_scene.assert_called_once_with("case", "transport")
    assert [c[0] for c in calls.mock_calls] == ["clear", "push", "push", "show"]
    colours = {name: tuple(part.color) for name, part in pushed_parts(calls).items()}
    assert colours == {
        "keywell": tuple(Color(colour("keywell", "left"))), "power_switch": tuple(Color(colour("power_switch", "right")))}
    assert scene["keywell_left"].color is None


def test_the_ghost_style_makes_only_the_see_through_groups_see_through():
    scene = {"keywell_left": Box(1, 1, 1), "bottom_right": Box(1, 1, 1), "battery_left": Box(1, 1, 1), "switches_left": Box(1, 1, 1)}
    calls, _, pose_scene, _ = run_view(["exploded", "--ghost"], scene)
    pose_scene.assert_called_once_with("case", "exploded")
    alphas = {name: tuple(part.color)[3] for name, part in pushed_parts(calls).items()}
    # a colour keeps its opacity in steps of 1/255
    assert alphas == pytest.approx({"keywell": GHOST_ALPHA, "bottom": GHOST_ALPHA, "battery": GHOST_ALPHA, "switches": 1.0}, abs=1 / 255)


def test_without_the_ghost_style_every_part_is_opaque():
    calls, _, _, _ = run_view(["assembled"], {"keywell_left": Box(1, 1, 1)})
    assert all(tuple(part.color)[3] == 1.0 for part in pushed_parts(calls).values())


def test_the_assembled_pose_is_the_default_and_the_compact_variant_is_a_flag():
    _, build, pose_scene, _ = run_view(["--compact"], {"keywell_left": Box(1, 1, 1)})
    assert build.call_args.kwargs["compact"] is True
    pose_scene.assert_called_once_with("case", "assembled")


def test_a_coupon_plate_is_shown_as_one_group_without_building_a_case():
    scene = {"A switch plate": Box(1, 1, 1), "B cavity": Box(1, 1, 1)}
    calls, build, pose_scene, coupons = run_view(["coupons"], scene)
    coupons.assert_called_once_with("coupons")
    build.assert_not_called()
    pose_scene.assert_not_called()
    assert [c.kwargs["name"] for c in calls.push.call_args_list] == ["coupons"]
    assert calls.push.call_args.args[0] == scene


def test_the_debug_group_arrives_last_and_only_when_asked():
    scene = {"keywell_left": Box(1, 1, 1)}
    calls, build, _, _ = run_view(["assembled", "--debug"], scene)
    assert isinstance(build.call_args.kwargs["viewer"].debug, DebugScope)
    names = [c.kwargs["name"] for c in calls.push.call_args_list]
    assert names == ["left", "debug"]
    calls, _, _, _ = run_view(["assembled"], scene)
    assert [c.kwargs["name"] for c in calls.push.call_args_list] == ["left"]


@pytest.mark.parametrize("argv", [
    ["sideways"], ["transport", "--debug"], ["coupons", "--ghost"], ["coupons", "--compact"], ["coupons-engraving", "--debug"], ["coupons-wiring", "--debug"]])
def test_the_view_command_refuses_arguments_that_do_not_fit_together(argv):
    with pytest.raises(SystemExit):
        run_view(argv, {})
