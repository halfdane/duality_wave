import unittest

import pytest
from dataclasses import replace

from build123d import Axis, Box, Location, Plane, Solid, Vector

from duality_wave.builders.bottom import add_switch_post_cutouts

from duality_wave.models.choc import Choc
from duality_wave.models.features import magnet_recess_cutter, switch_cutter
from duality_wave.print_profile import PrintProfile
from tests.builds import PARTS, make_inputs


def width_at(part, z):
    return (part & Box(60, 60, 0.002).translate((0, 0, z))).bounding_box().size.X


class FeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, _, cls.dims, _ = make_inputs()

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
        magnet, profile, top_z = self.dims.magnet_d, self.dims.print_profile, self.dims.magnet_z
        cutter = magnet_recess_cutter(magnet, profile, [Vector(0, 0, top_z)], top_z=top_z)
        box = cutter.bounding_box()
        recess_width = 2 * (magnet.radius + profile.magnet_clearance)
        mouth_width = recess_width + 2 * profile.mouth_chamfer
        just_below_the_top = top_z - 0.001
        middle_of_the_straight_wall = top_z - (profile.mouth_chamfer + 2 * magnet.Z) / 2
        self.assertAlmostEqual(box.max.Z, top_z, places=3)
        self.assertAlmostEqual(box.max.Z - box.min.Z, 2 * magnet.Z, places=3)
        self.assertAlmostEqual(width_at(cutter, just_below_the_top), mouth_width, places=2)
        self.assertAlmostEqual(width_at(cutter, middle_of_the_straight_wall), recess_width, places=3)


@pytest.mark.integration
def test_right_half_mirrors_the_left_half(full):  # R-02
    offset = full.ctx.dims.right_side_offset
    for name in PARTS:
        left, right = getattr(full.left, name), getattr(full.right, name)
        # the trenches of the wiring differ between the halves
        assert left.volume / right.volume == pytest.approx(1, abs=1e-2 if name == "keyplate" else 1e-3), name
        assert right.bounding_box().min.X == pytest.approx(offset - left.bounding_box().max.X, abs=1e-3), name
        assert right.bounding_box().max.X == pytest.approx(offset - left.bounding_box().min.X, abs=1e-3), name
        assert right.bounding_box().min.Y == pytest.approx(left.bounding_box().min.Y, abs=1e-3), name


@pytest.mark.integration
def test_complete_case_terminal_clearance(full):  # R-06
    switch, keys, dims = full.ctx.switch, full.ctx.keys, full.ctx.dims
    for side in ("left", "right"):
        bottom = getattr(full, side).bottom
        for key in keys.keys:
            position = key.p if side == "left" else Vector(dims.right_side_offset - key.p.X, key.p.Y, key.p.Z)
            rotation = key.r if side == "left" else -key.r
            for post in (switch.posts.p1, switch.posts.p2):
                terminal = Solid.make_cylinder(
                    post.d.radius,
                    post.d.Z,
                    Plane(origin=(post.p.X, -post.p.Y, -switch.bottom_housing.d.Z), z_dir=(0, 0, -1)),
                ).rotate(Axis.Z, rotation).translate(position)
                overlap = bottom & terminal
                volume = sum(s.volume for s in overlap.solids()) if overlap else 0
                assert volume < 1e-7, f"{side} key at {key.p}, post at {post.p}"


class SwitchPostCutoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.switch, _, cls.dims, _ = make_inputs()

    def blank_at(self, position):
        """A bottom plate blank around a switch: its top is the underside of the keyplate and its bottom is the bed face."""
        dims = self.dims
        size = 2 * self.switch.base.d.X
        return Box(size, size, dims.bottom_plate_z).translate(position + Vector(0, 0, -dims.keyplate_z - dims.bottom_plate_z / 2))

    def test_physical_footprint_on_both_halves(self):  # R-06
        switch, dims = self.switch, self.dims
        housing_z, clearance = switch.bottom_housing.d.Z, dims.print_profile.post_clearance
        just_inside_the_plate = -dims.keyplate_z - 0.1
        reaching_the_plate = [post for post in switch.posts.posts if housing_z + post.d.Z > dims.keyplate_z]
        mirrored_post = switch.posts.p2
        for angle in (0, 23, -37):
            for right in (False, True):
                with self.subTest(angle=angle, right=right):
                    position = Vector(dims.right_side_offset - 30 if right else 30, 20, 0)
                    rotation = -angle if right else angle
                    placement = Location(position, (0, 0, rotation))
                    bottom = add_switch_post_cutouts(self.blank_at(position), switch, dims.keyplate_z, [placement], clearance)
                    self.assertTrue(bottom.is_valid)
                    self.assertEqual(len(bottom.solids()), 1)
                    for post in switch.posts.posts:
                        terminal = Solid.make_cylinder(
                            post.d.radius,
                            post.d.Z,
                            Plane(origin=(post.p.X, -post.p.Y, -housing_z), z_dir=(0, 0, -1)),
                        ).rotate(Axis.Z, rotation).translate(position)
                        overlap = bottom & terminal
                        self.assertLess(sum(s.volume for s in overlap.solids()) if overlap else 0, 1e-7)
                    for post in reaching_the_plate:
                        centre = Vector(post.p.X, -post.p.Y).rotate(Axis.Z, rotation) + position
                        edge = Vector(post.d.radius + clearance + 0.01, 0, 0).rotate(Axis.Z, rotation)
                        self.assertFalse(bottom.is_inside(centre + Vector(0, 0, just_inside_the_plate)))
                        self.assertTrue(bottom.is_inside(centre + edge + Vector(0, 0, just_inside_the_plate)))
                        tip_z = -housing_z - post.d.Z
                        if tip_z > -dims.below_z:
                            self.assertTrue(bottom.is_inside(centre + Vector(0, 0, tip_z - 0.05)))

                    mirrored = Vector(-mirrored_post.p.X, -mirrored_post.p.Y).rotate(Axis.Z, rotation) + position
                    self.assertTrue(bottom.is_inside(mirrored + Vector(0, 0, just_inside_the_plate)))

    def test_post_clearance_sets_the_radius_of_the_hole(self):
        switch, dims = self.switch, self.dims
        position = Vector(30, 20, 0)
        post = max(switch.posts.posts, key=lambda p: p.d.Z)
        centre = Vector(post.p.X, -post.p.Y, -dims.keyplate_z - 0.1) + position
        for clearance in (0.05, 0.3):
            with self.subTest(clearance=clearance):
                bottom = add_switch_post_cutouts(self.blank_at(position), switch, dims.keyplate_z, [Location(position)], clearance)
                radius = post.d.radius + clearance
                self.assertFalse(bottom.is_inside(centre + Vector(radius - 0.02, 0, 0)))
                self.assertTrue(bottom.is_inside(centre + Vector(radius + 0.02, 0, 0)))


if __name__ == "__main__":
    unittest.main()
