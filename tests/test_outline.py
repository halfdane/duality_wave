"""R-25, R-26, R-27, R-28, R-29 and the outline part of R-12."""

import time
from collections.abc import Callable
from dataclasses import dataclass

import pytest
from build123d import Vector

from duality_wave.geometry2d import bridge_gaps, circle_face, close_concave, grow, overlap_area, polygon_face, rect_face, round_convex
from duality_wave.layout import Point, get_points
from duality_wave.models.outline import Outline, OutlineSpec
from tests import COMPACT_LAYOUT, PERF_FACTOR, WAVE_LAYOUT
from tests.builds import make_outline


def split_thumbs(points: dict[str, Point]) -> tuple[dict[str, Point], dict[str, Point]]:
    fingers = {name: point for name, point in points.items() if not name.startswith("thumb")}
    return fingers, {name: point for name, point in points.items() if name.startswith("thumb")}


def with_extra_column(points: dict[str, Point], pitch: float = 18) -> dict[str, Point]:
    """A copy of the last finger column, one pitch further out."""
    fingers, thumbs = split_thumbs(points)
    last = list(fingers)[-1].split("_")[1]
    extra = {
        name.replace(f"_{last}_", "_extra_"): Point(p=point.p + Vector(pitch, 0), r=point.r)
        for name, point in fingers.items() if f"_{last}_" in name}
    return {**fingers, **extra, **thumbs}


def with_extra_row(points: dict[str, Point], pitch: float = 17) -> dict[str, Point]:
    """A copy of the top key of every finger column, one pitch further up."""
    fingers, _ = split_thumbs(points)
    tops = {tuple(name.split("_")[:2]): point for name, point in fingers.items()}
    extra = {f"{cluster}_{column}_extra": Point(p=point.p + Vector(0, pitch), r=point.r) for (cluster, column), point in tops.items()}
    return {**points, **extra}


@dataclass(frozen=True)
class Case:
    compact: bool
    spec: OutlineSpec = OutlineSpec()
    edit: Callable | None = None

    def build(self) -> Outline:
        points = get_points(COMPACT_LAYOUT if self.compact else WAVE_LAYOUT)
        return make_outline(self.compact, self.spec, self.edit(points) if self.edit else None)


CASES = {
    "full": Case(False),
    "compact": Case(True),
    "full-small-radius": Case(False, OutlineSpec(corner_radius=1.0)),
    "full-big-radius-and-gap": Case(False, OutlineSpec(corner_radius=6.0, bridge_gap=8.0, cutout_concave_radius=1.5)),
    "compact-big-gap": Case(True, OutlineSpec(corner_radius=2.0, bridge_gap=8.0)),
    "full-extra-column": Case(False, edit=with_extra_column),
    "full-extra-row": Case(False, edit=with_extra_row),
}


@pytest.fixture(scope="module", params=list(CASES), ids=list(CASES))
def outline(request) -> Outline:
    return CASES[request.param].build()


def kinks(face) -> list[tuple[float, float]]:
    """The corners of the outer wire where the direction jumps by more than a degree."""
    edges = face.outer_wire().edges()
    found = []
    for vertex in face.outer_wire().vertices():
        point = Vector(vertex.X, vertex.Y, 0)
        directions = []
        for edge in edges:
            if (edge.position_at(0) - point).length < 1e-6:
                directions.append(edge.tangent_at(0))
            elif (edge.position_at(1) - point).length < 1e-6:
                directions.append(-edge.tangent_at(1))
        if len(directions) == 2 and directions[0].get_angle(directions[1]) < 179:
            found.append((round(point.X, 1), round(point.Y, 1)))
    return found


def test_keycaps_and_switches_lie_inside_the_cutout(outline):  # R-27
    cutout = outline.keywell_sketch.faces()
    for key in outline.keys.keys:
        for box in (outline.switch.cap.d, outline.switch.above.d):
            footprint = rect_face(key.p, box.X, box.Y, key.r)
            overlap = sum(overlap_area(footprint, region) for region in cutout)
            assert overlap == pytest.approx(footprint.area, rel=1e-6), f"key at {key.p}"


def test_the_cutout_lies_inside_the_cavity(outline):  # R-27
    cavity = outline.create_inner_outline(-outline.wall_thickness).faces()[0]
    for cutout in outline.keywell_sketch.faces():
        assert overlap_area(cutout, cavity) == pytest.approx(cutout.area, rel=1e-6)


def test_the_outlines_have_no_kinks(outline):  # R-26
    assert kinks(outline.sketch.faces()[0]) == []
    for offset_by in (-outline.wall_thickness, -outline.wall_thickness - 0.2):
        assert kinks(outline.create_inner_outline(offset_by).faces()[0]) == []


