"""R-36 to R-42: the wiring file, the diode pockets, the trenches and the channel."""

from dataclasses import replace

import numpy as np
import pytest
from build123d import Vector

from duality_wave.paths import WIRING_FILE
from duality_wave.wiring import check
from duality_wave.wiring import nets as nets_module
from duality_wave.wiring.geometry import inside
from duality_wave.wiring.plan import LAYERS, SIDES, WiringFileError, WiringPlan, read_file
from duality_wave.wiring.plate import DEFAULT_Y, MIN_WALL, Plate
from duality_wave.wiring.rounded import normalize, sample, tangent_overlaps
from tests.builds import make_context


SIDE_TEXT = """{name}:
  notches:
    k: {{side: -1, y: -1.5}}
  underside:
    col 1:
      - {trench}
  top: {{}}
{extra}"""


def write_file(tmp_path, trench="[[10, 20], [14, 30]]", channel="{from: [1, 2], to: [8, 3]}", left_extra=""):
    text = "diode: {body_d: 2.0, body_l: 4.2, lead_d: 0.5}\nchannel: " + channel + "\n"
    text += SIDE_TEXT.format(name="left", trench=trench, extra=left_extra) + SIDE_TEXT.format(name="right", trench="[[10, 20], [14, 30]]", extra="")
    path = tmp_path / "wiring.yaml"
    path.write_text(text)
    return path


@pytest.fixture(scope="module")
def ctx():
    return make_context()


@pytest.fixture(scope="module")
def plan():
    return WiringPlan.load(WIRING_FILE)


@pytest.fixture(scope="module", params=SIDES)
def half(request, ctx, plan):
    """The plate of one half, its notches and the matrix nets with the trenches of the file."""
    return check.Half.of(ctx, plan, request.param)


@pytest.fixture(scope="module")
def result(half):
    return check.check(half)


def test_the_wiring_file_passes_every_check(result):  # R-36
    assert result.problems == []


def test_every_key_has_a_diode_pocket_with_a_wall(half):  # R-37
    assert set(half.plan.notches) == set(half.plate.names)
    for name, notch in half.notches.items():
        assert notch.wall >= MIN_WALL - 1e-6, f"{name}: wall {notch.wall:.2f} next to {notch.closest}"


def test_the_file_has_trenches_for_every_net_once_and_the_thumbs_keep_their_columns(half):  # R-38
    assert sorted(half.plan.underside) == sorted(net.name for net in half.nets)
    assert [net.name for net in half.nets] == ["col 1", "col 2", "col 3", "col 4", "col 5", "row 1", "row 2", "row 3", "row 4"]
    layout, _, rows = nets_module.key_layout(half.plate)
    assert (layout["thumb_reachy"], layout["thumb_middle"]) == ((0, rows), (1, rows))


def test_a_diode_whose_lead_crosses_the_cutout_needs_a_sleeve_and_a_diode_stays_along_its_cutout(half):  # R-37
    plate = half.plate
    crossing = [name for name, (side, _) in half.plan.notches.items() if side != plate.default_side]
    assert half.sleeves() == crossing
    low, high = plate.y_range()
    assert low < plate.spec.pocket(plate.cutout_half, 1, DEFAULT_Y)[1] < high
    for name, (_, y) in half.plan.notches.items():
        assert low - 1e-6 <= y <= high + 1e-6, name
    _, centre, _, length = plate.spec.pocket(plate.cutout_half, 1, low)
    assert centre - length / 2 == pytest.approx(-plate.cutout_half)
    _, centre, _, length = plate.spec.pocket(plate.cutout_half, 1, high)
    assert centre + length / 2 == pytest.approx(plate.cutout_half)


def test_every_trench_reaches_its_terminals_and_the_trenches_of_a_net_join_up_in_the_channel(half):  # R-39
    assert check.check_nets(half) == []


def test_a_net_that_misses_the_channel_or_a_terminal_is_reported(half):  # R-39
    far = replace(half.plan, channel=half.plan.channel + 100)
    assert any("does not reach the channel" in p for p in check.check_nets(replace(half, plan=far)))
    only_the_stub = [replace(half.nets[0], paths=half.nets[0].paths[-1:]), *half.nets[1:]]
    assert any("no trench reaches the terminal" in p for p in check.check_nets(replace(half, nets=only_the_stub)))


def test_no_wire_comes_near_a_contact_it_does_not_serve_or_runs_beside_another_net(half):  # R-40
    assert check.check_keepouts(half) == []
    assert check.check_parallel(half) == []


