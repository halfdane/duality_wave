import unittest

from build123d import Vector

from tests import WAVE_LAYOUT

from duality_wave.coupons import create_coupon_parts, create_coupons, plate_fit_coupon, pocket_coupon, round_hole_coupon, switch_plate_coupon
from duality_wave.models.case_dimensions import CaseDimensions
from duality_wave.models.choc import Choc
from duality_wave.models.xiao import Xiao
from duality_wave.models.keys import ErgoKeys, get_points
from duality_wave.models.outline import Outline


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

    def test_round_holes_open_on_the_expected_faces(self):
        magnet, block_z, pilot_depth = self.dims.magnet_d, self.dims.above_z, self.dims.heat_insert_z
        coupon = round_hole_coupon(self.profile, magnet, block_z, pilot_depth, magnet_clearances=(0.1,), pilot_diameters=(3.0,))
        self.assertSingleSolid(coupon)
        x, pilot_y, magnet_y = 5.5, 6.0, 19.0
        self.assertFalse(coupon.is_inside(Vector(x, magnet_y, 0.3)))
        self.assertFalse(coupon.is_inside(Vector(x, magnet_y, 2 * magnet.Z - 0.1)))
        self.assertTrue(coupon.is_inside(Vector(x, magnet_y, 2 * magnet.Z + 0.1)))
        self.assertTrue(coupon.is_inside(Vector(x + magnet.radius + 0.2, magnet_y, 1.0)))
        self.assertFalse(coupon.is_inside(Vector(x, pilot_y, block_z - 0.1)))
        self.assertFalse(coupon.is_inside(Vector(x, pilot_y, block_z - pilot_depth + 0.1)))
        self.assertTrue(coupon.is_inside(Vector(x, pilot_y, block_z - pilot_depth - 0.1)))
        self.assertTrue(coupon.is_inside(Vector(x + 1.6, pilot_y, block_z - 1.0)))

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

    def test_battery_pocket_is_open_upwards(self):
        battery = self.dims.battery_pd.d
        coupon = pocket_coupon(self.profile, self.dims.xiao_position.Z, self.dims.keyplate_z, battery, xiao_clearances=(0.05,), battery_depth=2.0)
        top = self.dims.keyplate_z
        box = coupon.bounding_box()
        y = box.size.Y / 2
        x = box.size.X - 3 - (battery.X + 2 * self.profile.battery_clearance) / 2
        self.assertFalse(coupon.is_inside(Vector(x, y, top - 1.0)))
        self.assertTrue(coupon.is_inside(Vector(x, y, top - 2.5)))

    def test_all_coupons_fit_on_a_small_print_bed(self):
        coupons = create_coupons(self.switch, self.dims)
        self.assertEqual(len(coupons.solids()), 9)
        size = coupons.bounding_box().size
        self.assertLessEqual(max(size.X, size.Y), 180)
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
