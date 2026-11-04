import unittest
from unittest.mock import patch

from dataclasses import replace
from types import SimpleNamespace

from build123d import Axis, Box, Location, Plane, Solid, Vector

from models.choc import Choc
from models.features import magnet_recess_cutter, switch_cutter
from models.model_types import RoundDimensions
from models.print_profile import PrintProfile
from duality_wave import CaseDimensions
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


class DebugFlagTests(unittest.TestCase):
    def test_debug_off_builds_the_same_parts_without_accessories(self):
        switch = Choc()
        keys = ErgoKeys(get_points("ergogen/wave.yml"))
        outline = Outline(switch=switch, keys=keys, wall_thickness=CaseDimensions.wall_thickness)
        dims = CaseDimensions(switch=switch, outline=outline, keys=keys)
        with patch("wave_generator.push_object") as push_object:
            quiet = WaveCase(switch, keys, dims, outline, debug=False, both_sides=True)
            push_object.assert_not_called()
            verbose = WaveCase(switch, keys, dims, outline, debug=True, both_sides=True)
        self.assertFalse(hasattr(quiet, "switches"))
        for name in ("keywell", "keyplate", "bottom"):
            for side in ("left", "right"):
                with self.subTest(part=f"{name}_{side}"):
                    self.assertAlmostEqual(
                        getattr(quiet, f"{name}_{side}").volume, getattr(verbose, f"{name}_{side}").volume, places=3)


class SwitchPostCutoutTests(unittest.TestCase):
    def test_complete_case_terminal_clearance(self):
        switch = Choc()
        keys = ErgoKeys(get_points("ergogen/wave.yml"))
        outline = Outline(switch=switch, keys=keys, wall_thickness=CaseDimensions.wall_thickness)
        dims = CaseDimensions(switch=switch, outline=outline, keys=keys)
        with patch("wave_generator.push_object"):
            case = WaveCase(switch, keys, dims, outline, debug=True, both_sides=True)
        for side in ("left", "right"):
            for name in ("keywell", "keyplate", "bottom"):
                part = getattr(case, f"{name}_{side}")
                self.assertTrue(part.is_valid)
                self.assertEqual(len(part.solids()), 1)
            bottom = getattr(case, f"bottom_{side}")
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
        case = WaveCase.__new__(WaveCase)
        case.switch = Choc
        case.dims = SimpleNamespace(bottom_plate_z=3.0)
        for angle in (0, 23, -37):
            for right in (False, True):
                with self.subTest(angle=angle, right=right):
                    position = Vector(170 if right else 30, 20, 0)
                    rotation = -angle if right else angle
                    placement = Location(position, (0, 0, rotation))
                    blank = Box(30, 30, 3).translate(position + Vector(0, 0, -4.4))
                    bottom = case.add_switch_post_cutouts(blank, [placement])
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