def test_the_corners_of_the_cutout_are_round(outline):  # R-26
    spec = outline.spec
    for cutout in outline.keywell_sketch.faces():
        assert sum(f.area for f in close_concave(cutout, spec.cutout_concave_radius)) == pytest.approx(cutout.area, abs=0.05)
        assert sum(f.area for f in round_convex(cutout, spec.cutout_convex_radius)) == pytest.approx(cutout.area, abs=0.05)


def test_the_sweep_is_an_arc_on_the_right_wall(outline):  # R-29
    wall = outline.top - outline.thumb_top.Y
    assert outline.sweep_radius == pytest.approx(outline.spec.sweep_ratio * wall)
    radii = [edge.radius for edge in outline.sketch.faces()[0].outer_wire().edges() if edge.geom_type.name == "CIRCLE"]
    assert any(radius == pytest.approx(outline.sweep_radius, rel=1e-3) for radius in radii)


def test_a_notch_for_the_trackpad_keeps_clear_of_the_cutout(outline):  # R-28
    if not outline.has_cirque_notch:
        return
    notch = circle_face(outline.cirque_recess_position, outline.cirque_recess_radius)
    assert overlap_area(notch, outline.keywell_sketch.faces()[0]) == 0
    assert overlap_area(notch, outline.sketch.faces()[0]) < 0.01 * notch.area


def test_the_full_variant_has_a_notch_for_the_trackpad():  # R-28
    assert CASES["full"].build().has_cirque_notch


def test_a_notch_is_cut_only_where_the_thumb_is_far_enough_from_the_keys():  # R-28
    first = make_outline()
    width, height = 1.5 * first.d_x, 1.5 * first.d_y
    near = {"a_0_0": Point(Vector(0, 0)), "a_1_0": Point(Vector(width + 2, 0)), "thumb_0_0": Point(Vector(30, -3 * height))}
    far = {**near, "thumb_0_0": Point(Vector(30 + 2 * first.cirque_recess_radius, -3 * height))}
    # the thumb key sits far below the fingers on purpose, which leaves the body a thin neck there.
    # corner rounding is not what this test is about, so it is turned off to keep that neck intact.
    spec = OutlineSpec(corner_radius=0)
    assert not make_outline(spec=spec, points=near).has_cirque_notch
    outline = make_outline(spec=spec, points=far)
    assert outline.has_cirque_notch
    notch = circle_face(outline.cirque_recess_position, outline.cirque_recess_radius)
    assert overlap_area(notch, outline.sketch.faces()[0]) < 0.01 * notch.area


def test_a_gap_narrower_than_the_bridge_gap_is_closed_and_a_wider_one_is_not():  # R-25
    spec = OutlineSpec()
    first = make_outline(spec=spec)
    width, height = 1.5 * first.d_x, 1.5 * first.d_y

    def regions(gap: float) -> int:
        points = {
            "a_0_0": Point(Vector(0, 0)),
            "a_1_0": Point(Vector(width + gap, 0)),
            "thumb_0_0": Point(Vector((width + gap) / 2, -3 * height)),
        }
        return len(make_outline(spec=spec, points=points).keywell_sketch.faces())

    assert regions(0.5 * spec.bridge_gap) == regions(1.5 * spec.bridge_gap) - 1


def test_a_closed_gap_has_straight_edges():  # R-25
    gap = OutlineSpec().bridge_gap
    cells = [rect_face((0, 0), 10, 10), rect_face((10 + gap / 2, 0), 10, 10)]
    (bridged,) = bridge_gaps(cells, gap)
    assert bridged.area > sum(cell.area for cell in cells)
    assert all(edge.geom_type.name == "LINE" for edge in bridged.outer_wire().edges())


def test_the_walls_have_one_thickness_around_the_rounded_corners(outline):  # R-26
    if outline.spec.corner_radius < 2 * outline.wall_thickness:
        pytest.skip("the corners are too tight to stay concentric")
    inner = outline.create_inner_outline(-outline.wall_thickness).faces()[0]
    assert inner.area == pytest.approx(grow(outline._outer_face, -outline.wall_thickness).area, abs=1e-6)


@pytest.mark.perf
def test_building_an_outline_stays_inside_its_time_budget():  # R-12
    start = time.perf_counter()
    outline = make_outline()
    outline.create_inner_outline(-outline.wall_thickness - 0.2)
    assert time.perf_counter() - start < 0.4 * PERF_FACTOR


def test_faces_from_the_helpers_look_up():
    clockwise = polygon_face([(0, 0), (0, 10), (10, 10), (10, 0)])
    assert clockwise.normal_at().Z > 0
    assert circle_face((0, 0), 3).normal_at().Z > 0
    gap = OutlineSpec().bridge_gap
    assert all(face.normal_at().Z > 0 for face in bridge_gaps([rect_face((0, 0), 10, 10), rect_face((10 + gap / 2, 0), 10, 10)], gap))
