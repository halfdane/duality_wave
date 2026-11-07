"""R-08, R-09, R-15."""

import shutil
import subprocess

import pytest
import yaml
from build123d import Vector

from duality_wave.layout import get_points
from tests import COMPACT_LAYOUT, ROOT, WAVE_LAYOUT
from tests.builds import make_outline


@pytest.mark.skipif(shutil.which("ergogen") is None, reason="ergogen is not installed")
@pytest.mark.parametrize("name", ["wave", "compact"])
def test_points_file_is_the_output_of_ergogen(name, tmp_path):  # R-08
    subprocess.run(["ergogen", str(ROOT / "ergogen" / f"{name}.yml"), "-o", str(tmp_path)], check=True, capture_output=True)
    made = yaml.safe_load((tmp_path / "points" / "points.yaml").read_text())
    committed = yaml.safe_load((ROOT / "ergogen" / f"{name}.points.yaml").read_text())
    assert committed == made, f"run `task layout` to update ergogen/{name}.points.yaml"


def test_the_loader_keeps_the_file_order_and_drops_skipped_points(tmp_path):  # R-09
    path = tmp_path / "points.yaml"
    path.write_text(yaml.safe_dump({
        "c": {"x": 7, "y": 8, "r": 9},
        "a": {"x": 1, "y": 2, "r": 3, "meta": {"skip": False}},
        "b": {"x": 4, "y": 5, "r": 6, "meta": {"skip": True}},
    }, sort_keys=False))
    points = get_points(path)
    assert list(points) == ["c", "a"]
    assert points["a"].p == Vector(1, 2) and points["a"].r == 3


@pytest.mark.parametrize("compact", [False, True], ids=["full", "compact"])
def test_keywell_outline_ignores_noise_in_the_last_digits(compact):  # R-15
    def keywell_outline(noise: float):
        points = get_points(COMPACT_LAYOUT if compact else WAVE_LAYOUT)
        for i, point in enumerate(points.values()):
            point.p = point.p + Vector(noise * ((i % 3) - 1), noise * ((i % 2) * 2 - 1))
        sketch = make_outline(compact, points=points).create_keywell_outline()
        return sketch.area, len(sketch.edges())

    area, edges = keywell_outline(0)
    for noise in (4e-8, -7e-8):
        noisy_area, noisy_edges = keywell_outline(noise)
        assert noisy_area == pytest.approx(area, abs=1e-3)
        assert noisy_edges == edges
