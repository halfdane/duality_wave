"""The viewers and the command that shows a pose."""

from unittest.mock import MagicMock, patch

import pytest
from build123d import Box

from duality_wave.builders.parts import colour
from duality_wave.builders.viewer import OcpViewer, SilentViewer
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


def test_the_view_command_clears_the_viewer_then_pushes_every_part_in_its_colour():
    scene = {"keywell_left": Box(1, 1, 1), "power_switch_right": Box(1, 1, 1)}
    calls = MagicMock()
    with (
        patch.object(view, "build_full_case", return_value="case") as build,
        patch.object(view, "pose_scene", return_value=scene) as pose_scene,
        patch("ocp_vscode.show_clear", calls.clear),
        patch("ocp_vscode.push_object", calls.push),
        patch.object(view, "show_in_viewer", calls.show),
    ):
        view.main(["transport"])
    assert isinstance(build.call_args.kwargs["viewer"], SilentViewer)
    pose_scene.assert_called_once_with("case", "transport")
    assert [c[0] for c in calls.mock_calls] == ["clear", "push", "push", "show"]
    pushed = {c.kwargs["name"]: c.kwargs["color"] for c in calls.push.call_args_list}
    assert pushed == {"keywell_left": colour("keywell", "left"), "power_switch_right": colour("power_switch", "right")}


def test_the_view_command_refuses_an_unknown_pose():
    with pytest.raises(SystemExit):
        view.main(["sideways"])
