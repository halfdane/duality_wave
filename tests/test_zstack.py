"""R-18 to R-24."""

import pytest
from build123d import Align, Axis, Cylinder, Plane, Vector, extrude, offset

from duality_wave.models.case_dimensions import CaseDimensions, CompactCaseDimensions
from duality_wave.models.choc import Choc, PostDimensions
from duality_wave.models.heat_set_insert import HeatSetInsert
from duality_wave.models.power_switch import PowerSwitch
from duality_wave.models.print_profile import PrintProfile
from duality_wave.models.rubber_bumper import BumperDimensions
from duality_wave.models.screw import ScrewDimensions
from duality_wave.models.xiao import Xiao
from duality_wave.builders.bottom import add_switch_post_cutouts, build_bottom
from duality_wave.builders.side import Side
from tests.builds import make_context, make_inputs

PARTS = ("keywell", "keyplate", "bottom")


@pytest.mark.parametrize("compact", [False, True])
def test_the_z_levels_derive_from_one_chain(compact):  # R-18
    switch, _, dims, _ = make_inputs(compact)
    layer = dims.print_profile.layer_height
    assert switch.bottom_housing.d.Z + dims.keyplate_under_housing - 1e-6 <= dims.keyplate_z < switch.bottom_housing.d.Z + dims.keyplate_under_housing + layer
    assert dims.below_z == pytest.approx(switch.below.d.Z + dims.floor_under_pins)
    assert dims.bottom_plate_z == pytest.approx(dims.below_z - dims.keyplate_z)
    assert switch.above.d.Z + dims.wall_over_cap - 1e-6 <= dims.above_z < switch.above.d.Z + dims.wall_over_cap + layer


def test_a_post_of_length_zero_does_not_exist():  # R-19
    switch = Choc(pin_len=1.5, side_post_len=0)
    assert switch.posts.a1 not in switch.posts.posts and switch.posts.a2 not in switch.posts.posts
    assert switch.posts.center in switch.posts.posts
    assert switch.below.d.Z == pytest.approx(switch.bottom_housing.d.Z + 1.5)


def test_the_centre_post_keeps_its_length_and_does_not_set_the_depth_below_the_housing():  # R-19
    for pin_len in (0.5, 2.0, 3.0):
        switch = Choc(pin_len=pin_len)
        assert switch.posts.center.d.Z == pytest.approx(PostDimensions().center.d.Z)
        assert switch.below.d.Z == pytest.approx(switch.bottom_housing.d.Z + pin_len)


def test_the_longest_of_contact_and_side_post_sets_the_depth_below_the_housing():  # R-19
    switch = Choc(pin_len=1.5, side_post_len=2.5)
    assert len(switch.posts.posts) == len(PostDimensions().posts)
    assert switch.below.d.Z == pytest.approx(switch.bottom_housing.d.Z + 2.5)


def test_a_post_is_never_longer_than_its_datasheet_value():  # R-19
    switch = Choc(pin_len=9.0, side_post_len=9.0)
    datasheet = PostDimensions()
    assert switch.posts.p1.d.Z == pytest.approx(datasheet.p1.d.Z)
    assert switch.posts.a1.d.Z == pytest.approx(datasheet.a1.d.Z)


def test_the_switch_model_has_the_trimmed_posts_where_the_cutouts_are():  # R-19
    switch = Choc()
    part = switch.model.part
    assert part.bounding_box().min.Z == pytest.approx(-switch.bottom_housing.d.Z - switch.posts.center.d.Z)
    for post in switch.posts.posts:
        tip = -switch.bottom_housing.d.Z - post.d.Z
        assert part.is_inside(Vector(post.p.X, -post.p.Y, tip + 0.05))
        assert not part.is_inside(Vector(post.p.X, -post.p.Y, tip - 0.05))


def test_the_top_of_the_keywell_stands_a_little_over_the_caps():  # R-18
    switch, _, dims, _ = make_inputs()
    cap_top = switch.base.d.Z + switch.upper_housing.d.Z + switch.stem.d.Z + switch.cap.d.Z - switch.cap.overlap
    assert switch.above.d.Z == pytest.approx(cap_top)
    assert dims.above_z == pytest.approx(cap_top + dims.wall_over_cap)
    assert switch.model.part.bounding_box().max.Z == pytest.approx(cap_top)


@pytest.mark.parametrize("compact", [False, True])
def test_everything_that_sticks_out_of_the_bed_face_stays_inside_the_bumpers(compact):  # R-21
    switch, _, dims, _ = make_inputs(compact)
    dome = BumperDimensions.dome_z
    poke_through = max(0.0, switch.bottom_housing.d.Z + switch.posts.center.d.Z - dims.below_z)
    usb_proud = max(0.0, Xiao.dims.d.Z + Xiao.usb.d.Z - dims.below_z - dims.xiao_position.Z)
    assert poke_through < dome
    assert usb_proud < dome


@pytest.mark.parametrize("compact", [False, True])
def test_the_power_switch_lever_tip_is_where_the_protrusion_says(compact):  # R-21
    _, _, dims, _ = make_inputs(compact)
    local_top = PowerSwitch().model.bounding_box().max.Z
    assert local_top == pytest.approx(PowerSwitch.lever.reach)
    protrusion = -(dims.powerswitch_position.Z - local_top) - dims.below_z
    assert dims.lever_protrusion <= protrusion < dims.lever_protrusion + dims.print_profile.layer_height
    assert protrusion < BumperDimensions.dome_z


