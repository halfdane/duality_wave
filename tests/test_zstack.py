"""R-18, R-19, R-20."""

import pytest

from build123d import Vector

from duality_wave.models.choc import Choc
from tests.builds import make_inputs


@pytest.mark.parametrize("compact", [False, True])
def test_the_z_levels_derive_from_one_chain(compact):  # R-18
    switch, _, dims, _ = make_inputs(compact)
    assert dims.above_z == pytest.approx(8.2)
    assert dims.keyplate_z == pytest.approx(switch.bottom_housing.d.Z + dims.keyplate_under_housing)
    assert dims.below_z == pytest.approx(switch.below.d.Z + dims.floor_under_pins)
    assert dims.bottom_plate_z == pytest.approx(dims.below_z - dims.keyplate_z)
    assert dims.keyplate_z == pytest.approx(2.9)
    assert dims.below_z == pytest.approx(4.9)
    assert dims.bottom_plate_z == pytest.approx(2.0)


def test_the_default_switch_has_short_contacts_and_no_side_posts():  # R-19
    switch = Choc()
    assert switch.posts.p1.d.Z == pytest.approx(2.0)
    assert switch.posts.p2.d.Z == pytest.approx(2.0)
    assert switch.posts.a1.d.Z == 0 and switch.posts.a2.d.Z == 0
    assert switch.posts.center in switch.posts.posts
    assert len(switch.posts.posts) == 3
    assert switch.below.d.Z == pytest.approx(switch.bottom_housing.d.Z + 2.0)


def test_the_centre_post_keeps_its_length_and_does_not_set_the_depth_below_the_housing():  # R-19
    for pin_len in (0.5, 2.0, 3.0):
        switch = Choc(pin_len=pin_len)
        assert switch.posts.center.d.Z == pytest.approx(2.65)
        assert switch.below.d.Z == pytest.approx(switch.bottom_housing.d.Z + pin_len)


def test_the_longest_of_contact_and_side_post_sets_the_depth_below_the_housing():  # R-19
    switch = Choc(pin_len=1.5, side_post_len=2.5)
    assert len(switch.posts.posts) == 5
    assert switch.below.d.Z == pytest.approx(switch.bottom_housing.d.Z + 2.5)


def test_a_post_is_never_longer_than_its_datasheet_value():  # R-19
    switch = Choc(pin_len=9.0, side_post_len=9.0)
    assert switch.posts.p1.d.Z == pytest.approx(3.0)
    assert switch.posts.a1.d.Z == pytest.approx(2.65)


def test_the_switch_model_has_the_trimmed_posts_where_the_cutouts_are():  # R-19
    switch = Choc()
    part = switch.model.part
    assert part.bounding_box().min.Z == pytest.approx(-switch.bottom_housing.d.Z - switch.posts.center.d.Z)
    for post in switch.posts.posts:
        tip = -switch.bottom_housing.d.Z - post.d.Z
        assert part.is_inside(Vector(post.p.X, -post.p.Y, tip + 0.05))
        assert not part.is_inside(Vector(post.p.X, -post.p.Y, tip - 0.05))


def test_the_top_of_the_keywell_stands_a_little_over_the_caps():  # R-20
    switch, _, dims, _ = make_inputs()
    cap_top = switch.base.d.Z + switch.upper_housing.d.Z + switch.stem.d.Z + switch.cap.d.Z - switch.cap.overlap
    assert cap_top == pytest.approx(8.02)
    assert switch.above.d.Z == pytest.approx(cap_top)
    assert dims.above_z == pytest.approx(cap_top + dims.wall_over_cap)
    assert switch.model.part.bounding_box().max.Z == pytest.approx(cap_top)
