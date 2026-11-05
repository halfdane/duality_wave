import unittest
from functools import cache
from unittest.mock import patch

from dataclasses import replace

from build123d import Axis, Box, Location, Plane, Solid, Vector
from ocp_vscode import Render

from builders.bottom import add_switch_post_cutouts

from models.choc import Choc
from models.features import magnet_recess_cutter, switch_cutter
from models.model_types import RoundDimensions
from models.print_profile import PrintProfile
from models.case_dimensions import CaseDimensions
from models.keys import ErgoKeys, get_points
from models.outline import Outline
from wave_generator import WaveCase


class OutlineTests(unittest.TestCase):
    def test_inner_outline_is_deterministic(self):
        switch = Choc()
        keys = ErgoKeys(get_points("ergogen/wave.yml"))
        outline = Outline(switch=switch, keys=keys, wall_thickness=CaseDimensions.wall_thickness)
        for offset_by in (-1.8, -1.82):
            areas = {round(outline.create_inner_outline(offset_by=offset_by).area, 6) for _ in range(5)}
            self.assertEqual(len(areas), 1, f"inner outline area varies between calls: {sorted(areas)}")


def width_at(part, z):
    return (part & Box(60, 60, 0.002).translate((0, 0, z))).bounding_box().size.X


class FeatureTests(unittest.TestCase):
    def test_switch_cutter_widens_at_the_bed_side_mouth(self):
        profile = replace(PrintProfile(), switch_corner_relief=0)
        cutter = switch_cutter(Choc(), profile, [Location((0, 0, 0))], plate_z=2.9)
        hole = Choc.below.d.X + 2 * profile.switch_clearance
        self.assertTrue(cutter.is_valid)
        self.assertAlmostEqual(width_at(cutter, -0.001), hole + 2 * profile.mouth_chamfer, places=2)
        self.assertAlmostEqual(width_at(cutter, -profile.mouth_chamfer - 0.1), hole, places=3)
        self.assertAlmostEqual(width_at(cutter, -2.0), hole + 1.0, places=3)

    def test_switch_cutter_without_mouth_chamfer_is_a_plain_hole(self):
        profile = replace(PrintProfile(), mouth_chamfer=0, switch_corner_relief=0)
        cutter = switch_cutter(Choc(), profile, [Location((0, 0, 0))], plate_z=2.9)
        self.assertAlmostEqual(width_at(cutter, -0.001), Choc.below.d.X + 2 * profile.switch_clearance, places=3)

    def test_switch_corner_relief_cuts_into_the_corners(self):
        profile = replace(PrintProfile(), mouth_chamfer=0, switch_corner_relief=0)
        plain = switch_cutter(Choc(), profile, [Location((0, 0, 0))], plate_z=2.9)
        relieved = switch_cutter(Choc(), replace(profile, switch_corner_relief=0.3), [Location((0, 0, 0))], plate_z=2.9)
        self.assertGreater(relieved.volume, plain.volume)
        corner = Vector(Choc.below.d.X / 2 + 0.1, Choc.below.d.Y / 2 + 0.1, -0.5)
        self.assertFalse(plain.is_inside(corner))
        self.assertTrue(relieved.is_inside(corner))

    def test_magnet_recess_cutter_holds_two_magnets(self):
        magnet = RoundDimensions(2.5, 2)
        profile = PrintProfile()
        cutter = magnet_recess_cutter(magnet, profile, [Vector(0, 0, 8.3)], top_z=8.3)
        box = cutter.bounding_box()
        self.assertAlmostEqual(box.max.Z, 8.3, places=3)
        self.assertAlmostEqual(box.max.Z - box.min.Z, 2 * magnet.Z, places=3)
        self.assertAlmostEqual(width_at(cutter, 8.299), 2 * (magnet.radius + profile.magnet_clearance + profile.mouth_chamfer), places=2)
        self.assertAlmostEqual(width_at(cutter, 7.0), 2 * (magnet.radius + profile.magnet_clearance), places=3)


PARTS = ("keywell", "keyplate", "bottom")


@cache
def build_case(debug: bool, both_sides: bool = True):
    """Build a case once per test run. Returns the case and the mock that received its viewer pushes."""
    switch = Choc()
    keys = ErgoKeys(get_points("ergogen/wave.yml"))
    outline = Outline(switch=switch, keys=keys, wall_thickness=CaseDimensions.wall_thickness)
    dims = CaseDimensions(switch=switch, outline=outline, keys=keys)
    with patch("ocp_vscode.push_object") as push_object:
        case = WaveCase(switch, keys, dims, outline, debug=debug, both_sides=both_sides)
    return case, push_object


def pushed_names(push_object):
    return [call.kwargs["name"] for call in push_object.call_args_list]