@pytest.mark.parametrize("compact", [False, True])
def test_the_screw_goes_through_the_insert_and_stops_short_of_the_cap(compact):  # R-21
    switch, _, dims, _ = make_inputs(compact)
    screw = ScrewDimensions()
    tip = -dims.below_z + screw.head.Z + screw.shaft.Z
    cap_underside = switch.above.d.Z - switch.cap.d.Z
    assert tip >= HeatSetInsert.dims.d.Z
    assert tip < cap_underside


@pytest.mark.integration
@pytest.mark.parametrize("variant", ["full", "compact"])
def test_no_fixture_collides_with_a_part(variant, request):  # R-22
    built = request.getfixturevalue(variant).left
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


@pytest.mark.parametrize("compact", [False, True])
def test_the_power_switch_keeps_off_the_battery(compact):  # R-22
    dims = make_inputs(compact)[2]
    body_top = dims.powerswitch_position.Z + PowerSwitch.dims.d.Z
    battery_bottom = dims.battery_pd.p.Z - dims.battery_pd.d.Z / 2
    assert battery_bottom - body_top > 0


@pytest.mark.parametrize("compact", [False, True])
def test_the_bottom_plate_keeps_its_walls_around_the_pockets_and_under_the_pins(compact):  # R-23
    ctx = make_context(compact)
    dims, switch = ctx.dims, ctx.switch
    bottom = add_switch_post_cutouts(build_bottom(ctx), switch, dims.keyplate_z, Side.left(ctx).switch_locations)
    z0 = -dims.below_z

    web = 0.5
    outline = ctx.outline.create_inner_outline(offset_by=-dims.wall_thickness - dims.print_profile.plate_clearance)
    # the chamfer on the bed edge takes away the rim, so the web only counts inside it
    inside_chamfer = offset(outline, amount=-dims.print_profile.plate_bed_chamfer)
    footprint = extrude(Plane.XY.offset(z0) * inside_chamfer, amount=BumperDimensions.base_z)
    pocket_radius = BumperDimensions.radius + dims.clearance
    for location in dims.bumper_locations:
        ring = Cylinder(
            pocket_radius + web, BumperDimensions.base_z, align=(Align.CENTER, Align.CENTER, Align.MIN)
        ) - Cylinder(pocket_radius, BumperDimensions.base_z, align=(Align.CENTER, Align.CENTER, Align.MIN))
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


def test_a_height_snaps_to_whole_layers():  # R-24
    profile = PrintProfile(layer_height=0.2)
    assert profile.snap_up(2.0) == pytest.approx(2.0)
    assert profile.snap_up(2.0 + 1e-12) == pytest.approx(2.0)
    assert profile.snap_up(2.01) == pytest.approx(2.2)
    assert profile.snap_down(2.19) == pytest.approx(2.0)
    assert profile.snap_down(2.2 - 1e-12) == pytest.approx(2.2)
    assert PrintProfile(layer_height=0.12).snap_up(1.0) == pytest.approx(1.08)


def bed_layers(dims, z):
    """The number of layers between the bed face and z. A whole number puts z on a layer boundary."""
    return (z + dims.below_z) / dims.print_profile.layer_height


@pytest.mark.parametrize("layer_height", [0.2, 0.16, 0.12, 0.28])
@pytest.mark.parametrize("compact", [False, True])
def test_every_level_sits_on_a_layer_boundary_counted_from_the_bed_face(compact, layer_height):  # R-24
    switch, keys, _, outline = make_inputs(compact)
    cls = CompactCaseDimensions if compact else CaseDimensions
    dims = cls(switch=switch, outline=outline, keys=keys, print_profile=PrintProfile(layer_height=layer_height))
    levels = {
        "keyplate top": 0.0,
        "plate top": -dims.keyplate_z,
        "keywell top": dims.above_z,
        "xiao back": dims.xiao_position.Z,
        "power switch": dims.powerswitch_position.Z,
        "battery roof": dims.battery_pd.p.Z + dims.battery_pd.d.Z / 2,
    }
    for name, z in levels.items():
        layers = bed_layers(dims, z)
        assert layers == pytest.approx(round(layers), abs=1e-4), f"{name} at {z} is {layers} layers above the bed"


@pytest.mark.parametrize("layer_height", [0.2, 0.16, 0.12, 0.28])
@pytest.mark.parametrize("compact", [False, True])
def test_snapping_moves_a_level_only_in_the_safe_direction(compact, layer_height):  # R-24
    switch, keys, _, outline = make_inputs(compact)
    cls = CompactCaseDimensions if compact else CaseDimensions
    dims = cls(switch=switch, outline=outline, keys=keys, print_profile=PrintProfile(layer_height=layer_height))
    layer = layer_height
    eps = 1e-6
    # the keywell stays at least wall_over_cap over the caps, the plate keeps its pins and its housing room
    assert switch.above.d.Z + dims.wall_over_cap - eps <= dims.above_z < switch.above.d.Z + dims.wall_over_cap + layer + eps
    assert dims.below_z >= switch.below.d.Z + dims.floor_under_pins - eps
    assert dims.keyplate_z >= switch.bottom_housing.d.Z + dims.keyplate_under_housing - eps
    assert dims.below_z - dims.keyplate_z >= 0
    # the XIAO is never lower than asked, the power switch body never higher, the battery roof never thinner than the wall
    assert -dims.xiao_ledge - eps <= dims.xiao_position.Z < -dims.xiao_ledge + layer + eps
    raw_switch = -(dims.below_z - PowerSwitch.lever.reach + dims.lever_protrusion)
    assert raw_switch - layer - eps < dims.powerswitch_position.Z <= raw_switch + eps
    roof = dims.battery_pd.p.Z + dims.battery_pd.d.Z / 2
    assert dims.above_z - roof >= dims.wall_thickness - eps
