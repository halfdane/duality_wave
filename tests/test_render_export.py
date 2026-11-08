"""The files that the Blender script reads."""

import json
from unittest.mock import patch

from build123d import Box

from duality_wave.builders.parts import GROUPS, alpha, colour
from duality_wave.cli import render


def test_a_manifest_entry_carries_the_colour_of_the_group_and_the_side():
    entry = render.manifest_entry("power_switch_right")
    assert entry == {
        "stem": "power_switch_right", "group": "power_switch", "side": "right",
        "color": colour("power_switch", "right"), "metallic": GROUPS["power_switch"].metallic,
        "ghost_alpha": 1.0,
    }
    assert render.manifest_entry("keywell_left")["ghost_alpha"] == alpha("keywell", ghost=True) < 1


def test_every_part_of_a_pose_gets_a_mesh_and_a_manifest_entry(tmp_path):
    scene = {"keywell_left": Box(1, 1, 1), "usb_right": Box(2, 2, 2)}
    with patch.object(render, "pose_scene", return_value=scene):
        render.export_pose("case", "transport", tmp_path)
    folder = tmp_path / "transport"
    assert sorted(path.name for path in folder.glob("*.stl")) == ["keywell_left.stl", "usb_right.stl"]
    manifest = json.loads((folder / "scene.json").read_text())
    assert [entry["stem"] for entry in manifest] == list(scene)
    assert manifest[1]["metallic"] is True
