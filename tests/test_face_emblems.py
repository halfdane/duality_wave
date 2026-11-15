"""R-46."""

import pytest
from build123d import Face, Solid, Vector

from duality_wave.builders.export import print_transform
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


def test_the_invader_has_no_gap_between_its_pixels():  # R-46
    pitch = 1.25
    sketch = SpaceInvader(pitch, gap=0).sketch
    assert sum(face.area for face in sketch.faces()) == pytest.approx(PIXELS * pitch * pitch)
    assert len(sketch.faces()) < PIXELS
