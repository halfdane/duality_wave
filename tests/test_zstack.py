"""R-18 to R-23."""

import pytest
from build123d import Align, Axis, Cylinder, Plane, Vector, extrude, offset

from duality_wave.models.choc import Choc
from duality_wave.models.heat_set_insert import HeatSetInsert
from duality_wave.models.power_switch import PowerSwitch
from duality_wave.models.rubber_bumper import BumperDimensions
from duality_wave.models.screw import ScrewDimensions
from duality_wave.models.xiao import Xiao
from tests.builds import build_case, make_inputs

PARTS = ("keywell", "keyplate", "bottom")


@pytest.mark.parametrize("compact", [False, True])
def test_the_z_levels_derive_from_one_chain(compact):  # R-18
    switch, _, dims, _ = make_inputs(compact)
    assert dims.above_z == pytest.approx(8.2)
    assert dims.keyplate_z == pytest.approx(switch.bottom_housing.d.Z + dims.keyplate_under_housing)
    assert dims.below_z == pytest.approx(switch.below.d.Z + dims.floor_under_pins)
    assert dims.bottom_plate_z == pytest.approx(dims.below_z - dims.keyplate_z)
    assert dims.keyplate_z == pytest.approx(2.9)
    assert dims.below_z == pytest.approx(4.6)
    assert dims.bottom_plate_z == pytest.approx(1.7)


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


@pytest.mark.parametrize("compact", [False, True])
def test_everything_that_sticks_out_of_the_bed_face_stays_inside_the_bumpers(compact):  # R-21
    switch, _, dims, _ = make_inputs(compact)
    dome = BumperDimensions.dome_z
    poke_through = max(0.0, switch.bottom_housing.d.Z + switch.posts.center.d.Z - dims.below_z)
    usb_proud = max(0.0, Xiao.dims.d.Z + Xiao.usb.d.Z - dims.below_z + dims.xiao_ledge)
    assert poke_through == pytest.approx(0.25)
    assert usb_proud == pytest.approx(0.46)
    assert dims.lever_protrusion == pytest.approx(0.8)
    assert poke_through < dome
    assert usb_proud < dome
    assert dims.lever_protrusion < dome


@pytest.mark.parametrize("compact", [False, True])
def test_the_power_switch_lever_tip_is_where_the_protrusion_says(compact):  # R-21
    _, _, dims, _ = make_inputs(compact)
    local_top = PowerSwitch().model.bounding_box().max.Z
    assert local_top == pytest.approx(PowerSwitch.lever.reach)
    tip = dims.powerswitch_position.Z - local_top
    assert tip == pytest.approx(-dims.below_z - dims.lever_protrusion)


@pytest.mark.parametrize("compact", [False, True])
def test_the_screw_goes_through_the_insert_and_stops_short_of_the_cap(compact):  # R-21
    _, _, dims, _ = make_inputs(compact)
    screw = ScrewDimensions()
    tip = -dims.below_z + screw.head.Z + screw.shaft.Z
    assert tip >= HeatSetInsert.dims.d.Z
    assert tip < dims.above_z - 3


@pytest.mark.slow
@pytest.mark.parametrize("compact", [False, True])
def test_no_fixture_collides_with_a_part(compact):  # R-22
    case = build_case(debug=True, both_sides=False, compact=compact)[0]
    built = case.left
    fixtures = built.accessories.fixtures
    items = {
        "switches": built.accessories.switches,
        "xiao": built.accessories.xiao,
        "power_switch": fixtures.power_switch,
        "battery": fixtures.battery,
        "bumpers": fixtures.bumpers,
        "screws": fixtures.screws,
        "magnets": fixtures.magnets,
        **{name: getattr(built, name) for name in PARTS},
    }
    # the inserts are pressed into the keywell on purpose and are left out
    parts = {name: items[name] for name in PARTS}
    loose = {name: item for name, item in items.items() if item is not None and name not in PARTS}
    pairs = [(a, b) for a in loose for b in parts] + [
        ("power_switch", "battery"), ("power_switch", "xiao"), ("xiao", "battery"), ("xiao", "bumpers"),
        ("switches", "xiao"), ("screws", "xiao"), ("screws", "switches"), ("bumpers", "screws"),
    ]
    for a, b in pairs:
        first, second = loose.get(a) or parts.get(a), loose.get(b) or parts.get(b)
        if first is None or second is None:
            continue
        overlap = first & second
        volume = sum(solid.volume for solid in overlap.solids()) if overlap else 0
        assert volume < 1e-6, f"{a} collides with {b}: {volume:.3f} mm3"


@pytest.mark.slow
@pytest.mark.parametrize("compact", [False, True])
def test_the_power_switch_keeps_off_the_battery(compact):  # R-22
    case = build_case(debug=True, both_sides=False, compact=compact)[0]
    dims = case.ctx.dims
    body_top = dims.powerswitch_position.Z + PowerSwitch.dims.d.Z
    battery_bottom = dims.battery_pd.p.Z - dims.battery_pd.d.Z / 2
    assert battery_bottom - body_top >= 0.1


@pytest.mark.slow
@pytest.mark.parametrize("compact", [False, True])
def test_the_bottom_plate_keeps_its_walls_around_the_pockets_and_under_the_pins(compact):  # R-23
    case = build_case(debug=False, both_sides=False, compact=compact)[0]
    ctx = case.ctx
    dims, switch = ctx.dims, ctx.switch
    bottom = case.left.bottom
    z0 = -dims.below_z

    web = 0.5
    outline = ctx.outline.create_inner_outline(offset_by=-dims.wall_thickness - dims.print_profile.plate_clearance)
    # the chamfer on the bed edge takes away the rim, so the web only counts inside it
    inside_chamfer = offset(outline, amount=-dims.print_profile.plate_bed_chamfer)
    footprint = extrude(Plane.XY.offset(z0) * inside_chamfer, amount=BumperDimensions.base_z)
    for location in dims.bumper_locations:
        ring = Cylinder(
            BumperDimensions.radius + web, BumperDimensions.base_z, align=(Align.CENTER, Align.CENTER, Align.MIN)
        ) - Cylinder(BumperDimensions.radius, BumperDimensions.base_z, align=(Align.CENTER, Align.CENTER, Align.MIN))
        ring = (ring.translate((location.X, location.Y, z0)) & footprint)
        assert (ring & bottom).volume == pytest.approx(ring.volume, rel=0.01), f"bumper at {location}"

    housing = switch.bottom_housing.d.Z
    for key in ctx.keys.keys:
        for post in switch.posts.posts:
            xy = Vector(post.p.X, -post.p.Y).rotate(Axis.Z, key.r) + key.p
            tip = -(housing + post.d.Z)
            assert not bottom.is_inside(Vector(xy.X, xy.Y, max(tip, z0) + 0.05)), f"no room for the post at {key.p}"
            if tip > z0:
                assert bottom.is_inside(Vector(xy.X, xy.Y, tip - 0.05)), f"no floor under the post at {key.p}"
                assert tip - z0 == pytest.approx(dims.floor_under_pins)
