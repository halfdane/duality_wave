import unittest
from dataclasses import replace

import pytest

from build123d import Axis, Compound, Vector

from tests import WAVE_LAYOUT

from duality_wave.coupons import (
    create_coupon_parts,
    create_coupons,
    create_wiring_coupon_parts,
    diode_pocket_coupon,
    insert_pilot_coupon,
    magnet_pocket_coupon,
    magnet_skin_coupon,
    plate_fit_coupon,
    pocket_coupon,
    switch_plate_coupon,
    trench_coupon,
)
from duality_wave.models.case_dimensions import CaseDimensions
from duality_wave.models.choc import Choc
from duality_wave.models.diode import Diode, DiodeNotchSpec
from duality_wave.models.xiao import Xiao
from duality_wave.models.keys import ErgoKeys, get_points
from duality_wave.models.outline import Outline

SMALL_PRINT_BED = 180


@pytest.mark.integration
class CouponTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.switch = Choc()
        keys = ErgoKeys(get_points(WAVE_LAYOUT))
        outline = Outline(switch=cls.switch, keys=keys, wall_thickness=CaseDimensions.wall_thickness)
        cls.dims = CaseDimensions(switch=cls.switch, outline=outline, keys=keys)
        cls.profile = cls.dims.print_profile

    def assertSingleSolid(self, part):
        self.assertTrue(part.is_valid)
        self.assertEqual(len(part.solids()), 1)

    def test_switch_plate_holes_have_the_requested_sizes(self):
        sizes, pitch, margin = (13.8, 13.9, 14.0, 14.1), 18.0, 8.0
        coupon = switch_plate_coupon(self.switch, self.profile, self.dims.keyplate_z, sizes=sizes, reliefs=(0.0,), pitch=pitch, margin=margin)
        self.assertSingleSolid(coupon)
        y = margin + pitch / 2
        for column, size in enumerate(sizes):
            x = margin + pitch * (column + 0.5)
            with self.subTest(size=size):
                self.assertFalse(coupon.is_inside(Vector(x, y, 0.8)))
                self.assertFalse(coupon.is_inside(Vector(x + size / 2 - 0.02, y + size / 2 - 0.5, 0.8)))
                self.assertTrue(coupon.is_inside(Vector(x + size / 2 + 0.02, y, 0.8)))
                self.assertTrue(coupon.is_inside(Vector(x, y + size / 2 + 0.02, 0.8)))

    def test_plates_fit_into_the_cavity_with_their_clearance(self):
        clearances = (0.0, 0.1, 0.2)
        cavity, plates = plate_fit_coupon(self.profile, self.dims.keyplate_z, self.dims.wall_thickness, clearances=clearances)
        self.assertSingleSolid(cavity)
        self.assertEqual(len(plates), len(clearances))
        for clearance, plate in zip(clearances, plates):
            with self.subTest(clearance=clearance):
                self.assertSingleSolid(plate)
                box = plate.bounding_box()
                placed = plate.translate((-box.center().X, -box.center().Y, self.dims.wall_thickness))
                overlap = cavity & placed
                self.assertLess(sum(s.volume for s in overlap.solids()) if overlap else 0, 1e-6)
                self.assertAlmostEqual(box.size.Z, self.dims.keyplate_z, places=3)

    def test_insert_pilots_open_upwards_with_the_requested_diameters(self):
        pilot_depth, diameters, pitch, margin = self.dims.heat_insert_z, (3.0, 3.2), 9.5, 5.5
        coupon = insert_pilot_coupon(self.profile, pilot_depth, pilot_diameters=diameters, pitch=pitch, margin=margin)
        self.assertSingleSolid(coupon)
        top = coupon.bounding_box().max.Z
        self.assertGreater(top, pilot_depth)
        y = 6.0
        for index, diameter in enumerate(diameters):
            x = margin + index * pitch
            with self.subTest(diameter=diameter):
                self.assertFalse(coupon.is_inside(Vector(x, y, top - 0.1)))
                self.assertFalse(coupon.is_inside(Vector(x, y, top - pilot_depth + 0.1)))
                self.assertTrue(coupon.is_inside(Vector(x, y, top - pilot_depth - 0.1)))
                self.assertFalse(coupon.is_inside(Vector(x + diameter / 2 - 0.02, y, top - 1.0)))
                self.assertTrue(coupon.is_inside(Vector(x + diameter / 2 + 0.02, y, top - 1.0)))

    def test_magnet_pockets_have_the_requested_sizes_and_a_skin_on_the_bed(self):
        magnet, clearances = self.dims.magnet_d, (0.0, 0.2)
        coupon = magnet_pocket_coupon(self.profile, magnet, clearances=clearances)
        self.assertSingleSolid(coupon)
        top = coupon.bounding_box().max.Z
        skin = self.profile.magnet_skin
        self.assertGreaterEqual(top - skin, 2 * magnet.Z)
        # the pitch follows the largest pocket
        diameter = 2 * (magnet.radius + max(clearances))
        for index, clearance in enumerate(clearances):
            x = 3.0 + diameter / 2 + index * (diameter + 2.0)
            y = coupon.bounding_box().size.Y / 2
            radius = magnet.radius + clearance
            with self.subTest(clearance=clearance):
                self.assertTrue(coupon.is_inside(Vector(x, y, skin / 2)), "the skin is on the bed")
                self.assertFalse(coupon.is_inside(Vector(x, y, skin + 0.1)))
                self.assertFalse(coupon.is_inside(Vector(x, y, top - 0.1)), "the pocket opens upwards")
                self.assertFalse(coupon.is_inside(Vector(x + radius - 0.02, y, top / 2)))
                self.assertTrue(coupon.is_inside(Vector(x + radius + 0.05, y, top / 2)))

    def test_magnet_skins_have_the_requested_thickness(self):
        skins = (0.2, 0.6)
        coupon = magnet_skin_coupon(self.profile, self.dims.magnet_d, skins=skins)
        self.assertSingleSolid(coupon)
        diameter = 2 * (self.dims.magnet_d.radius + self.profile.magnet_clearance)
        for index, skin in enumerate(skins):
            x = 3.0 + diameter / 2 + index * (diameter + 2.0)
            y = coupon.bounding_box().size.Y / 2
            with self.subTest(skin=skin):
                self.assertTrue(coupon.is_inside(Vector(x, y, skin - 0.05)))
                self.assertFalse(coupon.is_inside(Vector(x, y, skin + 0.05)))

    def test_a_turned_over_skin_coupon_puts_its_pockets_on_top_of_the_originals(self):
        skins = (0.2, 0.6)
        coupon = magnet_skin_coupon(self.profile, self.dims.magnet_d, skins=skins)
        box = coupon.bounding_box()
        turned = coupon.rotate(Axis.X, 180).translate((0, box.min.Y + box.max.Y, box.max.Z))
        diameter = 2 * (self.dims.magnet_d.radius + self.profile.magnet_clearance)
        for index, skin in enumerate(skins):
            x, y = 3.0 + diameter / 2 + index * (diameter + 2.0), box.size.Y / 2
            with self.subTest(skin=skin):
                self.assertTrue(turned.is_inside(Vector(x, y, box.max.Z - skin / 2)))
                self.assertFalse(turned.is_inside(Vector(x, y, box.max.Z - skin - 0.1)))

    def test_xiao_pockets_have_a_window_and_a_pocket_of_the_requested_size(self):
        clearances = (0.0, 0.10)
        xiao_z, plate_z = self.dims.xiao_position.Z, self.dims.keyplate_z
        coupon = pocket_coupon(self.profile, xiao_z, plate_z, self.dims.battery_pd.d, xiao_clearances=clearances)
        self.assertSingleSolid(coupon)
        pitch_x = Xiao.dims.d.X + 2 * max(clearances) + 4
        pitch_y = Xiao.dims.d.Y + 2 * max(clearances) + 5
        for column, clearance in enumerate(clearances):
            x, y = 3 + pitch_x * (column + 0.5), 3 + pitch_y * 0.5
            half_x, half_y = Xiao.dims.d.X / 2 + clearance, Xiao.dims.d.Y / 2 + clearance
            with self.subTest(clearance=clearance):
                # the window at the bed side is smaller than the board, the pocket above it fits the board
                self.assertFalse(coupon.is_inside(Vector(x, y, 0.5)))
                self.assertTrue(coupon.is_inside(Vector(x + Xiao.dims.d.X / 2 - 0.5, y, 0.5)))
                self.assertFalse(coupon.is_inside(Vector(x + half_x - 0.02, y + half_y - 0.5, plate_z - 0.5)))
                self.assertTrue(coupon.is_inside(Vector(x + half_x + 0.02, y, plate_z - 0.5)))
                self.assertTrue(coupon.is_inside(Vector(x, y + half_y + 0.02, plate_z - 0.5)))

    def test_battery_pockets_are_open_upwards_and_differ_by_their_clearance(self):
        battery = self.dims.battery_pd.d
        clearances = (0.0, 0.2)
        coupon = pocket_coupon(
            self.profile, self.dims.xiao_position.Z, self.dims.keyplate_z, battery,
            xiao_clearances=(0.05,), battery_clearances=clearances, battery_depth=2.0)
        self.assertSingleSolid(coupon)
        top = self.dims.keyplate_z
        box = coupon.bounding_box()
        x = box.size.X - 3 - (battery.X + 2 * max(clearances)) / 2
        # walk along the column of the pockets
        column = [y / 4 for y in range(0, int(box.size.Y * 4))]
        opens = [y for y in column if not coupon.is_inside(Vector(x, y, top - 1.0))]
        self.assertTrue(opens)
        gaps = [b - a for a, b in zip(opens, opens[1:]) if b - a > 1.0]
        self.assertEqual(len(gaps), len(clearances) - 1, "one pocket for every clearance")
        self.assertTrue(all(coupon.is_inside(Vector(x, y, top - 2.5)) for y in opens))

    def test_trenches_have_the_requested_width_and_depth_and_open_upwards(self):
        widths, depths, pitch_x, pitch_y, length, margin = (0.6, 0.9), (0.8, 1.2), 20.0, 9.0, 16.0, 8.0
        z = self.dims.keyplate_z
        coupon = trench_coupon(self.profile, z, widths=widths, depths=depths, length=length, pitch_x=pitch_x, pitch_y=pitch_y, margin=margin)
        self.assertSingleSolid(coupon)
        for column, depth in enumerate(depths):
            for row, width in enumerate(widths):
                x = margin + column * pitch_x + (pitch_x - length) / 2 + length / 4
                y = margin + pitch_y * (row + 0.5) - 2.5
                self.assertFalse(coupon.is_inside(Vector(x, y, z - depth + 0.05)))
                self.assertTrue(coupon.is_inside(Vector(x, y, z - depth - 0.05)))
                for side in (-1, 1):
                    self.assertFalse(coupon.is_inside(Vector(x, y + side * (width / 2 - 0.03), z - depth / 2)))
                    self.assertTrue(coupon.is_inside(Vector(x, y + side * (width / 2 + 0.03), z - depth / 2)))

    def test_diode_pockets_are_as_wide_and_deep_as_the_diode_plus_the_slack(self):
        diode, slacks, margin = Diode(), (0.0, 0.2), 5.0
        z = self.dims.keyplate_z
        coupon = diode_pocket_coupon(self.profile, diode, z, self.dims.bottom_plate_z, slacks=slacks, margin=margin)
        self.assertSingleSolid(coupon)
        specs = [DiodeNotchSpec.of(diode, replace(self.profile, diode_width_slack=s, diode_length_slack=2 * s, diode_depth_slack=s), z, self.dims.bottom_plate_z)
                 for s in slacks]
        pitch = max(spec.width for spec in specs) + 5.0
        top = coupon.bounding_box().max.Y - margin
        for index, spec in enumerate(specs):
            x = margin + spec.width / 2 + index * pitch
            y = top - spec.total_length / 2
            self.assertFalse(coupon.is_inside(Vector(x, y, z - spec.depth + 0.05)))
            self.assertTrue(coupon.is_inside(Vector(x, y, z - spec.depth - 0.05)))
            for side in (-1, 1):
                self.assertFalse(coupon.is_inside(Vector(x + side * (spec.width / 2 - 0.03), y, z - 0.5)))
                self.assertTrue(coupon.is_inside(Vector(x + side * (spec.width / 2 + 0.03), y, z - 0.5)))
            self.assertFalse(coupon.is_inside(Vector(x, top - 0.03, z - 0.5)))
            self.assertTrue(coupon.is_inside(Vector(x, top + 0.03, z - 0.5)))
        self.assertGreater(specs[1].width, specs[0].width)

    def test_the_wiring_coupons_fit_on_a_small_print_bed_as_separate_solids(self):
        parts = create_wiring_coupon_parts(self.dims)
        self.assertEqual(set(parts), {"F trenches", "G diode pockets"})
        coupons = Compound(list(parts.values()))
        self.assertEqual(len(coupons.solids()), 2)
        size = coupons.bounding_box().size
        self.assertLessEqual(max(size.X, size.Y), SMALL_PRINT_BED)

    def test_all_coupons_fit_on_a_small_print_bed(self):
        coupons = create_coupons(self.switch, self.dims)
        self.assertEqual(len(coupons.solids()), len(create_coupon_parts(self.switch, self.dims)))
        size = coupons.bounding_box().size
        self.assertLessEqual(max(size.X, size.Y), SMALL_PRINT_BED)
        self.assertAlmostEqual(coupons.bounding_box().min.Z, 0, places=6)

    def test_coupons_do_not_touch_each_other(self):
        boxes = [part.bounding_box() for part in create_coupon_parts(self.switch, self.dims).values()]
        for index, a in enumerate(boxes):
            for b in boxes[index + 1:]:
                separated = (
                    a.max.X + 5 <= b.min.X or b.max.X + 5 <= a.min.X
                    or a.max.Y + 5 <= b.min.Y or b.max.Y + 5 <= a.min.Y
                )
                self.assertTrue(separated)


if __name__ == "__main__":
    unittest.main()
