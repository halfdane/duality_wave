"""The viewers and the command that shows a pose."""

from unittest.mock import MagicMock, patch

import pytest
from build123d import Box

from duality_wave.builders.parts import colour
from duality_wave.builders.viewer import DebugScope, OcpViewer, SilentViewer
from duality_wave.cli import view


def test_the_silent_viewer_builds_accessories_but_shows_nothing():
    viewer = SilentViewer()
    with patch("ocp_vscode.push_object") as push_object:
        viewer.push(Box(1, 1, 1), name="x", color="#ffffff")
        viewer.push_debug()
        viewer.debug.note("a", Box(1, 1, 1))
        viewer.debug.scope("b").note("c", Box(1, 1, 1))
    assert viewer.enabled
    push_object.assert_not_called()


def test_the_ocp_viewer_passes_a_colour_only_when_it_gets_one():
    with patch("ocp_vscode.push_object") as push_object:
        OcpViewer().push(Box(1, 1, 1), name="plain")
        OcpViewer().push(Box(1, 1, 1), name="coloured", color="#123456")
    assert "color" not in push_object.call_args_list[0].kwargs
    assert push_object.call_args_list[1].kwargs["color"] == "#123456"


def test_the_ocp_viewer_clears_the_viewer():
    with patch("ocp_vscode.show_clear") as show_clear:
        OcpViewer().clear()
    show_clear.assert_called_once()


def run_view(argv, scene, pose_scene_result=True):
    """Run the view command with a fake scene. Returns the recorded calls of the viewer and the mocks of the builders."""
    calls = MagicMock()
    with (
        patch.object(view, "build_case", return_value="case") as build,
        patch.object(view, "pose_scene", return_value=scene) as pose_scene,
        patch.object(view, "coupon_parts", return_value=scene) as coupons,
        patch("ocp_vscode.show_clear", calls.clear),
        patch("ocp_vscode.push_object", calls.push),
        patch.object(view, "show_in_viewer", calls.show),
        patch("ocp_vscode.status", return_value={}),
    ):
        view.main(argv)
    return calls, build, pose_scene, coupons


def test_the_view_command_clears_the_viewer_then_pushes_every_part_in_its_colour():
    scene = {"keywell_left": Box(1, 1, 1), "power_switch_right": Box(1, 1, 1)}
    calls, build, pose_scene, _ = run_view(["transport"], scene)
    assert isinstance(build.call_args.kwargs["viewer"], SilentViewer)
    assert build.call_args.kwargs["compact"] is False
    pose_scene.assert_called_once_with("case", "transport")
    assert [c[0] for c in calls.mock_calls] == ["clear", "push", "push", "show"]
    pushed = {c.kwargs["name"]: c.kwargs["color"] for c in calls.push.call_args_list}
    assert pushed == {"keywell_left": colour("keywell", "left"), "power_switch_right": colour("power_switch", "right")}


def test_the_assembled_pose_is_the_default_and_the_compact_variant_is_a_flag():
    _, build, pose_scene, _ = run_view(["--compact"], {"keywell_left": Box(1, 1, 1)})
    assert build.call_args.kwargs["compact"] is True
    pose_scene.assert_called_once_with("case", "assembled")


def test_a_coupon_plate_is_shown_part_by_part_without_building_a_case():
    scene = {"A switch plate": Box(1, 1, 1), "B cavity": Box(1, 1, 1)}
    calls, build, pose_scene, coupons = run_view(["coupons"], scene)
    coupons.assert_called_once_with("coupons")
    build.assert_not_called()
    pose_scene.assert_not_called()
    assert [c.kwargs["name"] for c in calls.push.call_args_list] == list(scene)
    assert all("color" not in c.kwargs for c in calls.push.call_args_list)


def test_the_debug_group_arrives_last_and_only_when_asked():
    scene = {"keywell_left": Box(1, 1, 1)}
    calls, build, _, _ = run_view(["assembled", "--debug"], scene)
    assert isinstance(build.call_args.kwargs["viewer"].debug, DebugScope)
    names = [c.kwargs["name"] for c in calls.push.call_args_list]
    assert names == ["keywell_left", "debug"]
    calls, _, _, _ = run_view(["assembled"], scene)
    assert [c.kwargs["name"] for c in calls.push.call_args_list] == ["keywell_left"]


@pytest.mark.parametrize("argv", [
    ["sideways"], ["transport", "--debug"], ["coupons", "--compact"], ["coupons-engraving", "--debug"]])
def test_the_view_command_refuses_arguments_that_do_not_fit_together(argv):
    with pytest.raises(SystemExit):
        run_view(argv, {})
