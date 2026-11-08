"""R-18 to R-24 and R-31 to R-33."""

import pytest
from math import dist

from build123d import Align, Axis, Cylinder, Plane, Vector, Vertex, extrude, offset

from duality_wave.models.case_dimensions import CaseDimensions, CompactCaseDimensions
from duality_wave.models.choc import Choc, PostDimensions
from duality_wave.models.heat_set_insert import HeatSetInsert
from duality_wave.models.power_switch import PowerSwitch
from duality_wave.models.print_profile import PrintProfile
from duality_wave.models.rubber_bumper import BumperDimensions
from duality_wave.models.screw import ScrewDimensions
from duality_wave.models.xiao import Xiao
from duality_wave.builders.bottom import add_switch_post_cutouts, build_bottom
from duality_wave.builders.keyplate import build_keyplate
from duality_wave.builders.keywell import build_keywell
from duality_wave.geometry2d import rect_face
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


def test_the_switch_splits_into_body_and_keycap_without_losing_volume():
    switch = Choc()
    body, cap = switch.split_cap()
    whole = switch.model.part
    assert body.volume + cap.volume == pytest.approx(whole.volume, rel=1e-6)
    assert body.bounding_box().max.Z == pytest.approx(switch.cap_start_z)
    assert cap.bounding_box().min.Z == pytest.approx(switch.cap_start_z)
    assert cap.bounding_box().max.Z == pytest.approx(whole.bounding_box().max.Z)
    assert body.bounding_box().min.Z == pytest.approx(whole.bounding_box().min.Z)


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
        "keycaps": built.accessories.keycaps,
        "xiao": built.accessories.xiao,
        "power_switch": fixtures.power_switch,
        "battery": fixtures.battery,
        "bumpers": fixtures.bumpers,
        "screws": fixtures.screws,
        "magnets": fixtures.magnets,
        "spacers": fixtures.spacers,
        **{name: getattr(built, name) for name in PARTS},
    }
    # the inserts are pressed into the keywell on purpose and are left out
    parts = {name: items[name] for name in PARTS}
    loose = {name: item for name, item in items.items() if item is not None and name not in PARTS}
    pairs = [(a, b) for a in loose for b in parts] + [
        ("power_switch", "battery"), ("power_switch", "xiao"), ("xiao", "battery"), ("xiao", "bumpers"),
        ("switches", "xiao"), ("screws", "xiao"), ("screws", "switches"), ("bumpers", "screws"),
        ("keycaps", "xiao"), ("screws", "keycaps"),
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
    bottom = add_switch_post_cutouts(
        build_bottom(ctx), switch, dims.keyplate_z, Side.left(ctx).switch_locations, dims.print_profile.post_clearance)
    z0 = -dims.below_z

    web = 0.5
    outline = ctx.outline.create_inner_outline(offset_by=-dims.wall_thickness - dims.print_profile.plate_clearance)
    # the chamfer on the bed edge takes away the rim, so the web only counts inside it
    inside_chamfer = offset(outline, amount=-dims.print_profile.plate_bed_chamfer)
    footprint = extrude(Plane.XY.offset(z0) * inside_chamfer, amount=BumperDimensions.base_z)
    pocket_radius = BumperDimensions.radius + dims.print_profile.bumper_clearance
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


def wall_to_edge(face, center, radius):
    """The wall between a round hole and the edge of a face. Negative when the hole leaves the face."""
    distance = face.outer_wire().distance_to(Vertex(center.X, center.Y, 0))
    return (distance if face.is_inside(Vector(center.X, center.Y, 0)) else -distance) - radius


def wall_to_cutouts(faces, center, radius):
    """The wall between a round hole and the key cutouts. Negative when the hole reaches into a cutout."""
    if any(face.is_inside(Vector(center.X, center.Y, 0)) for face in faces):
        return -radius
    return min(face.outer_wire().distance_to(Vertex(center.X, center.Y, 0)) for face in faces) - radius


def test_hand_placed_holes_keep_a_wall_to_each_other_and_to_the_edges():  # R-31
    ctx = make_context()
    dims, outline = ctx.dims, ctx.outline
    profile = dims.print_profile
    screws, magnets, bumpers = dims.fastener_positions, dims.magnet_positions, dims.bumper_locations
    head_recess = ctx.screw.dims.head.radius + profile.screw_head_clearance
    pilot = profile.insert_pilot_radius
    magnet = dims.magnet_d.radius + profile.magnet_clearance
    bumper = ctx.bumper.dims.radius + profile.bumper_clearance

    plate_edge = outline.create_inner_outline(offset_by=-dims.wall_thickness - profile.plate_clearance).faces()[0]
    cavity = outline.inner_sketch.faces()[0]
    battery = dims.battery_pd
    battery_recess = rect_face(
        (battery.p.X, battery.p.Y), battery.d.X + 2 * profile.battery_clearance, battery.d.Y + 2 * profile.battery_clearance)
    cutouts = [*outline.keywell_sketch.faces(), battery_recess]
    layers = {
        "bottom plate": ([("head recess", screws, head_recess), ("bumper", bumpers, bumper)], plate_edge, []),
        "keywell": ([("pilot", screws, pilot), ("magnet", magnets, magnet)], cavity, cutouts),
    }

    walls = {}
    for layer, (holes, edge, key_cutouts) in layers.items():
        placed = [(kind, i, center, radius) for kind, centers, radius in holes for i, center in enumerate(centers)]
        for n, (kind, i, center, radius) in enumerate(placed):
            walls[f"{layer}: {kind} {i} to the edge"] = wall_to_edge(edge, center, radius)
            if key_cutouts:
                walls[f"{layer}: {kind} {i} to the cutouts"] = wall_to_cutouts(key_cutouts, center, radius)
            for other_kind, j, other, other_radius in placed[n + 1:]:
                walls[f"{layer}: {kind} {i} to {other_kind} {j}"] = (
                    dist((center.X, center.Y), (other.X, other.Y)) - radius - other_radius
                )

    too_thin = {name: round(wall, 2) for name, wall in walls.items() if wall < profile.min_wall}
    assert not too_thin


def test_a_magnet_pocket_opens_into_the_cavity_and_a_skin_closes_the_top_face():  # R-32
    ctx = make_context()
    dims, profile = ctx.dims, ctx.dims.print_profile
    keywell = build_keywell(ctx)
    radius = dims.magnet_d.radius + profile.magnet_clearance
    assert dims.above_z - dims.magnet_z >= profile.magnet_skin - 1e-6
    assert dims.magnet_positions
    for magnet in dims.magnet_positions:
        def solid(z, away=0.0):
            return keywell.is_inside(Vector(magnet.X + away, magnet.Y, z))

        assert not solid(0.1), "the pocket opens at the cavity"
        assert not solid(dims.magnet_z - 0.1), "the pocket reaches the skin"
        assert solid(dims.magnet_z + 0.1) and solid(dims.above_z - 0.1), "the skin closes the top face"
        assert solid(dims.magnet_z / 2, away=radius + 0.3), "the pocket has a wall"


def test_a_spacer_disc_fills_the_pocket_and_the_keyplate_carries_it():  # R-33
    ctx = make_context()
    dims, profile = ctx.dims, ctx.dims.print_profile
    spacer = dims.magnet_spacer
    assert spacer.radius < dims.magnet_d.radius + profile.magnet_clearance
    assert spacer.Z + 2 * dims.magnet_d.Z + profile.magnet_spacer_gap == pytest.approx(dims.magnet_z)

    keyplate = build_keyplate(ctx)
    for magnet in dims.magnet_positions:
        rim = [Vector(magnet.X, magnet.Y, -0.1)] + [
            Vector(magnet.X, magnet.Y, -0.1) + Vector(spacer.radius, 0).rotate(Axis.Z, angle) for angle in range(0, 360, 45)
        ]
        assert all(keyplate.is_inside(point) for point in rim), f"no keyplate under the spacer at {magnet}"


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
        "top of the magnets": dims.magnet_z,
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
    # the skin over the magnets never gets thinner than asked
    skin = dims.above_z - dims.magnet_z
    assert dims.print_profile.magnet_skin - eps <= skin < dims.print_profile.magnet_skin + layer + eps
