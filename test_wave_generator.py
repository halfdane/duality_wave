import unittest
from unittest.mock import patch

from build123d import Axis, Box, Location, Plane, Solid, Vector

from models.choc import Choc
from duality_wave import CaseDimensions
from models.keys import ErgoKeys, get_points
from models.outline import Outline
from wave_generator import WaveCase


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
