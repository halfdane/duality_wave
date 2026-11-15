"""Guards for the tests themselves. They keep new tests small, fast and free of the current numbers of the design."""

import ast
import re
from functools import cache
from pathlib import Path

from tests import ROOT

THIS_FILE = Path(__file__).name
TEST_FILES = sorted(path for path in (ROOT / "tests").glob("test_*.py") if path.name != THIS_FILE)

ESCAPE = "# literal-ok:"
DESIGN_NAMES = {
    "make_inputs", "make_context", "build_case", "full", "compact", "quiet",
    "Choc", "CaseDimensions", "CompactCaseDimensions", "PrintProfile",
}
TOLERANCE_KEYWORDS = {"abs", "rel", "delta", "places", "atol", "rtol"}
SMALL_INTS = {-2, -1, 0, 1, 2}

# TEMPORARY: unit tests over the CPU budget that wait for a fix. Fix a test, remove its marker and delete its line.
# The marker and this list go away when the list is empty. Do not add a line.
SLOW_BASELINE = {
    "test_coupons_engraving.py::test_a_slab_is_one_valid_solid_as_high_as_the_keywell_wall",
    "test_coupons_engraving.py::test_the_roof_is_the_side_that_prints_last_and_slopes_when_asked",
    "test_coupons_engraving.py::test_the_top_row_of_an_emblem_is_next_to_the_bed_and_the_pockets_have_the_asked_depth",
    "test_coupons_engraving.py::test_the_wiring_plate_has_a_slab_for_every_depth_and_roof_and_fits_on_a_small_bed",
    "test_wall_engraving.py::test_the_pocket_is_in_the_wall_and_as_deep_as_asked",
    "test_wall_engraving.py::test_the_roof_slopes_at_45_degrees",
    "test_wiring.py::test_no_wire_comes_near_a_contact_it_does_not_serve_or_runs_beside_another_net",
    "test_wiring_editor.py::test_a_corner_without_an_arc_is_sharp_and_does_not_break_the_checks",
    "test_wiring_editor.py::test_a_radius_is_written_only_for_a_corner_that_has_one",
    "test_wiring_editor.py::test_saving_writes_the_moved_vertex_keeps_a_backup_and_leaves_the_rest",
    "test_wiring_editor.py::test_the_checks_of_the_editor_give_the_place_of_each_problem",
    "test_wiring_editor.py::test_the_file_survives_a_round_trip_through_the_vertices_of_the_editor",
    "test_wiring_editor.py::test_tidy_takes_away_repeated_and_straight_vertices_and_keeps_the_ends_and_the_corners",
    "test_zstack.py::test_a_spacer_disc_fills_the_pocket_and_the_keyplate_carries_it",
    "test_zstack.py::test_the_top_of_the_keycap_is_a_dish_that_is_highest_at_the_corners",
}

# Tests that already compare real design values with a literal number. Fix a test and delete its line. Do not add a line.
LITERAL_BASELINE = {
    "test_builders.py::ThumbZoneTests.test_the_corners_are_round",
    "test_coupons.py::CouponTests.test_battery_pockets_are_open_upwards_and_differ_by_their_clearance",
    "test_coupons.py::CouponTests.test_the_second_plate_holds_the_wiring_and_the_plate_fit_as_separate_solids",
    "test_spec.py::TestCompactCase.test_the_build_stays_inside_its_time_budget",
    "test_spec.py::TestFullCase.test_the_build_stays_inside_its_time_budget",
    "test_wave_generator.py::FeatureTests.test_magnet_recess_cutter_holds_two_magnets",
    "test_wave_generator.py::SwitchPostCutoutTests.test_physical_footprint_on_both_halves",
    "test_zstack.py::test_a_height_snaps_to_whole_layers",
    "test_zstack.py::test_a_post_of_length_zero_does_not_exist",
    "test_zstack.py::test_the_longest_of_contact_and_side_post_sets_the_depth_below_the_housing",
    "test_zstack.py::test_the_top_of_the_keycap_is_a_dish_that_is_highest_at_the_corners",
}


def definitions(tree):
    """Every function and class as (qualified name, node, enclosing class)."""

    def visit(node, prefix, owner):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                qualname = prefix + child.name
                yield qualname, child, owner
                yield from visit(child, qualname + ".", child if isinstance(child, ast.ClassDef) else owner)
            else:
                yield from visit(child, prefix, owner)

    yield from visit(tree, "", None)


def slow_marked(source: str, filename: str) -> set[str]:
    tree = ast.parse(source)
    marked, decorated = set(), set()
    for qualname, node, _ in definitions(tree):
        for decorator in node.decorator_list:
            for part in ast.walk(decorator):
                if isinstance(part, ast.Attribute) and part.attr == "slow":
                    marked.add(f"{filename}::{qualname}")
                    decorated.add(id(part))
    elsewhere = any(isinstance(n, ast.Attribute) and n.attr == "slow" and id(n) not in decorated for n in ast.walk(tree))
    return marked | ({f"{filename}::<slow outside a decorator>"} if elsewhere else set())


