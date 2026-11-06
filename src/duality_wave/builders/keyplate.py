import math

from build123d import *

from duality_wave.builders.common import CaseContext, circle_sketch, powerswitch_plane
from duality_wave.builders.viewer import NullScope
from duality_wave.models.features import switch_cutter, xiao_pocket_cutter
from duality_wave.models.keys import Point
from duality_wave.models.power_switch import PowerSwitch
from duality_wave.models.xiao import Xiao

CONNECTOR_WIDTH = 2


def build_keyplate(ctx: CaseContext, dbg=NullScope()) -> Part:
    print("Creating keyplate...")
    dims = ctx.dims
    with BuildPart() as keyplate:
        base = insert(ctx.outline.create_inner_outline(offset_by=-dims.wall_thickness - dims.print_profile.plate_clearance))
        extrude(amount=-dims.keyplate_z)
        dbg.note("base", base)

        # the face at z=0 is printed on the bed
        plate_faces = faces().filter_by(Axis.Z).sort_by(Axis.Z)
        chamfer(objects=plate_faces[0].edges(), length=dims.print_profile.plate_edge_chamfer)
        chamfer(objects=plate_faces[-1].edges(), length=dims.print_profile.plate_bed_chamfer)

        dbg.note("base edges", base.edges())

        _cut_fasteners(ctx, dbg)
        _cut_switches(ctx, dbg)
        _cut_xiao(ctx, dbg)
        _cut_connectors(ctx, dbg)
        _cut_powerswitch(ctx, dbg)

    return keyplate.part


def _cut_fasteners(ctx: CaseContext, dbg) -> None:
    print("  fastener holes...")
    fastener_holes = circle_sketch(ctx.dims.fastener_positions, ctx.screw.mount.clearance.radius)
    extrude(to_extrude=fastener_holes.sketch, amount=-ctx.dims.keyplate_z, mode=Mode.SUBTRACT)
    dbg.note("fastener holes", fastener_holes)


def _cut_switches(ctx: CaseContext, dbg) -> None:
    print("  key holes...")
    key_holes = switch_cutter(
        ctx.switch, ctx.dims.print_profile,
        [Location(key.p, (0, 0, key.r)) for key in ctx.keys.keys],
        plate_z=ctx.dims.below_z)
    dbg.note("key_holes", key_holes)
    insert(key_holes, mode=Mode.SUBTRACT)


def _cut_xiao(ctx: CaseContext, dbg) -> None:
    print("  xiao hole...")
    xiao_pocket = xiao_pocket_cutter(ctx.dims.print_profile, ctx.dims.xiao_position, plate_z=ctx.dims.below_z)
    dbg.note("xiao_pocket", xiao_pocket)
    insert(xiao_pocket, mode=Mode.SUBTRACT)


def _cut_connectors(ctx: CaseContext, dbg) -> None:
    """Channels on the underside of the plate that carry the wiring between the switches and to the XIAO."""
    print("  connector cut...")
    connector_sketch = _connector_sketch(ctx)
    extrude(to_extrude=connector_sketch.sketch, amount=ctx.dims.keyplate_z - ctx.switch.bottom_housing.d.Z, mode=Mode.SUBTRACT)
    dbg.note("connector_sketch", connector_sketch)


def _connector_sketch(ctx: CaseContext) -> BuildSketch:
    dims = ctx.dims
    keys = ctx.keys
    post_offset = (ctx.switch.posts.p2.d.X, -ctx.switch.posts.p2.d.Y)

    with BuildSketch(Plane.XY.offset(-dims.keyplate_z)) as connector_sketch:
        for cluster in keys.clusters:
            for keycol in cluster:
                pts = [key.p + post_offset for key in keycol]
                if len(pts) < 2:
                    continue
                with BuildLine() as col_line:
                    Polyline(*pts)
                    offset(amount=CONNECTOR_WIDTH, side=Side.BOTH)
                make_face()

            max_rows = max(len(col) for col in cluster)
            for row_idx in range(max_rows):
                # For this row, collect the appropriate position from each column
                pts = []
                for col in cluster:
                    if len(col) > row_idx:
                        pts.append(col[row_idx])
                    elif len(col) > 0:  # fall back to the "lower" row if not enough points
                        pts.append(col[-1])
                    # else: skip empty column (no point to connect)
                pts = [key.p + post_offset for key in pts]
                if len(pts) < 2:
                    continue
                with BuildLine() as row_line:
                    Polyline(*pts)
                    offset(amount=CONNECTOR_WIDTH, side=Side.BOTH)
                make_face()

        # find closest points between clusters and connect them
        for i in range(len(keys.clusters) - 1):
            cluster_a = [key for col in keys.clusters[i] for key in col]
            cluster_b = [key for col in keys.clusters[i + 1] for key in col]
            with BuildLine():
                Line(_closest_pair(cluster_a, cluster_b))
                offset(amount=CONNECTOR_WIDTH, side=Side.BOTH)
            make_face()

        top_pinkie = keys.finger_clusters[0][0][len(keys.finger_clusters[0][0]) - 1].p
        with BuildLine():
            Line(top_pinkie, (dims.xiao_position.X - Xiao.dims.d.X / 4, dims.xiao_position.Y, top_pinkie.Z))
            offset(amount=CONNECTOR_WIDTH, side=Side.BOTH)
        make_face()
    return connector_sketch


def _closest_pair(keys_a: list[Point | Vector], keys_b: list[Point | Vector]) -> tuple[Vector, Vector]:
    min_distance = math.inf
    closest_a = None
    closest_b = None
    for a in keys_a:
        for b in keys_b:
            a_pos = a.p if isinstance(a, Point) else a
            b_pos = b.p if isinstance(b, Point) else b
            dist = (a_pos - b_pos).length
            if dist < min_distance:
                min_distance = dist
                closest_a = a_pos
                closest_b = b_pos
    return closest_a, closest_b


def _cut_powerswitch(ctx: CaseContext, dbg) -> None:
    print("  powerswitch...")
    dims = ctx.dims
    with BuildSketch(powerswitch_plane(dims)) as powerswitch_cut:
        Rectangle(PowerSwitch.dims.d.X + 2 * dims.clearance, PowerSwitch.dims.d.Y + 2 * dims.clearance)
        pin_clearance_y = PowerSwitch.dims.d.Y + PowerSwitch.dims.pin_length + 10
        with Locations((0, pin_clearance_y / 2)):
            Rectangle(PowerSwitch.dims.d.X - 3, pin_clearance_y)
    extrude(to_extrude=powerswitch_cut.sketch, amount=-PowerSwitch.dims.d.Z, mode=Mode.SUBTRACT)
    dbg.note("powerswitch_cut", powerswitch_cut)
