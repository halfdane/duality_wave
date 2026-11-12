"""R-46."""

import pytest
from build123d import Face, Solid, Vector, export_step, import_step

from duality_wave.builders.export import print_pose, print_pose_emblem, print_transform
from duality_wave.models.space_invader import PATTERN, SpaceInvader

PIXELS = sum(map(sum, PATTERN))
EMBLEM_PARTS = ("keywell", "bottom")


def outside_volume(emblem, body) -> float:
    """The volume of the emblem that is not material of the body."""
    return sum(solid.cut(body).volume for solid in emblem.solids())


def lost_volume(emblem, body, margin: float, face_z: float, direction: float) -> float:
    """The volume of the emblem footprint, grown by margin and as deep as the emblem plus margin, that is not material of the body.

    direction is +1 when the emblem rises from the face and -1 when it hangs from it.
    """
    lost = 0.0
    for solid in emblem.solids():
        box = solid.bounding_box()
        depth = box.max.Z - box.min.Z + margin
        for face in solid.faces().filter_by(lambda f: abs(f.normal_at().Z) > 0.99 and abs(f.center().Z - face_z) < 1e-6):
            grown = Face(face.outer_wire().offset_2d(margin))
            grown = grown if grown.normal_at().Z > 0 else -grown
            lost += Solid.extrude(grown, Vector(0, 0, direction * depth)).cut(body).volume
    return lost


@pytest.mark.integration
class TestFullCase:

    @pytest.mark.parametrize("name", EMBLEM_PARTS)
    def test_the_emblem_lies_inside_its_part(self, full, name):  # R-46
        for side in (full.left, full.right):
            emblem = side.emblems[name]
            assert emblem.is_valid
            assert outside_volume(emblem, getattr(side, name)) == pytest.approx(0, abs=1e-4)

    def test_the_emblem_keeps_min_wall_of_material_around_and_behind_it(self, full):  # R-46
        dims = full.ctx.dims
        margin = dims.print_profile.min_wall
        for side in (full.left, full.right):
            assert lost_volume(side.emblems["keywell"], side.keywell, margin, dims.above_z, -1) == pytest.approx(0, abs=1e-3)
            assert lost_volume(side.emblems["bottom"], side.bottom, margin, -dims.below_z, 1) == pytest.approx(0, abs=1e-3)

    @pytest.mark.parametrize("name", EMBLEM_PARTS)
    def test_the_emblem_is_flush_with_the_bed_face_and_layers_deep(self, full, name):  # R-46
        depth = full.ctx.dims.print_profile.emblem_depth
        for side in (full.left, full.right):
            body = getattr(side, name)
            transform = print_transform(name, body)
            box = side.emblems[name].moved(transform).bounding_box()
            assert box.min.Z == pytest.approx(0, abs=1e-6)
            assert box.max.Z == pytest.approx(depth, abs=1e-6)

    def test_the_right_emblems_are_the_left_emblems_mirrored(self, full):  # R-46
        offset = full.ctx.dims.right_side_offset
        for name in EMBLEM_PARTS:
            left, right = full.left.emblems[name], full.right.emblems[name]
            assert right.bounding_box().center().X == pytest.approx(offset - left.bounding_box().center().X, abs=1e-6)
            assert right.volume == pytest.approx(left.volume, rel=1e-6)

    @pytest.mark.parametrize("name", EMBLEM_PARTS)
    def test_the_emblem_file_shares_the_frame_of_the_part_file(self, full, name, tmp_path):  # R-46
        body, emblem = getattr(full.left, name), full.left.emblems[name]
        body_path, emblem_path = tmp_path / f"{name}.step", tmp_path / f"{name}_emblem.step"
        export_step(print_pose(name, body), str(body_path))
        export_step(print_pose_emblem(name, body, emblem), str(emblem_path))
        posed_body, posed_emblem = import_step(str(body_path)), import_step(str(emblem_path))
        assert len(posed_body.solids()) == 1
        assert len(posed_emblem.solids()) == len(emblem.solids())
        assert posed_emblem.volume == pytest.approx(emblem.volume, rel=1e-6)
        assert outside_volume(posed_emblem, posed_body) == pytest.approx(0, abs=1e-4)


@pytest.mark.integration
class TestCompactCase:

    @pytest.mark.parametrize("name", EMBLEM_PARTS)
    def test_the_emblem_lies_inside_its_part(self, compact, name):  # R-46
        assert outside_volume(compact.left.emblems[name], getattr(compact.left, name)) == pytest.approx(0, abs=1e-4)

    def test_the_emblem_keeps_min_wall_of_material_around_and_behind_it(self, compact):  # R-46
        dims = compact.ctx.dims
        margin = dims.print_profile.min_wall
        side = compact.left
        assert lost_volume(side.emblems["keywell"], side.keywell, margin, dims.above_z, -1) == pytest.approx(0, abs=1e-3)
        assert lost_volume(side.emblems["bottom"], side.bottom, margin, -dims.below_z, 1) == pytest.approx(0, abs=1e-3)


def test_the_invader_has_no_gap_between_its_pixels():  # R-46
    pitch = 1.25
    sketch = SpaceInvader(pitch, gap=0).sketch
    assert sum(face.area for face in sketch.faces()) == pytest.approx(PIXELS * pitch * pitch)
    assert len(sketch.faces()) < PIXELS