def test_the_power_wires_start_at_the_pins_inside_the_cut_and_stay_out_of_the_pockets(half):  # R-41
    plate, top = half.plate, half.plan.top
    assert len(top) == len(plate.power.tips[:nets_module.POWER_PINS])
    for tip, paths in zip(plate.power.tips, top.values()):
        assert inside(tip, plate.power.pins), "the pin tip lies outside the pin zone"
        assert min(np.linalg.norm(np.array(end[:2]) - tip) for path in paths for end in (path[0], path[-1])) < check.TOUCH
    blocked = [plate.power.body, *plate.top_cutouts.values(), *(n.poly for n in half.notches.values())]
    for paths in top.values():
        for path in paths:
            assert not any(inside(p, poly) for p in sample(path) for poly in blocked)


def test_the_wall_near_a_terminal_is_skipped_only_for_the_pocket_that_holds_the_terminal():  # R-39
    def box(x0, y0, x1, y1):
        return np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], dtype=float)

    mine, neighbour = box(-1, -4, 1, 0), box(-3, 0.6, 3, 5)
    terminal = np.array([[0.0, -1.0]])
    wire = np.array([[x, 0.3] for x in np.linspace(-1.5, 1.5, 31)])
    assert check.thinnest(wire, [mine], 0.4, False, terminal)[0] > 1
    assert check.thinnest(wire, [neighbour], 0.4, False, terminal)[0] < 0
    assert check.thinnest(wire, [mine, neighbour], 0.4, False, terminal)[0] < 0


def test_the_channel_opens_into_the_xiao_pocket_and_keeps_its_walls(half, result):  # R-42
    assert [p for p in result.problems if "channel" in p] == []
    assert result.walls["channel to outline"][0] >= MIN_WALL
    edge = check.densify(half.plan.channel)
    assert check.inside_any(edge, [half.plate.xiao_pocket]).any()


def test_a_wiring_file_holds_plain_coordinates_and_a_corner_has_a_radius_only_when_the_file_says_so(tmp_path):  # R-36
    path = write_file(tmp_path, trench="[[10, 20], [12.5, 20, 0.75], [12.5, 30], [14, 30]]")
    plan = WiringPlan.load(path)
    assert plan.left.notches == {"k": (-1, -1.5)}
    assert plan.left.channel.min(axis=0).tolist() == [1.0, 2.0] and plan.left.channel.max(axis=0).tolist() == [8.0, 3.0]
    path_left = plan.left.underside["col 1"][0]
    assert [v[:2] for v in path_left] == [(10.0, 20.0), (12.5, 20.0), (12.5, 30.0), (14.0, 30.0)]
    assert [v[2] for v in path_left] == [0.0, 0.75, pytest.approx(0.75), 0.0]
    assert read_file(path)["sides"]["left"]["underside"]["col 1"][0][1] == [12.5, 20.0, 0.75]
    assert read_file(path)["sides"]["left"]["underside"]["col 1"][0][2] == [12.5, 30.0]


@pytest.mark.parametrize("trench, message", [
    ("[[10, 20]]", "at least two vertices"),
    ("[[10, 20], matrix_ring_top.p1]", "vertex 2.*not 'matrix_ring_top.p1'"),
    ("[[10, 20], {at: a}]", "vertex 2"),
    ("[[10, 20], [1, 2, 3, 4]]", "vertex 2"),
    ("[[10, 20], [1, x]]", "vertex 2"),
])
def test_a_mistake_in_the_file_gives_a_message_that_says_where(tmp_path, trench, message):  # R-36
    with pytest.raises(WiringFileError, match=f"left underside col 1 trench 1.*{message}"):
        WiringPlan.load(write_file(tmp_path, trench=trench))


def test_the_channel_is_the_rectangle_between_two_corners_and_belongs_to_both_halves(tmp_path):  # R-36, R-42
    plan = WiringPlan.load(write_file(tmp_path, channel="{from: [8, 3], to: [1, 2]}"))
    assert np.array_equal(plan.left.channel, plan.right.channel)
    assert plan.left.channel.tolist() == [[1, 2], [8, 2], [8, 3], [1, 3]]
    with pytest.raises(WiringFileError, match="channel"):
        WiringPlan.load(write_file(tmp_path, channel="{from: [1, 2], to: [1, 3]}"))
    with pytest.raises(WiringFileError, match="channel"):
        WiringPlan.load(write_file(tmp_path, channel="{from: matrix_ring_top.p1, to: [1, 3]}"))
    with pytest.raises(WiringFileError, match="unknown keys.*channel"):
        WiringPlan.load(write_file(tmp_path, left_extra="  channel: {from: [0, 0], to: [5, 5]}\n"))


