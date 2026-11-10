"""The commands that write files, and the entry point that selects a command."""

from pathlib import Path
from unittest.mock import patch

import pytest
from build123d import Box

from duality_wave.cli import __main__ as entry
from duality_wave.cli import export_case, export_coupon


def test_the_case_is_exported_without_a_viewer():
    with patch.object(export_case, "build_case", return_value="case") as build, \
            patch.object(export_case, "export_steps", return_value=[]) as steps, \
            patch("ocp_viewer.push_object") as push_object:
        export_case.main([])
    assert build.call_args.kwargs == {"compact": False}
    steps.assert_called_once_with("case", suffix="")
    push_object.assert_not_called()


def test_the_compact_case_gets_its_own_file_names():
    with patch.object(export_case, "build_case", return_value="case") as build, \
            patch.object(export_case, "export_steps", return_value=[]) as steps:
        export_case.main(["--compact"])
    assert build.call_args.kwargs == {"compact": True}
    steps.assert_called_once_with("case", suffix="_compact")


def test_the_case_export_prints_the_paths_it_wrote(capsys):
    with patch.object(export_case, "build_case", return_value="case"), \
            patch.object(export_case, "export_steps", return_value=[Path("a.step"), Path("b.step")]):
        export_case.main([])
    assert capsys.readouterr().out.split() == ["a.step", "b.step"]


@pytest.mark.parametrize("target, name", [("coupons-hardware", "coupons_hardware.stl"), ("coupons-plate-wiring-engraving", "coupons_plate_wiring_engraving.stl")])
def test_a_coupon_plate_is_one_stl(target, name, tmp_path):
    with patch.object(export_coupon, "coupon_parts", return_value={"a": Box(1, 1, 1)}) as parts:
        path = export_coupon.export_coupon(target, tmp_path)
    parts.assert_called_once_with(target)
    assert path == tmp_path / name
    assert path.stat().st_size > 0


def test_every_coupon_plate_is_exported_and_printed(tmp_path, capsys):
    with patch.object(export_coupon, "coupon_parts", return_value={"a": Box(1, 1, 1)}):
        paths = export_coupon.export_coupons(tmp_path)
    assert [path.name for path in paths] == ["coupons_hardware.stl", "coupons_plate_wiring_engraving.stl"]
    with patch.object(export_coupon, "export_coupons", return_value=paths):
        export_coupon.main([])
    assert capsys.readouterr().out.split() == [str(path) for path in paths]


def test_the_entry_point_hands_the_arguments_to_the_command():
    with patch.dict(entry.COMMANDS, {"view": lambda argv: calls.append(argv)}):
        calls = []
        entry.main(["view", "transport", "--compact"])
    assert calls == [["transport", "--compact"]]


@pytest.mark.parametrize("argv", [[], ["build"]])
def test_the_entry_point_refuses_an_unknown_command(argv):
    with pytest.raises(SystemExit):
        entry.main(argv)
