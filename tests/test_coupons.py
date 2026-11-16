"""The calibration coupons are separate, valid solids that stand on the print bed."""

import pytest
from build123d import Box

from duality_wave.cli.common import COUPON_TARGETS, coupon_parts
from duality_wave.coupons import arrange


def apart_on_the_bed(a, b) -> bool:
    return a.max.X < b.min.X or b.max.X < a.min.X or a.max.Y < b.min.Y or b.max.Y < a.min.Y


@pytest.mark.integration
@pytest.mark.parametrize("target", COUPON_TARGETS)
def test_every_coupon_is_a_valid_solid_on_the_bed_and_apart_from_the_others(target):
    parts = coupon_parts(target)
    boxes = []
    for name, part in parts.items():
        assert part.is_valid and len(part.solids()) == 1, name
        box = part.bounding_box()
        assert box.min.Z == pytest.approx(0, abs=1e-6), name
        boxes.append(box)
    for index, a in enumerate(boxes):
        for b in boxes[index + 1:]:
            assert apart_on_the_bed(a, b)


def test_arrange_refuses_parts_that_do_not_fit_the_bed():
    bed = 50
    with pytest.raises(ValueError):
        arrange({"a": Box(bed, 10, 1), "b": Box(bed, bed, 1)}, bed=bed)
