import subprocess
import sys
import unittest
from dataclasses import replace
from types import SimpleNamespace

from build123d import BuildSketch, Box, Circle, Plane, Sketch, Vector

from builders.accessories import build_fixtures
from builders.side import Side
from builders.thumb_cut import ThumbCutSpec, thumb_cutter, thumb_depth, thumb_floor_z
from builders.viewer import DebugScope, NullScope
from models.choc import Choc
from models.heat_set_insert import HeatSetInsert
from models.keys import Point
from models.model_types import PosAndDims, RectDimensions, RoundDimensions
from models.rubber_bumper import RubberBumper
from models.screw import LowProfileScrew


def section_area(part, z):
    return (part & Box(400, 400, 0.002).translate((0, 0, z))).volume / 0.002


def thumb_keys(*positions, rotation=0.0):
    """One thumb cluster with one column that holds a key at each of the positions."""
    return [[[Point(p=Vector(*position), r=rotation) for position in positions]]]


class ThumbCutterTests(unittest.TestCase):
    switch = Choc()
    top_z = 8.0
    spec = ThumbCutSpec(run_inner=4, run_outer=10, inset_inner=2, inset_outer=2, layers=8)

    def cutter(self, keys=None, spec=None, top_z=None):
        keys = keys if keys is not None else thumb_keys((0, 0), (0, -19))
        return thumb_cutter(self.switch, keys, top_z if top_z is not None else self.top_z, spec or self.spec)

    def test_cutter_spans_from_the_thumb_floor_to_the_top(self):
        for top_z in (8.0, 12.5):
            with self.subTest(top_z=top_z):
                box = self.cutter(top_z=top_z).bounding_box()
                self.assertAlmostEqual(box.max.Z, top_z, places=3)
                self.assertAlmostEqual(box.min.Z, top_z - thumb_depth(self.switch), places=3)
                self.assertAlmostEqual(box.min.Z, thumb_floor_z(self.switch, top_z), places=3)

    def test_cutter_is_wider_at_the_top_than_at_the_floor(self):
        cutter = self.cutter()
        floor_z = thumb_floor_z(self.switch, self.top_z)
        self.assertGreater(section_area(cutter, self.top_z - 0.05), section_area(cutter, floor_z + 0.05))

    def test_cutter_without_growth_is_a_straight_pocket(self):
        flat = self.cutter(spec=ThumbCutSpec(0, 0, 0, 0, layers=4))
        floor_z = thumb_floor_z(self.switch, self.top_z)
        self.assertAlmostEqual(section_area(flat, floor_z + 0.05), section_area(flat, self.top_z - 0.05), places=1)

    def test_a_longer_run_cuts_more(self):
        shallow = self.cutter(spec=replace(self.spec, run_outer=self.spec.run_outer / 2))
        steep = self.cutter(spec=replace(self.spec, run_outer=self.spec.run_outer * 2))
        self.assertGreater(steep.volume, shallow.volume)

    def test_more_layers_refine_the_same_slope(self):
        coarse = self.cutter(spec=replace(self.spec, layers=6))
        fine = self.cutter(spec=replace(self.spec, layers=24))
        self.assertAlmostEqual(coarse.volume / fine.volume, 1, delta=0.05)

    def test_cutter_follows_the_keys(self):
        shift = Vector(13, -7)
        home = self.cutter(keys=thumb_keys((0, 0), (0, -19)))
        moved = self.cutter(keys=thumb_keys((shift.X, shift.Y), (shift.X, shift.Y - 19)))
        self.assertAlmostEqual(moved.volume, home.volume, places=2)
        self.assertAlmostEqual(moved.bounding_box().min.X - home.bounding_box().min.X, shift.X, places=3)
        self.assertAlmostEqual(moved.bounding_box().min.Y - home.bounding_box().min.Y, shift.Y, places=3)

    def test_more_keys_cut_more(self):
        one = self.cutter(keys=thumb_keys((0, 0)))
        two = self.cutter(keys=thumb_keys((0, 0), (0, -19)))
        self.assertGreater(two.volume, one.volume)


class DebugScopeTests(unittest.TestCase):
    def test_scope_nests_what_it_notes(self):
        debug = DebugScope()
        child = debug.scope("keyplate")
        self.assertEqual(child.note("holes", 1), 1)
        debug.note("top", 2)
        self.assertEqual(debug.content, {"keyplate": {"holes": 1}, "top": 2})

    def test_builders_are_noted_as_plain_shapes(self):
        debug = DebugScope()
        with BuildSketch() as sketch:
            Circle(2)
        returned = debug.note("holes", sketch)
        self.assertIs(returned, sketch)
        self.assertNotIsInstance(debug.content["holes"], BuildSketch)
        self.assertIsInstance(debug.content["holes"], Sketch)
        self.assertAlmostEqual(debug.content["holes"].area, sketch.sketch.area)

    def test_other_values_are_noted_as_they_are(self):
        debug = DebugScope()
        box = Box(1, 1, 1)
        debug.note("box", box)
        self.assertIs(debug.content["box"], box)

    def test_null_scope_keeps_nothing(self):
        scope = NullScope()
        self.assertEqual(scope.scope("a").note("b", 3), 3)


