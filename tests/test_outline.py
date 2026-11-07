"""R-25, R-26, R-27, R-28, R-29, R-30."""

import math
import os
import time

import pytest
from build123d import Vector

from duality_wave.geometry2d import circle_face, close_concave, grow, overlap_area, rect_face, round_convex
from duality_wave.layout import get_points
from duality_wave.models.case_dimensions import CaseDimensions, CompactCaseDimensions
from duality_wave.models.choc import Choc
from duality_wave.models.keys import ErgoKeys
from duality_wave.models.outline import Outline, OutlineSpec
from tests import COMPACT_LAYOUT, WAVE_LAYOUT

PERF_FACTOR = float(os.environ.get("WAVE_PERF_FACTOR", "1"))
UNBRIDGED = OutlineSpec(bridge_gap=0, cutout_concave_radius=0, cutout_convex_radius=0)


def make_outline(compact: bool, spec: OutlineSpec = OutlineSpec()) -> Outline:
    dimensions = CompactCaseDimensions if compact else CaseDimensions
    keys = ErgoKeys(get_points(COMPACT_LAYOUT if compact else WAVE_LAYOUT))
    return Outline(Choc(), keys, wall_thickness=dimensions.wall_thickness, additional_top_space=22 if compact else 10, spec=spec)


@pytest.fixture(scope="module", params=[False, True], ids=["full", "compact"])
def outline(request) -> Outline:
    return make_outline(request.param)


def area_cut(face, other) -> float:
    rest = face.cut(other)
    return sum(part.area for part in rest.faces()) if rest is not None else 0.0


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


def test_the_cutout_has_no_gap_narrower_than_twice_the_inner_radius(outline):  # R-25
    cutout = outline.keywell_sketch.faces()
    assert len(cutout) == 1
    radius = outline.spec.cutout_concave_radius
    assert grow(grow(cutout[0], radius), -radius).area - cutout[0].area < 0.05


@pytest.mark.parametrize("compact", [False, True], ids=["full", "compact"])
def test_without_bridging_the_cutout_has_such_gaps(compact):  # R-25
    cutout = make_outline(compact, UNBRIDGED).keywell_sketch.faces()[0]
    assert grow(grow(cutout, 2), -2).area - cutout.area > 20


def test_the_corners_of_the_cutout_are_round(outline):  # R-26
    cutout = outline.keywell_sketch.faces()[0]
    assert close_concave(cutout, outline.spec.cutout_concave_radius).area == pytest.approx(cutout.area, abs=0.05)
    assert round_convex(cutout, outline.spec.cutout_convex_radius).area == pytest.approx(cutout.area, abs=0.05)


def test_the_outlines_have_no_kinks(outline):  # R-26
    assert kinks(outline.sketch.faces()[0]) == []
    for offset_by in (-outline.wall_thickness, -outline.wall_thickness - 0.2):
        assert kinks(outline.create_inner_outline(offset_by).faces()[0]) == []


def test_the_keycaps_fit_into_the_cutout_and_the_cutout_into_the_cavity(outline):  # R-27
    cutout = outline.keywell_sketch.faces()[0]
    cavity = outline.create_inner_outline(-outline.wall_thickness).faces()[0]
    for key in outline.keys.keys:
        cap = rect_face(key.p, outline.switch.cap.d.X, outline.switch.cap.d.Y, key.r)
        assert overlap_area(cap, cutout) == pytest.approx(cap.area, abs=1e-6), f"cap at {key.p}"
    assert overlap_area(cutout, cavity) == pytest.approx(cutout.area, abs=0.2)


def test_the_outline_holds_the_cells_of_all_keys(outline):  # R-27
    face = outline.sketch.faces()[0]
    round_off = 2 * (1 - math.pi / 4) * outline.spec.corner_radius**2
    for scale, keys in ((1.5, outline.keys.finger_keys), (2, outline.keys.thumb_keys)):
        for key in keys:
            cell = rect_face(key.p, scale * outline.d_x, scale * outline.d_y, key.r)
            assert cell.area - overlap_area(cell, face) <= round_off + 1e-3, f"cell at {key.p}"


def test_the_notch_for_the_trackpad_exists_only_where_it_fits():  # R-28
    full, compact = make_outline(False), make_outline(True)
    assert full.has_cirque_notch and not compact.has_cirque_notch
    assert full.cirque_recess_position.X == pytest.approx(32.0578, abs=1e-3)
    notch = circle_face(full.cirque_recess_position, full.cirque_recess_radius)
    assert overlap_area(notch, full.sketch.faces()[0]) < 1
    assert overlap_area(notch, full.keywell_sketch.faces()[0]) == 0


def test_the_sweep_radius_is_a_fraction_of_the_wall_above_the_thumbs(outline):  # R-29
    wall = outline.top - outline.thumb_top.Y
    assert outline.sweep_radius == pytest.approx(outline.spec.sweep_ratio * wall)
    assert outline.sweep_radius > outline.spec.corner_radius


def test_the_closing_keeps_the_shape_of_the_old_tangent_arc_on_the_full_variant():  # R-29
    classic_area = 9138.96
    assert make_outline(False, OutlineSpec(corner_radius=1.0)).sketch.area == pytest.approx(classic_area, abs=2)


@pytest.mark.parametrize("compact", [False, True], ids=["full", "compact"])
def test_building_an_outline_stays_inside_its_time_budget(compact):  # R-30
    start = time.perf_counter()
    outline = make_outline(compact)
    outline.create_inner_outline(-outline.wall_thickness - 0.2)
    assert time.perf_counter() - start < 0.4 * PERF_FACTOR


def test_faces_from_the_helpers_look_up():
    from duality_wave.geometry2d import bridge_gaps, polygon_face

    clockwise = polygon_face([(0, 0), (0, 10), (10, 10), (10, 0)])
    assert clockwise.normal_at().Z > 0
    assert circle_face((0, 0), 3).normal_at().Z > 0
    assert all(face.normal_at().Z > 0 for face in bridge_gaps([rect_face((0, 0), 10, 10), rect_face((12, 0), 10, 10)], 4.4))