def has_escape(lines: list[str], node) -> bool:
    return any(line.partition(ESCAPE)[2].strip() for line in lines[node.lineno - 1:node.end_lineno])


def literal_numbers(node) -> list:
    tolerance_parts = {
        id(part)
        for call in ast.walk(node) if isinstance(call, ast.Call)
        for keyword in call.keywords if keyword.arg in TOLERANCE_KEYWORDS
        for part in ast.walk(keyword.value)
    }
    return [
        part.value for part in ast.walk(node)
        if isinstance(part, ast.Constant) and id(part) not in tolerance_parts
        and isinstance(part.value, (int, float)) and not isinstance(part.value, bool)
        and abs(part.value) >= 1 and part.value not in SMALL_INTS
    ]


def is_assertion(node) -> bool:
    return isinstance(node, ast.Assert) or (
        isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr.startswith("assert"))


def names_in(node) -> set[str]:
    names = {part.id for part in ast.walk(node) if isinstance(part, ast.Name)}
    if isinstance(node, ast.FunctionDef):
        names |= {argument.arg for argument in node.args.args}
    return names


def design_tests_with_literals(source: str, filename: str) -> set[str]:
    """Tests that use the design (switch, dimensions, layout, case) and compare it with a literal number."""
    tree, lines, found = ast.parse(source), source.splitlines(), set()
    for qualname, node, owner in definitions(tree):
        if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
            continue
        if not (names_in(node) | (names_in(owner) if owner else set())) & DESIGN_NAMES:
            continue
        for part in ast.walk(node):
            if is_assertion(part) and literal_numbers(part) and not has_escape(lines, part):
                found.add(f"{filename}::{qualname}")
    return found


def digit_patterns(source: str, filename: str) -> list[str]:
    """Strings that expect a digit pattern or a length, for example a regex for `12.3 mm` or the text `12.3 mm` itself."""
    tree, lines = ast.parse(source), source.splitlines()
    docstrings = {id(n.value) for n in ast.walk(tree) if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)}
    return [
        f"{filename}:{node.lineno}: {node.value!r}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings
        and (r"\d" in node.value or re.search(r"\d\s*mm\b", node.value))
        and not has_escape(lines, node)
    ]


@cache
def source_of(path: Path) -> str:
    return path.read_text()


def test_only_the_baseline_tests_carry_the_slow_marker():
    marked = set().union(*(slow_marked(source_of(path), path.name) for path in TEST_FILES))
    assert marked <= SLOW_BASELINE, (
        f"New slow tests: {sorted(marked - SLOW_BASELINE)}. A unit test must stay in the CPU budget. "
        "Test a smaller shape or one builder alone. Do not add the marker."
    )
    assert SLOW_BASELINE <= marked, f"Delete these lines from SLOW_BASELINE, they are fixed: {sorted(SLOW_BASELINE - marked)}"


def test_no_test_compares_the_design_with_a_number_that_it_typed():
    found = set().union(*(design_tests_with_literals(source_of(path), path.name) for path in TEST_FILES))
    assert found <= LITERAL_BASELINE, (
        f"These tests compare design values with a literal: {sorted(found - LITERAL_BASELINE)}. "
        "Take the expected value from dims, switch, the specs or the layout."
    )
    assert LITERAL_BASELINE <= found, f"Delete these lines from LITERAL_BASELINE, they are fixed: {sorted(LITERAL_BASELINE - found)}"


def test_no_test_expects_a_digit_pattern_or_a_number_in_a_string():
    found = [line for path in TEST_FILES for line in digit_patterns(source_of(path), path.name)]
    assert not found, f"Compare with the value that the code computed, not with a pattern of digits: {found}"


def test_the_checks_flag_a_pinned_design_value_and_a_digit_pattern():
    source = (
        "def test_a(full):\n"
        "    assert full.height == 12.5\n"
        "    assert re.search('Height: \\\\d\\\\d mm', text)\n"
    )
    assert design_tests_with_literals(source, "f.py") == {"f.py::test_a"}
    assert len(digit_patterns(source, "f.py")) == 1


def test_the_checks_let_tolerances_synthetic_inputs_and_a_reasoned_escape_pass():
    synthetic = "def test_a():\n    assert Box(2, 2, 8).height == 8\n"
    tolerant = "def test_a(full):\n    assert full.height == approx(full.top, abs=0.5)\n"
    escaped = "def test_a(full):\n    assert full.count == 9  # literal-ok: the layout has nine keys by definition\n"
    unreasoned = "def test_a(full):\n    assert full.count == 9  # literal-ok:\n"
    assert not any(design_tests_with_literals(source, "f.py") for source in (synthetic, tolerant, escaped))
    assert design_tests_with_literals(unreasoned, "f.py") == {"f.py::test_a"}