def fixture_context(magnets=True):
    dims = SimpleNamespace(
        below_z=5.9,
        bumper_locations=[Vector(5, 5), Vector(40, 30)],
        powerswitch_rotation=Vector(0, 180, -90),
        powerswitch_position=Vector(20, 20, -4),
        fastener_positions=[Vector(0, 0), Vector(30, 10)],
        battery_pd=PosAndDims(d=RectDimensions(31, 17, 6), p=Vector(15, 40, 4)),
        magnet_d=RoundDimensions(2.5, 2),
        magnet_positions=[Vector(10, 10, 8.3), Vector(30, 20, 8.3)] if magnets else [],
        right_side_offset=100,
    )
    return SimpleNamespace(
        dims=dims, switch=Choc(), keys=None,
        bumper=RubberBumper(), insert=HeatSetInsert(1.9), screw=LowProfileScrew())


class FixtureTests(unittest.TestCase):
    def test_building_twice_gives_the_same_placement(self):
        ctx = fixture_context()
        first = build_fixtures(ctx)
        second = build_fixtures(ctx)
        self.assertEqual(first.bumpers.bounding_box().size.Z, second.bumpers.bounding_box().size.Z)
        self.assertAlmostEqual(first.bumpers.bounding_box().min.Z, second.bumpers.bounding_box().min.Z, places=6)
        self.assertAlmostEqual(first.bumpers.volume, second.bumpers.volume, places=6)

    def test_every_fastener_gets_an_insert_and_a_screw(self):
        ctx = fixture_context()
        fixtures = build_fixtures(ctx)
        self.assertEqual(len(fixtures.inserts.solids()), len(ctx.dims.fastener_positions))
        self.assertEqual(len(fixtures.screws.solids()), len(ctx.dims.fastener_positions))

    def test_without_magnet_positions_there_are_no_magnets(self):
        fixtures = build_fixtures(fixture_context(magnets=False))
        self.assertIsNone(fixtures.magnets)
        self.assertIsNone(fixtures.mirrored(Plane.YZ).magnets)

    def test_magnets_sit_at_their_positions(self):
        ctx = fixture_context()
        box = build_fixtures(ctx).magnets.bounding_box()
        radius = ctx.dims.magnet_d.radius
        self.assertAlmostEqual(box.min.X, 10 - radius, places=3)
        self.assertAlmostEqual(box.max.X, 30 + radius, places=3)
        self.assertAlmostEqual(box.max.Z, 8.3, places=3)

    def test_mirrored_fixtures_swap_sides(self):
        fixtures = build_fixtures(fixture_context())
        about = Plane((50, 0, 0), x_dir=Plane.YZ.x_dir, z_dir=Plane.YZ.z_dir)
        mirrored = fixtures.mirrored(about)
        for name in ("bumpers", "power_switch", "battery", "inserts", "screws", "magnets"):
            with self.subTest(part=name):
                original, flipped = getattr(fixtures, name), getattr(mirrored, name)
                self.assertAlmostEqual(original.volume, flipped.volume, places=3)
                self.assertAlmostEqual(flipped.bounding_box().min.X, 100 - original.bounding_box().max.X, places=3)
                self.assertAlmostEqual(flipped.bounding_box().max.X, 100 - original.bounding_box().min.X, places=3)


class SideTests(unittest.TestCase):
    def context(self):
        keys = SimpleNamespace(keys=[Point(p=Vector(10, 5, 0), r=15), Point(p=Vector(30, 12, 0), r=-20)])
        dims = SimpleNamespace(xiao_position=Vector(12, 60, -1.5), right_side_offset=200)
        return SimpleNamespace(keys=keys, dims=dims)

    def test_right_keys_are_the_left_keys_mirrored(self):
        ctx = self.context()
        left = Side.left(ctx)
        right = Side.right(ctx, left)
        for key, a, b in zip(ctx.keys.keys, left.switch_locations, right.switch_locations):
            self.assertAlmostEqual(a.position.X + b.position.X, 200, places=6)
            self.assertAlmostEqual(a.position.Y, b.position.Y, places=6)
            self.assertAlmostEqual(a.orientation.Z, -b.orientation.Z, places=6)

    def test_right_xiao_is_the_left_xiao_mirrored(self):
        ctx = self.context()
        left = Side.left(ctx)
        right = Side.right(ctx, left)
        self.assertAlmostEqual(left.xiao_plane.origin.X + right.xiao_plane.origin.X, 200, places=6)
        self.assertAlmostEqual(left.xiao_plane.origin.Y, right.xiao_plane.origin.Y, places=6)
        self.assertAlmostEqual(left.xiao_plane.origin.Z, right.xiao_plane.origin.Z, places=6)

    def test_left_side_keeps_shapes_and_right_side_mirrors_them(self):
        ctx = self.context()
        left = Side.left(ctx)
        right = Side.right(ctx, left)
        block = Box(10, 10, 10).translate((20, 0, 0))
        self.assertIs(left.mirrored(block), block)
        self.assertAlmostEqual(right.mirrored(block).bounding_box().center().X, 200 - 20, places=6)

    def test_suffix_names_only_the_right_side(self):
        ctx = self.context()
        left = Side.left(ctx)
        self.assertEqual(left.suffix, "")
        self.assertEqual(Side.right(ctx, left).suffix, "_right")


class HeadlessImportTests(unittest.TestCase):
    def test_building_blocks_import_without_the_viewer_package(self):
        script = (
            "import sys\n"
            "class Block:\n"
            "    def find_spec(self, name, path=None, target=None):\n"
            "        if name.split('.')[0] == 'ocp_vscode':\n"
            "            raise ImportError('blocked ' + name)\n"
            "sys.meta_path.insert(0, Block())\n"
            "import wave_generator, render, ergogen, models.case_dimensions, builders.export\n"
            "assert 'ocp_vscode' not in sys.modules\n"
        )
        result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])


if __name__ == "__main__":
    unittest.main()
