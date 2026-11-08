import unittest

import pytest
from dataclasses import replace

from build123d import Axis, Box, Location, Plane, Solid, Vector
from ocp_viewer import Render

from duality_wave.builders.bottom import add_switch_post_cutouts

from duality_wave.models.choc import Choc
from duality_wave.models.features import magnet_recess_cutter, switch_cutter
from duality_wave.models.model_types import RoundDimensions
from duality_wave.models.print_profile import PrintProfile
from tests.builds import PARTS, build_case


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


def pushed_names(push_object):
    return [call.kwargs["name"] for call in push_object.call_args_list]


@pytest.mark.integration
def test_debug_off_pushes_nothing_and_builds_no_accessories(quiet):  # R-07
    case, push_object = quiet
    push_object.assert_not_called()
    assert case.left.accessories is None


@pytest.mark.integration
def test_debug_off_builds_the_same_parts_as_debug_on(quiet, full):  # R-07
    for name in PARTS:
        assert getattr(quiet[0].left, name).volume == pytest.approx(getattr(full.left, name).volume, abs=1e-3), name


@pytest.mark.integration
def test_debug_on_pushes_every_part_and_the_debug_group_last():
    case, push_object = build_case(debug=True)
    names = pushed_names(push_object)
    assert names[-1] == "debug"
    assert names.count("debug") == 1
    for side in ("left", "right"):
        for name in ("accessories", *PARTS):
            assert f"{name}_{side}" in names[:-1]


@pytest.mark.integration
def test_debug_group_starts_hidden_and_the_parts_do_not():
    _, push_object = build_case(debug=True)
    modes = {call.kwargs["name"]: call.kwargs.get("mode") for call in push_object.call_args_list}
    assert modes.pop("debug") == Render.NONE
    assert all(mode is None for mode in modes.values())


def test_a_debug_group_the_viewer_already_knows_keeps_the_visibility_of_the_user():
    from unittest.mock import patch

    from duality_wave.builders.viewer import OcpViewer

    for states, mode in (({}, Render.NONE), ({"/wave/debug": [0, 0]}, None)):
        with patch("ocp_viewer.push_object") as push_object, patch("ocp_viewer.status", return_value={"states": states}):
            OcpViewer().push_debug()
        assert push_object.call_args.kwargs["mode"] == mode


@pytest.mark.integration
def test_debug_group_holds_what_the_builders_noted():
    _, push_object = build_case(debug=True)
    group = next(c.args[0] for c in push_object.call_args_list if c.kwargs["name"] == "debug")
    for name in PARTS:
        assert group[name], f"nothing noted for {name}"


@pytest.mark.integration
def test_accessories_are_built_for_both_halves(full):
    for built in (full.left, full.right):
        for part in built.accessories.as_dict().values():
            assert part.volume > 0


@pytest.mark.integration
def test_one_sided_case_has_no_right_half(quiet):
    case, _ = quiet
    assert case.right is None
    for name in PARTS:
        assert getattr(case.left, name).volume > 0


@pytest.mark.integration
def test_right_half_mirrors_the_left_half(full):  # R-02
    offset = full.ctx.dims.right_side_offset
    for name in PARTS:
        left, right = getattr(full.left, name), getattr(full.right, name)
        assert left.volume / right.volume == pytest.approx(1, abs=1e-3), name
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
    def test_physical_footprint_on_both_halves(self):  # R-06
        for angle in (0, 23, -37):
            for right in (False, True):
                with self.subTest(angle=angle, right=right):
                    position = Vector(170 if right else 30, 20, 0)
                    rotation = -angle if right else angle
                    placement = Location(position, (0, 0, rotation))
                    blank = Box(30, 30, 3).translate(position + Vector(0, 0, -4.4))
                    bottom = add_switch_post_cutouts(blank, Choc, 2.9, [placement], PrintProfile().post_clearance)
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
                        edge = Vector(post.d.radius + PrintProfile().post_clearance + 0.01, 0, 0).rotate(Axis.Z, rotation)
                        self.assertFalse(bottom.is_inside(center))
                        self.assertTrue(bottom.is_inside(center + edge))

                    mirrored_terminal = Vector(-Choc.posts.p2.p.X, -Choc.posts.p2.p.Y, -4)
                    mirrored_terminal = mirrored_terminal.rotate(Axis.Z, rotation) + position
                    self.assertTrue(bottom.is_inside(mirrored_terminal))
                    self.assertTrue(bottom.is_inside(position + Vector(0, 0, -5.3)))

    def test_post_clearance_sets_the_radius_of_the_hole(self):
        position = Vector(30, 20, 0)
        blank = Box(30, 30, 3).translate(position + Vector(0, 0, -4.4))
        post = Choc.posts.center
        for clearance in (0.05, 0.3):
            with self.subTest(clearance=clearance):
                bottom = add_switch_post_cutouts(blank, Choc, 2.9, [Location(position)], clearance)
                center = Vector(post.p.X, -post.p.Y, -4) + position
                radius = post.d.radius + clearance
                self.assertFalse(bottom.is_inside(center + Vector(radius - 0.02, 0, 0)))
                self.assertTrue(bottom.is_inside(center + Vector(radius + 0.02, 0, 0)))


if __name__ == "__main__":
    unittest.main()
