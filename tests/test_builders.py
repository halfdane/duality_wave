import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from dataclasses import replace
from types import SimpleNamespace

from build123d import Axis, BuildSketch, Box, Circle, Plane, Rectangle, Sketch, Solid, Vector

from duality_wave.builders.accessories import build_fixtures
from duality_wave.builders.bottom import build_bottom
from duality_wave.builders.export import export_steps, print_pose
from duality_wave.builders.side import Side
from duality_wave.builders.keywell import build_keywell
from duality_wave.builders.thumb_cut import ThumbCutSpec, thumb_cutter, thumb_depth, thumb_floor_z, thumb_zone
from duality_wave.builders.viewer import DebugScope, NullScope
from duality_wave.models.choc import Choc
from duality_wave.models.heat_set_insert import HeatSetInsert
from duality_wave.models.keys import Point
from duality_wave.models.model_types import PosAndDims, RectDimensions, RoundDimensions
from duality_wave.print_profile import PrintProfile
from duality_wave.models.rubber_bumper import RubberBumper
from duality_wave.models.screw import LowProfileScrew
from tests import ROOT
from tests.builds import make_context, make_inputs

def section_area(part, z):
    return (part & Box(400, 400, 0.002).translate((0, 0, z))).volume / 0.002


def thumb_keys(*positions, rotation=0.0):
    """One thumb cluster with one column that holds a key at each of the positions."""
    return [[[Point(p=Vector(*position), r=rotation) for position in positions]]]


class ThumbCutterTests(unittest.TestCase):
    switch = Choc()
    top_z = 8.0
    spec = ThumbCutSpec(taper=8, inset_inner=2, inset_outer=2, corner_radius=1, layers=8)

    def cutter(self, keys=None, spec=None, top_z=None):
        keys = keys if keys is not None else thumb_keys((0, 0), (0, -17))
        return thumb_cutter(self.switch, keys, top_z if top_z is not None else self.top_z, spec or self.spec)

    def test_cutter_is_one_valid_solid(self):  # R-16
        cutter = self.cutter()
        self.assertTrue(cutter.is_valid)
        self.assertIsInstance(cutter, Solid)

    def test_cutter_spans_from_the_thumb_floor_to_the_top(self):  # R-16
        for top_z in (8.0, 12.5):
            with self.subTest(top_z=top_z):
                box = self.cutter(top_z=top_z).bounding_box()
                self.assertAlmostEqual(box.max.Z, top_z, delta=0.01)
                self.assertAlmostEqual(box.min.Z, top_z - thumb_depth(self.switch, top_z), delta=0.01)
                self.assertAlmostEqual(box.min.Z, thumb_floor_z(self.switch), delta=0.01)
                self.assertAlmostEqual(box.min.Z, self.switch.base.d.Z + self.switch.upper_housing.d.Z, delta=0.01)

    def test_cutter_is_wider_at_the_top_than_at_the_floor(self):  # R-16
        cutter = self.cutter()
        floor_z = thumb_floor_z(self.switch)
        self.assertGreater(section_area(cutter, self.top_z - 0.05), section_area(cutter, floor_z + 0.05))

    def test_the_slope_grows_by_the_taper_at_the_top(self):  # R-16
        keys = thumb_keys((0, 0), (0, -17))
        spec = replace(self.spec, corner_radius=0)
        floor = thumb_cutter(self.switch, keys, self.top_z, replace(spec, taper=0.001, layers=1)).bounding_box()
        top = self.cutter(keys=keys, spec=spec).bounding_box()
        self.assertAlmostEqual(floor.min.X - top.min.X, spec.taper, delta=0.01)
        self.assertAlmostEqual(top.max.X - floor.max.X, spec.taper, delta=0.01)

    def test_cutter_without_growth_is_a_straight_pocket(self):  # R-16
        flat = self.cutter(spec=ThumbCutSpec(taper=0.001, inset_inner=0, inset_outer=0, corner_radius=0, layers=4))
        floor_z = thumb_floor_z(self.switch)
        self.assertAlmostEqual(section_area(flat, floor_z + 0.05), section_area(flat, self.top_z - 0.05), delta=0.5)

    def test_the_real_layouts_loft_for_any_reasonable_spec(self):  # R-16
        for compact in (False, True):
            switch, keys, dims, _ = make_inputs(compact)
            for taper, layers in ((5, 4), (15, 16), (20, 32)):
                with self.subTest(compact=compact, taper=taper, layers=layers):
                    cutter = thumb_cutter(switch, keys.thumb_clusters, dims.above_z, ThumbCutSpec(taper=taper, layers=layers))
                    self.assertTrue(cutter.is_valid)

    def test_cutter_follows_the_keys(self):  # R-16
        shift = Vector(13, -7)
        home = self.cutter(keys=thumb_keys((0, 0), (0, -17)))
        moved = self.cutter(keys=thumb_keys((shift.X, shift.Y), (shift.X, shift.Y - 17)))
        self.assertAlmostEqual(moved.volume, home.volume, places=2)
        self.assertAlmostEqual(moved.bounding_box().min.X - home.bounding_box().min.X, shift.X, places=3)
        self.assertAlmostEqual(moved.bounding_box().min.Y - home.bounding_box().min.Y, shift.Y, places=3)

    def test_more_keys_cut_more(self):  # R-16
        one = self.cutter(keys=thumb_keys((0, 0)))
        two = self.cutter(keys=thumb_keys((0, 0), (0, -17)))
        self.assertGreater(two.volume, one.volume)