class DebugFlagTests(unittest.TestCase):
    def test_debug_off_pushes_nothing_and_builds_no_accessories(self):
        case, push_object = build_case(debug=False)
        push_object.assert_not_called()
        self.assertIsNone(case.left.accessories)
        self.assertIsNone(case.right.accessories)

    def test_debug_off_builds_the_same_parts_as_debug_on(self):
        quiet, _ = build_case(debug=False)
        verbose, _ = build_case(debug=True)
        for side in ("left", "right"):
            for name in PARTS:
                with self.subTest(part=f"{name}_{side}"):
                    self.assertAlmostEqual(
                        getattr(getattr(quiet, side), name).volume, getattr(getattr(verbose, side), name).volume, places=3)

    def test_debug_on_pushes_every_part_and_the_debug_group_last(self):
        case, push_object = build_case(debug=True)
        names = pushed_names(push_object)
        self.assertEqual(names[-1], "debug")
        self.assertEqual(names.count("debug"), 1)
        for side in ("left", "right"):
            for name in ("accessories", *PARTS):
                self.assertIn(f"{name}_{side}", names[:-1])

    def test_debug_group_starts_hidden_and_the_parts_do_not(self):
        _, push_object = build_case(debug=True)
        modes = {call.kwargs["name"]: call.kwargs.get("mode") for call in push_object.call_args_list}
        self.assertEqual(modes.pop("debug"), Render.NONE)
        self.assertTrue(all(mode is None for mode in modes.values()))

    def test_debug_group_holds_what_the_builders_noted(self):
        _, push_object = build_case(debug=True)
        group = next(c.args[0] for c in push_object.call_args_list if c.kwargs["name"] == "debug")
        for name in PARTS:
            self.assertTrue(group[name], f"nothing noted for {name}")

    def test_accessories_are_built_for_both_halves(self):
        case, _ = build_case(debug=True)
        for built in (case.left, case.right):
            for part in built.accessories.as_dict().values():
                self.assertGreater(part.volume, 0)


class SidesTests(unittest.TestCase):
    def test_one_sided_case_has_no_right_half(self):
        case, _ = build_case(debug=False, both_sides=False)
        self.assertIsNone(case.right)
        for name in PARTS:
            self.assertGreater(getattr(case.left, name).volume, 0)

    def test_right_half_mirrors_the_left_half(self):
        case, _ = build_case(debug=False)
        offset = case.ctx.dims.right_side_offset
        for name in PARTS:
            with self.subTest(part=name):
                left, right = getattr(case.left, name), getattr(case.right, name)
                self.assertAlmostEqual(left.volume / right.volume, 1, places=3)
                self.assertAlmostEqual(right.bounding_box().min.X, offset - left.bounding_box().max.X, places=3)
                self.assertAlmostEqual(right.bounding_box().max.X, offset - left.bounding_box().min.X, places=3)
                self.assertAlmostEqual(right.bounding_box().min.Y, left.bounding_box().min.Y, places=3)


class SwitchPostCutoutTests(unittest.TestCase):
    def test_complete_case_terminal_clearance(self):
        case, _ = build_case(debug=False)
        switch, keys, dims = case.ctx.switch, case.ctx.keys, case.ctx.dims
        for side in ("left", "right"):
            for name in PARTS:
                part = getattr(getattr(case, side), name)
                self.assertTrue(part.is_valid)
                self.assertEqual(len(part.solids()), 1)
            bottom = getattr(case, side).bottom
            for key in keys.keys:
                position = key.p if side == "left" else Vector(dims.right_side_offset - key.p.X, key.p.Y, key.p.Z)
                rotation = key.r if side == "left" else -key.r
                for post in (switch.posts.p1, switch.posts.p2):
                    with self.subTest(side=side, key=key.p, post=post.p):
                        terminal = Solid.make_cylinder(
                            post.d.radius,
                            post.d.Z,
                            Plane(origin=(post.p.X, -post.p.Y, -switch.bottom_housing.d.Z), z_dir=(0, 0, -1)),
                        ).rotate(Axis.Z, rotation).translate(position)
                        overlap = bottom & terminal
                        self.assertLess(sum(s.volume for s in overlap.solids()) if overlap else 0, 1e-7)

    def test_physical_footprint_on_both_halves(self):
        for angle in (0, 23, -37):
            for right in (False, True):
                with self.subTest(angle=angle, right=right):
                    position = Vector(170 if right else 30, 20, 0)
                    rotation = -angle if right else angle
                    placement = Location(position, (0, 0, rotation))
                    blank = Box(30, 30, 3).translate(position + Vector(0, 0, -4.4))
                    bottom = add_switch_post_cutouts(blank, Choc, 3.0, [placement])
                    self.assertTrue(bottom.is_valid)
                    self.assertEqual(len(bottom.solids()), 1)
                    for post in (Choc.posts.center, Choc.posts.p1, Choc.posts.p2):
                        terminal = Solid.make_cylinder(
                            post.d.radius,
                            post.d.Z,
                            Plane(origin=(post.p.X, -post.p.Y, -2.2), z_dir=(0, 0, -1)),
                        ).rotate(Axis.Z, rotation).translate(position)
                        overlap = bottom & terminal
                        self.assertLess(sum(s.volume for s in overlap.solids()) if overlap else 0, 1e-7)
                        center = Vector(post.p.X, -post.p.Y, -4).rotate(Axis.Z, rotation) + position
                        edge = Vector(post.d.radius + 0.11, 0, 0).rotate(Axis.Z, rotation)
                        self.assertFalse(bottom.is_inside(center))
                        self.assertTrue(bottom.is_inside(center + edge))

                    mirrored_terminal = Vector(-Choc.posts.p2.p.X, -Choc.posts.p2.p.Y, -4)
                    mirrored_terminal = mirrored_terminal.rotate(Axis.Z, rotation) + position
                    self.assertTrue(bottom.is_inside(mirrored_terminal))
                    self.assertTrue(bottom.is_inside(position + Vector(0, 0, -5.3)))


if __name__ == "__main__":
    unittest.main()
