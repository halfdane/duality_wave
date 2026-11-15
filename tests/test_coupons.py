import unittest

import pytest

from build123d import Box, Compound

from tests import WAVE_LAYOUT

from duality_wave.coupons import (
    BED_SIZE,
    arrange,
    create_coupon_parts,
    create_coupons,
    create_wiring_coupon_parts,
)
from duality_wave.case_dimensions import CaseDimensions
from duality_wave.models.choc import Choc
from duality_wave.models.keys import ErgoKeys, get_points
from duality_wave.models.outline import Outline

SMALL_PRINT_BED = 180
EDGE_MARGIN = 5


@pytest.mark.integration
class CouponTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.switch = Choc()
        keys = ErgoKeys(get_points(WAVE_LAYOUT))
        outline = Outline(switch=cls.switch, keys=keys, wall_thickness=CaseDimensions.wall_thickness)
        cls.dims = CaseDimensions(switch=cls.switch, outline=outline, keys=keys)

    def assertFitsSmallPrintBed(self, coupons):
        box = coupons.bounding_box()
        self.assertGreaterEqual(min(box.min.X, box.min.Y), -1e-6)
        self.assertLessEqual(max(box.max.X, box.max.Y), SMALL_PRINT_BED - 2 * EDGE_MARGIN + 1e-6)

    def test_the_second_plate_holds_the_wiring_and_the_plate_fit_as_separate_solids(self):
        parts = create_wiring_coupon_parts(self.dims)
        coupons = Compound(list(parts.values()))
        self.assertEqual(len(coupons.solids()), len(parts))
        self.assertFitsSmallPrintBed(coupons)

    def test_all_coupons_fit_on_a_small_print_bed(self):
        coupons = create_coupons(self.switch, self.dims)
        self.assertEqual(len(coupons.solids()), len(create_coupon_parts(self.switch, self.dims)))
        self.assertFitsSmallPrintBed(coupons)
        self.assertAlmostEqual(coupons.bounding_box().min.Z, 0, places=6)

    def test_arrange_refuses_parts_that_do_not_fit_the_bed(self):
        with self.assertRaises(ValueError):
            arrange({"a": Box(BED_SIZE, 10, 1), "b": Box(BED_SIZE, BED_SIZE, 1)})

    def test_coupons_do_not_touch_each_other(self):
        plates = (create_coupon_parts(self.switch, self.dims), create_wiring_coupon_parts(self.dims))
        for plate in plates:
            self.assertSeparated([part.bounding_box() for part in plate.values()])

    def assertSeparated(self, boxes):
        for index, a in enumerate(boxes):
            for b in boxes[index + 1:]:
                separated = (
                    a.max.X + 5 <= b.min.X or b.max.X + 5 <= a.min.X
                    or a.max.Y + 5 <= b.min.Y or b.max.Y + 5 <= a.min.Y
                )
                self.assertTrue(separated)


if __name__ == "__main__":
    unittest.main()