class ThumbZoneTests(unittest.TestCase):
    switch = Choc()
    keys = thumb_keys((0, 0), (0, -17))
    sharp = ThumbCutSpec(corner_radius=0)

    def test_the_zone_is_one_face_in_the_xy_plane(self):  # R-16
        zone = thumb_zone(self.switch, self.keys, self.sharp)
        self.assertEqual(zone.geom_type.name, "PLANE")
        self.assertAlmostEqual(zone.bounding_box().min.Z, 0)
        self.assertAlmostEqual(zone.bounding_box().max.Z, 0)

    def test_the_corners_are_round(self):  # R-16
        sharp = thumb_zone(self.switch, self.keys, self.sharp)
        round_ = thumb_zone(self.switch, self.keys, replace(self.sharp, corner_radius=2))
        self.assertEqual({e.geom_type.name for e in sharp.edges()}, {"LINE"})
        corners = sum(e.geom_type.name == "CIRCLE" for e in round_.edges())
        self.assertGreaterEqual(corners, 4)
        self.assertAlmostEqual(sharp.area - round_.area, corners * 2**2 * (1 - math.pi / 4), delta=0.01)

    def test_keys_that_do_not_touch_give_an_error(self):  # R-16
        far = thumb_keys((0, 0), (0, -300))
        with self.assertRaises(ValueError):
            thumb_zone(self.switch, far, self.sharp)


class KeywellRimTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = make_context(compact=True)
        cls.sharp = build_keywell(cls.ctx, thumb_spec=ThumbCutSpec(rim_chamfer=0))
        cls.chamfered = build_keywell(cls.ctx, thumb_spec=ThumbCutSpec(rim_chamfer=0.8))

    def test_the_chamfer_takes_material_from_the_rim(self):  # R-17
        self.assertLess(self.chamfered.volume, self.sharp.volume)
        self.assertGreater(self.chamfered.volume, 0.95 * self.sharp.volume)

    def test_the_chamfer_keeps_the_envelope(self):  # R-17
        a, b = self.sharp.bounding_box(), self.chamfered.bounding_box()
        for sharp, chamfered in zip((*a.min, *a.max), (*b.min, *b.max)):
            self.assertAlmostEqual(sharp, chamfered, places=3)

    def test_the_chamfered_keywell_is_one_valid_solid(self):  # R-17
        self.assertTrue(self.chamfered.is_valid)
        self.assertEqual(len(self.chamfered.solids()), 1)


class BottomFitTests(unittest.TestCase):
    def bottom(self, **fit):
        ctx = make_context(profile=replace(PrintProfile(), **fit))
        return ctx, build_bottom(ctx)

    def test_screw_clearance_sets_the_radius_of_the_hole(self):
        for clearance in (0.1, 0.3):
            with self.subTest(clearance=clearance):
                ctx, bottom = self.bottom(screw_clearance=clearance)
                center = ctx.dims.fastener_positions[0]
                z = -ctx.dims.below_z + ctx.dims.bottom_plate_z - 0.1
                radius = LowProfileScrew.dims.shaft.radius + clearance
                self.assertFalse(bottom.is_inside(Vector(center.X + radius - 0.02, center.Y, z)))
                self.assertTrue(bottom.is_inside(Vector(center.X + radius + 0.02, center.Y, z)))

    def test_screw_head_clearance_sets_the_radius_of_the_recess(self):
        for clearance in (0.05, 0.3):
            with self.subTest(clearance=clearance):
                ctx, bottom = self.bottom(screw_head_clearance=clearance)
                center = ctx.dims.fastener_positions[0]
                z = -ctx.dims.below_z + LowProfileScrew.dims.head.Z / 2
                radius = LowProfileScrew.dims.head.radius + clearance
                self.assertFalse(bottom.is_inside(Vector(center.X + radius - 0.02, center.Y, z)))
                self.assertTrue(bottom.is_inside(Vector(center.X + radius + 0.02, center.Y, z)))


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
        magnet_spacer=RoundDimensions(2, 3),
        magnet_positions=[Vector(10, 10, 8.3), Vector(30, 20, 8.3)] if magnets else [],
        right_side_offset=100,
    )
    return SimpleNamespace(
        dims=dims, switch=Choc(), keys=None,
        bumper=RubberBumper(), insert=HeatSetInsert(), screw=LowProfileScrew())


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
        self.assertIsNone(fixtures.spacers)
        self.assertIsNone(fixtures.mirrored(Plane.YZ).magnets)

    def test_magnets_sit_at_their_positions(self):
        ctx = fixture_context()
        box = build_fixtures(ctx).magnets.bounding_box()
        radius = ctx.dims.magnet_d.radius
        self.assertAlmostEqual(box.min.X, 10 - radius, places=3)
        self.assertAlmostEqual(box.max.X, 30 + radius, places=3)
        self.assertAlmostEqual(box.max.Z, 8.3, places=3)

    def test_a_spacer_stands_under_every_stack_of_magnets(self):
        ctx = fixture_context()
        fixtures = build_fixtures(ctx)
        self.assertEqual(len(fixtures.spacers.solids()), len(ctx.dims.magnet_positions))
        box = fixtures.spacers.bounding_box()
        self.assertAlmostEqual(box.min.Z, 0, places=3)
        self.assertAlmostEqual(box.max.Z, ctx.dims.magnet_spacer.Z, places=3)

    def test_mirrored_fixtures_swap_sides(self):
        fixtures = build_fixtures(fixture_context())
        about = Plane((50, 0, 0), x_dir=Plane.YZ.x_dir, z_dir=Plane.YZ.z_dir)
        mirrored = fixtures.mirrored(about)
        for name in ("bumpers", "power_switch", "battery", "inserts", "screws", "magnets", "spacers"):
            with self.subTest(part=name):
                original, flipped = getattr(fixtures, name), getattr(mirrored, name)
                self.assertAlmostEqual(original.volume, flipped.volume, places=3)
                self.assertAlmostEqual(flipped.bounding_box().min.X, 100 - original.bounding_box().max.X, places=3)
                self.assertAlmostEqual(flipped.bounding_box().max.X, 100 - original.bounding_box().min.X, places=3)