def test_the_checked_in_file_has_no_names_in_it():  # R-36
    data = read_file(WIRING_FILE)
    for side in data["sides"].values():
        for layer in LAYERS:
            for paths in side[layer].values():
                assert all(len(v) in (2, 3) and all(isinstance(c, float) for c in v) for path in paths for v in path)


def test_the_named_points_follow_the_layout_of_each_half(half):  # R-36
    points = half.anchors()
    for name in half.plate.names:
        assert {name, f"{name}.p1", f"{name}.p2", f"{name}.post", f"{name}.cathode"} <= set(points)
    assert {"xiao", "power.pin1", "power.pin2", "channel.from", "channel.to", "channel.mid"} <= set(points)
    assert np.allclose(points["channel.from"].point, half.plan.channel.min(axis=0))
    assert np.allclose(points["matrix_pinky_top.p1"].point, half.plate.pin("matrix_pinky_top", half.plate.switch.posts.p1))


def test_a_vertex_without_a_radius_gets_the_largest_arc_that_fits():  # R-39
    vertices = normalize([[0, 0], [10, 0], [10, 10]])
    assert vertices[0][2] == 0 and vertices[-1][2] == 0
    assert vertices[1][2] == pytest.approx(1.5)
    assert normalize([[0, 0], [1, 0], [1, 1]])[1][2] == pytest.approx(0.5)
    assert normalize([[0, 0], [1, 0], [2, 0]])[1][2] == 0
    assert normalize([[0, 0, 0], [10, 0, 2.5], [10, 10, 0]])[1][2] == 2.5
    assert tangent_overlaps(normalize([[0, 0], [1, 0], [1, 1], [2, 1]])) == []
    assert tangent_overlaps([(0, 0, 0), (1, 0, 1.5), (1, 1, 1.5), (2, 1, 0)]) != []


@pytest.mark.integration
def test_the_keyplate_has_a_pocket_a_trench_and_the_channel_where_the_file_says(full, plan):  # R-37, R-39, R-42
    dims = full.ctx.dims
    depth, floor = dims.print_profile.trench_depth, -dims.keyplate_z
    offset = dims.right_side_offset
    for built, side in ((full.left, "left"), (full.right, "right")):
        def world(x, y):
            return x if side == "left" else offset - x, y

        plate = Plate(full.ctx, plan.diode, "left")
        side_plan = plan.side(side)
        # the middle of a long stretch of wire over solid plate is empty from the underside up to the trench depth
        longest = max((path for paths in side_plan.underside.values() for path in paths), key=lambda p: len(sample(p)))
        points = sample(longest)
        solid = [p for p in points if not any(inside(p, c) for c in plate.cutouts.values()) and not inside(p, plate.xiao_pocket)
                 and not inside(p, side_plan.channel)]
        x, y = solid[len(solid) // 2]
        wx, wy = world(x, y)
        assert not built.keyplate.is_inside(Vector(wx, wy, floor + depth / 2))
        assert built.keyplate.is_inside(Vector(wx, wy, floor + depth + 0.3))
        # the channel is empty in the same way, between the columns where no cutout reaches it
        x, y = 62.0, float(side_plan.channel[:, 1].mean())
        assert not any(inside((x, y), c) for c in plate.cutouts.values())
        wx, wy = world(x, y)
        assert not built.keyplate.is_inside(Vector(wx, wy, floor + depth / 2))
        assert built.keyplate.is_inside(Vector(wx, wy, floor + depth + 0.3))
        # the pocket of a key reaches into the keyplate and into the bottom plate
        name, (pocket_side, pocket_y) = next(iter(side_plan.notches.items()))
        notch = plate.notch_at(name, pocket_side, pocket_y)
        wx, wy = world(*notch.center)
        assert not built.keyplate.is_inside(Vector(wx, wy, floor + 0.3))
        assert not built.bottom.is_inside(Vector(wx, wy, floor - 0.3))
        assert built.bottom.is_inside(Vector(wx, wy, floor - dims.bottom_plate_z + 0.3))


@pytest.mark.integration
def test_the_top_face_has_a_trench_for_each_power_wire(full, plan):  # R-41
    depth = full.ctx.dims.print_profile.trench_depth
    for built, side in ((full.left, "left"), (full.right, "right")):
        for paths in plan.side(side).top.values():
            (x0, y0, _), (x1, y1, _) = paths[0][0], paths[0][-1]
            x, y = (x0 + x1) / 2, (y0 + y1) / 2
            wx = x if side == "left" else full.ctx.dims.right_side_offset - x
            assert not built.keyplate.is_inside(Vector(wx, y, -depth / 2))
            assert built.keyplate.is_inside(Vector(wx, y, -depth - 0.3))
