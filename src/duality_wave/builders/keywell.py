from build123d import *

from duality_wave.builders.common import CaseContext, circle_sketch
from duality_wave.builders.thumb_cut import ThumbCutSpec, chamfer_rim, thumb_cutter
from duality_wave.builders.viewer import NullScope
from duality_wave.models.features import magnet_recess_cutter


def build_keywell(ctx: CaseContext, dbg=NullScope(), thumb_spec: ThumbCutSpec = ThumbCutSpec()) -> Part:
    print("Creating keywell...")
    dims = ctx.dims
    with BuildPart() as keywell:
        with BuildSketch(Plane.XY.offset(dims.above_z)):
            insert(ctx.outline.sketch)
        extrude(amount=-dims.below_z - dims.above_z)

        print("  skulpting thumb cut...")
        insert(thumb_cutter(ctx.switch, ctx.keys.thumb_clusters, dims.above_z, thumb_spec, dbg.scope("thumb_cut")),
            mode=Mode.SUBTRACT)
        chamfer_rim(keywell, ctx.outline.sketch, thumb_spec.rim_chamfer)

        _cut_cavity(ctx)
        _cut_insert_pilots(ctx, dbg)
        _cut_fastener_holes(ctx, dbg)
        _cut_battery(ctx, dbg)
        _cut_magnets(ctx, dbg)

    return keywell.part


def _cut_cavity(ctx: CaseContext) -> None:
    print("  keywell cut...")
    dims = ctx.dims
    insert(ctx.outline.create_inner_outline(offset_by=-dims.wall_thickness))
    extrude(amount=-dims.below_z, mode=Mode.SUBTRACT)

    with BuildSketch(Plane.XY.offset(dims.above_z)) as key_cut_sketch:
        insert(ctx.outline.keywell_sketch)
    extrude(to_extrude=key_cut_sketch.sketch, amount=-dims.below_z - dims.above_z, mode=Mode.SUBTRACT)


def _cut_insert_pilots(ctx: CaseContext, dbg) -> None:
    if not ctx.dims.fastener_positions:
        return
    print("  heat-set insert pilots...")
    dims = ctx.dims
    insert_pilots = circle_sketch(dims.fastener_positions, dims.print_profile.insert_pilot_radius, Plane.XY.offset(dims.heat_insert_z))
    extrude(to_extrude=insert_pilots.sketch, amount=-20, mode=Mode.SUBTRACT)
    dbg.note("insert pilots", insert_pilots)


def _cut_fastener_holes(ctx: CaseContext, dbg) -> None:
    if not ctx.dims.fastener_positions:
        return
    print("  fastener holes...")
    dims = ctx.dims
    hole_radius = ctx.screw.dims.shaft.radius + dims.print_profile.screw_clearance
    fastener_holes = circle_sketch(dims.fastener_positions, hole_radius, Plane.XY.offset(-dims.below_z))
    extrude(to_extrude=fastener_holes.sketch, amount=ctx.screw.dims.shaft.Z + ctx.screw.dims.head.Z + 0.1, mode=Mode.SUBTRACT)
    dbg.note("fastener holes", fastener_holes)


def _cut_battery(ctx: CaseContext, dbg) -> None:
    print("  battery recess...")
    dims = ctx.dims
    battery_pd = dims.battery_pd
    clearance = dims.print_profile.battery_clearance
    with BuildSketch(Plane.XY.offset(battery_pd.p.Z + battery_pd.d.Z / 2 + clearance)) as battery_sketch:
        with Locations((battery_pd.p.X, battery_pd.p.Y)):
            Rectangle(battery_pd.d.X + 2 * clearance, battery_pd.d.Y + 2 * clearance)
    extrude(to_extrude=battery_sketch.sketch, amount=-battery_pd.d.Z - dims.wall_thickness, mode=Mode.SUBTRACT)
    dbg.note("battery_sketch", battery_sketch)


def _cut_magnets(ctx: CaseContext, dbg) -> None:
    dims = ctx.dims
    if not dims.magnet_positions:
        return
    print("  magnet pockets...")
    # the pockets open into the cavity at z=0 and stop under the skin
    magnet_recesses = magnet_recess_cutter(
        dims.magnet_d, dims.print_profile, dims.magnet_positions, top_z=0, depth=dims.magnet_z).mirror(Plane.XY)
    insert(magnet_recesses, mode=Mode.SUBTRACT)
    dbg.note("magnet_recesses", magnet_recesses)