class SideTests(unittest.TestCase):
    def context(self):
        keys = SimpleNamespace(keys=[Point(p=Vector(10, 5, 0), r=15), Point(p=Vector(30, 12, 0), r=-20)])
        dims = SimpleNamespace(xiao_position=Vector(12, 60, -1.5), right_side_offset=200)
        with BuildSketch() as outline:
            Rectangle(40, 30)
        return SimpleNamespace(keys=keys, dims=dims, outline=SimpleNamespace(sketch=outline.sketch))

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


class PrintPoseTests(unittest.TestCase):
    def stepped_block(self):
        # a wide base (z -5..0) with a narrow stub on top (z 0..3)
        return Box(20, 20, 5).translate((0, 0, -2.5)) + Box(4, 4, 3).translate((0, 0, 1.5))

    def test_keywell_and_keyplate_are_flipped_onto_the_bed(self):
        for name in ("keywell", "keyplate"):
            posed = print_pose(name, self.stepped_block())
            box = posed.bounding_box()
            self.assertAlmostEqual(box.min.Z, 0, places=6)
            self.assertAlmostEqual(box.max.Z, 8, places=6)
            # the stub is now on the bed, the wide base on top
            self.assertAlmostEqual(posed.faces().sort_by(Axis.Z)[0].bounding_box().size.X, 4, places=6)

    def test_bottom_stays_upright_and_drops_to_the_bed(self):
        posed = print_pose("bottom", self.stepped_block())
        box = posed.bounding_box()
        self.assertAlmostEqual(box.min.Z, 0, places=6)
        self.assertAlmostEqual(posed.faces().sort_by(Axis.Z)[0].bounding_box().size.X, 20, places=6)


class ExportTests(unittest.TestCase):
    def built_side(self, name):
        parts = {part: Box(1, 1, 1) for part in ("keywell", "keyplate", "bottom")}
        return SimpleNamespace(side=SimpleNamespace(name=name), **parts)

    def test_exports_every_part_of_every_built_half(self):
        case = SimpleNamespace(left=self.built_side("left"), right=self.built_side("right"), magnet_spacer=Box(1, 1, 1))
        with tempfile.TemporaryDirectory() as tmp:
            written = export_steps(case, suffix="_x", out_dir=Path(tmp) / "nested")
            self.assertEqual(len(written), 7)
            for path in written:
                self.assertGreater(path.stat().st_size, 0)
            names = {path.name for path in written}
            self.assertIn("keywell_right_x.step", names)
            self.assertIn("magnet_spacer_x.step", names)

    def test_skips_a_half_that_was_not_built(self):
        case = SimpleNamespace(left=self.built_side("left"), right=None, magnet_spacer=None)
        with tempfile.TemporaryDirectory() as tmp:
            written = export_steps(case, out_dir=tmp)
            self.assertEqual({path.name for path in written}, {"keywell_left.step", "keyplate_left.step", "bottom_left.step"})


class HeadlessImportTests(unittest.TestCase):
    def test_building_blocks_import_without_the_viewer_package(self):
        script = (
            "import sys\n"
            "class Block:\n"
            "    def find_spec(self, name, path=None, target=None):\n"
            "        if name.split('.')[0] == 'ocp_viewer':\n"
            "            raise ImportError('blocked ' + name)\n"
            "sys.meta_path.insert(0, Block())\n"
            "import duality_wave.case, duality_wave.cli.render, duality_wave.layout, duality_wave.models.case_dimensions, duality_wave.builders.export\n"
            "assert 'ocp_viewer' not in sys.modules\n"
        )
        result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])


if __name__ == "__main__":
    unittest.main()
