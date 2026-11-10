"""R-01, R-03, R-04, R-05, R-10, R-11, R-12 and the rule that every requirement has a test."""

import re

import pytest
from build123d import Vector, export_step, import_step

from duality_wave.models.xiao import Xiao
from tests import PERF_FACTOR, ROOT
from tests.builds import PARTS

SPEC = ROOT / "docs" / "SPEC.md"
ID = re.compile(r"R-\d{2}")
STAGE_LIMITS = {"keywell": 1.2, "keyplate": 1.6, "bottom": 0.7, "finish_left": 5.0, "finish_right": 5.0}


def spec_ids() -> set[str]:
    return {m.group(0) for line in SPEC.read_text().splitlines() if (m := re.match(r"R-\d{2}(?=:)", line))}


def test_every_requirement_has_a_test_and_every_cited_requirement_exists():
    cited = set()
    for path in (ROOT / "tests").glob("*.py"):
        cited |= set(ID.findall(path.read_text()))
    ids = spec_ids()
    assert ids - cited == set(), f"requirements without a test: {sorted(ids - cited)}"
    assert cited - ids == set(), f"tests cite unknown requirements: {sorted(cited - ids)}"


def test_a_test_without_the_integration_marker_cannot_build_a_case():
    from duality_wave.case import WaveCase

    with pytest.raises(AssertionError, match="integration"):
        WaveCase(None, None, None, None)


@pytest.mark.integration
class TestFullCase:

    def test_each_half_has_a_switch_for_every_key_of_the_layout(self, full):  # R-01
        for side in (full.left, full.right):
            for key in full.ctx.keys.keys:
                position = key.p if side is full.left else Vector(full.ctx.dims.right_side_offset - key.p.X, key.p.Y)
                assert side.accessories.switches.is_inside(Vector(position.X, position.Y, full.ctx.switch.base.d.Z / 2)), f"no switch at {key.p}"

    def test_every_part_is_one_valid_solid(self, full):  # R-03
        for side in (full.left, full.right):
            for name in PARTS:
                part = getattr(side, name)
                assert part.is_valid, name
                assert len(part.solids()) == 1, name

    def test_every_face_of_every_part_can_be_meshed(self, full):  # R-44
        unmeshable = []
        parts = [(f"{name}_{side.side.name}", getattr(side, name)) for side in (full.left, full.right) for name in PARTS]
        parts.append(("magnet_spacer", full.magnet_spacer))
        for name, part in parts:
            for index, face in enumerate(part.faces()):
                try:
                    face.tessellate(0.01, 0.2)
                except AttributeError:
                    unmeshable.append((name, index, face.geom_type.name, round(face.area, 4)))
        assert unmeshable == []

    def test_every_step_file_reads_back_as_the_same_solid(self, full, tmp_path):  # R-45
        parts = [(f"{name}_{side.side.name}", getattr(side, name)) for side in (full.left, full.right) for name in PARTS]
        parts.append(("magnet_spacer", full.magnet_spacer))
        for name, part in parts:
            path = tmp_path / f"{name}.step"
            export_step(part, str(path))
            back = import_step(str(path))
            assert len(back.solids()) == 1, name
            assert len(back.faces()) == len(part.faces()), name
            assert back.volume == pytest.approx(part.volume, rel=1e-6), name

    def test_parts_span_the_expected_heights(self, full):  # R-04
        dims = full.ctx.dims
        for side in (full.left, full.right):
            keywell, keyplate, bottom = (getattr(side, name).bounding_box() for name in PARTS)
            assert keywell.max.Z == pytest.approx(dims.above_z, abs=1e-3)
            assert keywell.min.Z == pytest.approx(-dims.below_z, abs=1e-3)
            assert keyplate.max.Z == pytest.approx(0, abs=1e-3)
            assert keyplate.min.Z == pytest.approx(-dims.keyplate_z, abs=1e-3)
            assert bottom.min.Z == pytest.approx(-dims.below_z, abs=1e-3)
            # the bump under the reset button of the XIAO rises above the plate, up to the button
            reset_bump_top = dims.xiao_position.Z - Xiao.dims.d.Z - Xiao.components.reset_button_d.d.Z
            assert bottom.max.Z == pytest.approx(max(-dims.keyplate_z, reset_bump_top), abs=1e-3)

    def test_the_keyplate_fits_inside_the_keywell(self, full):  # R-05
        for side in (full.left, full.right):
            keywell, keyplate = side.keywell.bounding_box(), side.keyplate.bounding_box()
            assert keyplate.min.X > keywell.min.X and keyplate.max.X < keywell.max.X
            assert keyplate.min.Y > keywell.min.Y and keyplate.max.Y < keywell.max.Y

    @pytest.mark.perf
    def test_the_build_stays_inside_its_time_budget(self, full):  # R-10, R-12
        assert full.timings.total <= 12 * PERF_FACTOR
        for stage, limit in STAGE_LIMITS.items():
            assert full.timings.get(stage, 0) <= limit * PERF_FACTOR, stage


@pytest.mark.integration
class TestCompactCase:

    def test_every_part_is_one_valid_solid(self, compact):  # R-03
        for name in PARTS:
            part = getattr(compact.left, name)
            assert part.is_valid, name
            assert len(part.solids()) == 1, name

    def test_parts_span_the_expected_heights(self, compact):  # R-04
        dims = compact.ctx.dims
        assert compact.left.keywell.bounding_box().max.Z == pytest.approx(dims.above_z, abs=1e-3)
        assert compact.left.bottom.bounding_box().min.Z == pytest.approx(-dims.below_z, abs=1e-3)

    @pytest.mark.perf
    def test_the_build_stays_inside_its_time_budget(self, compact):  # R-11
        assert compact.timings.total <= 3 * PERF_FACTOR
