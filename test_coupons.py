import os
import unittest

from build123d import Vector

from coupons import create_coupons, plate_fit_coupon, pocket_coupon, round_hole_coupon, switch_plate_coupon
from duality_wave import CaseDimensions
from models.choc import Choc
from models.keys import ErgoKeys, get_points
from models.outline import Outline


class CouponTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.switch = Choc()
        keys = ErgoKeys(get_points(os.path.join(os.path.dirname(__file__), "ergogen", "wave.yml")))
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

    def test_pocket_coupon_is_a_single_valid_part(self):
        self.assertSingleSolid(pocket_coupon(self.profile, self.dims.weight_d, self.dims.battery_pd.d))

    def test_all_coupons_fit_on_the_print_bed(self):
        coupons = create_coupons(self.switch, self.dims)
        self.assertEqual(len(coupons.solids()), 9)
        size = coupons.bounding_box().size
        self.assertLessEqual(max(size.X, size.Y), 256)
        self.assertAlmostEqual(coupons.bounding_box().min.Z, 0, places=6)


if __name__ == "__main__":
    unittest.main()
