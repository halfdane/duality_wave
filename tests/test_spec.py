"""R-01, R-03, R-04, R-05, R-10, R-11, R-12, R-13, R-14."""

import os
import re

import pytest

from tests import ROOT
from tests.builds import PARTS, build_case

SPEC = ROOT / "docs" / "SPEC.md"
ID = re.compile(r"R-\d{2}")
PERF_FACTOR = float(os.environ.get("WAVE_PERF_FACTOR", "1"))
STAGE_LIMITS = {"keywell": 9, "keyplate": 7, "bottom": 2, "finish_left": 8, "finish_right": 8}


def spec_ids() -> set[str]:
    return {m.group(0) for line in SPEC.read_text().splitlines() if (m := re.match(r"R-\d{2}(?=:)", line))}


def test_every_requirement_has_a_test_and_every_cited_requirement_exists():  # R-14
    cited = set()
    for path in (ROOT / "tests").glob("*.py"):
        cited |= set(ID.findall(path.read_text()))
    ids = spec_ids()
    assert ids - cited == set(), f"requirements without a test: {sorted(ids - cited)}"
    assert cited - ids == set(), f"tests cite unknown requirements: {sorted(cited - ids)}"


def test_a_test_without_the_slow_marker_cannot_build_a_case():  # R-13
    from duality_wave.case import WaveCase

    with pytest.raises(AssertionError, match="slow"):
        WaveCase(None, None, None, None)


@pytest.fixture(scope="module")
def full_case():
    return build_case(debug=False)[0]


@pytest.fixture(scope="module")
def compact_case():
    return build_case(debug=False, both_sides=False, compact=True)[0]


@pytest.mark.slow
class TestFullCase:

    def test_each_half_has_17_keys(self, full_case):  # R-01
        assert len(full_case.ctx.keys.keys) == 17

    def test_every_part_is_one_valid_solid(self, full_case):  # R-03
        for side in (full_case.left, full_case.right):
            for name in PARTS:
                part = getattr(side, name)
                assert part.is_valid, name
                assert len(part.solids()) == 1, name

    def test_parts_span_the_expected_heights(self, full_case):  # R-04
        dims = full_case.ctx.dims
        for side in (full_case.left, full_case.right):
            keywell, keyplate, bottom = (getattr(side, name).bounding_box() for name in PARTS)
            assert keywell.max.Z == pytest.approx(dims.above_z, abs=1e-3)
            assert keywell.min.Z == pytest.approx(-dims.below_z, abs=1e-3)
            assert keyplate.max.Z == pytest.approx(0, abs=1e-3)
            assert keyplate.min.Z == pytest.approx(-dims.keyplate_z, abs=1e-3)
            assert bottom.min.Z == pytest.approx(-dims.below_z, abs=1e-3)
            assert bottom.max.Z == pytest.approx(-dims.keyplate_z, abs=1e-3)

    def test_the_keyplate_fits_inside_the_keywell(self, full_case):  # R-05
        for side in (full_case.left, full_case.right):
            keywell, keyplate = side.keywell.bounding_box(), side.keyplate.bounding_box()
            assert keyplate.min.X > keywell.min.X and keyplate.max.X < keywell.max.X
            assert keyplate.min.Y > keywell.min.Y and keyplate.max.Y < keywell.max.Y

    def test_the_build_stays_inside_its_time_budget(self, full_case):  # R-10, R-12
        assert full_case.timings.total <= 30 * PERF_FACTOR
        for stage, limit in STAGE_LIMITS.items():
            assert full_case.timings.get(stage, 0) <= limit * PERF_FACTOR, stage


@pytest.mark.slow
class TestCompactCase:

    def test_every_part_is_one_valid_solid(self, compact_case):  # R-03
        for name in PARTS:
            part = getattr(compact_case.left, name)
            assert part.is_valid, name
            assert len(part.solids()) == 1, name

    def test_parts_span_the_expected_heights(self, compact_case):  # R-04
        dims = compact_case.ctx.dims
        assert compact_case.left.keywell.bounding_box().max.Z == pytest.approx(dims.above_z, abs=1e-3)
        assert compact_case.left.bottom.bounding_box().min.Z == pytest.approx(-dims.below_z, abs=1e-3)

    def test_the_build_stays_inside_its_time_budget(self, compact_case):  # R-11
        assert compact_case.timings.total <= 15 * PERF_FACTOR
