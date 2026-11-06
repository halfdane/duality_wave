"""R-08, R-09, R-15."""

import shutil
import subprocess

import pytest
import yaml
from build123d import Vector

from duality_wave.layout import get_points
from duality_wave.models.case_dimensions import CompactCaseDimensions
from duality_wave.models.choc import Choc
from duality_wave.models.keys import ErgoKeys
from duality_wave.models.outline import Outline
from tests import COMPACT_LAYOUT, ROOT, WAVE_LAYOUT

WAVE_KEYS = [
    "matrix_pinky_bottom", "matrix_pinky_home", "matrix_pinky_top",
    "matrix_ring_bottom", "matrix_ring_home", "matrix_ring_top",
    "matrix_middle_bottom", "matrix_middle_home", "matrix_middle_top",
    "matrix_index_bottom", "matrix_index_home", "matrix_index_top",
    "matrix_inner_bottom", "matrix_inner_home", "matrix_inner_top",
    "thumb_middle", "thumb_reachy",
]


@pytest.mark.skipif(shutil.which("ergogen") is None, reason="ergogen is not installed")
@pytest.mark.parametrize("name", ["wave", "compact"])
def test_points_file_is_the_output_of_ergogen(name, tmp_path):  # R-08
    subprocess.run(["ergogen", str(ROOT / "ergogen" / f"{name}.yml"), "-o", str(tmp_path)], check=True, capture_output=True)
    made = yaml.safe_load((tmp_path / "points" / "points.yaml").read_text())
    committed = yaml.safe_load((ROOT / "ergogen" / f"{name}.points.yaml").read_text())
    assert committed == made, f"run `task layout` to update ergogen/{name}.points.yaml"


def test_wave_points_keep_the_file_order():  # R-09
    points = get_points(WAVE_LAYOUT)
    assert list(points) == WAVE_KEYS
    first = points["matrix_pinky_bottom"]
    assert (first.p.X, first.p.Y, first.r) == (0, 0, 8)
    assert points["matrix_pinky_home"].p.Y > first.p.Y


def test_compact_points():  # R-09
    assert len(get_points(COMPACT_LAYOUT)) == 4


def test_skipped_points_are_dropped(tmp_path):  # R-09
    path = tmp_path / "points.yaml"
    path.write_text(yaml.safe_dump({
        "a": {"x": 1, "y": 2, "r": 3, "meta": {"skip": False}},
        "b": {"x": 4, "y": 5, "r": 6, "meta": {"skip": True}},
    }))
    points = get_points(path)
    assert list(points) == ["a"]
    assert points["a"].p == Vector(1, 2) and points["a"].r == 3


@pytest.mark.parametrize("name", ["wave", "compact"])
def test_keywell_outline_ignores_noise_in_the_last_digits(name):  # R-15
    layout = WAVE_LAYOUT if name == "wave" else COMPACT_LAYOUT

    def keywell_outline(noise: float):
        points = get_points(layout)
        for i, point in enumerate(points.values()):
            point.p = point.p + Vector(noise * ((i % 3) - 1), noise * ((i % 2) * 2 - 1))
        switch = Choc()
        outline = Outline(
            switch=switch, keys=ErgoKeys(points), wall_thickness=CompactCaseDimensions.wall_thickness, additional_top_space=22)
        sketch = outline.create_keywell_outline()[0]
        return sketch.area, len(sketch.edges())

    area, edges = keywell_outline(0)
    for noise in (4e-8, -7e-8):
        noisy_area, noisy_edges = keywell_outline(noise)
        assert noisy_area == pytest.approx(area, abs=1e-3)
        assert noisy_edges == edges
