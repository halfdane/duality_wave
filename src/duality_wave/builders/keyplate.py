
from build123d import *

from duality_wave.builders.common import CaseContext, circle_sketch, powerswitch_plane
from duality_wave.builders.viewer import NullScope
from duality_wave.models.features import switch_cutter, xiao_pocket_cutter
from duality_wave.models.power_switch import PowerSwitch, keyplate_cut

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

        _cut_fasteners(ctx, dbg)
        _cut_switches(ctx, dbg)
        _cut_xiao(ctx, dbg)
        _cut_powerswitch(ctx, dbg)

    return keyplate.part


def _cut_fasteners(ctx: CaseContext, dbg) -> None:
    if not ctx.dims.fastener_positions:
        return
    print("  fastener holes...")
    hole_radius = ctx.screw.dims.shaft.radius + ctx.dims.print_profile.screw_clearance
    fastener_holes = circle_sketch(ctx.dims.fastener_positions, hole_radius)
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

def _cut_powerswitch(ctx: CaseContext, dbg) -> None:
    print("  powerswitch...")
    dims = ctx.dims
    body, pins = keyplate_cut(dims.clearance)
    with BuildSketch(powerswitch_plane(dims)) as powerswitch_cut:
        for x, y, width, height in (body, pins):
            with Locations((x, y)):
                Rectangle(width, height)
    extrude(to_extrude=powerswitch_cut.sketch, amount=-PowerSwitch.dims.d.Z, mode=Mode.SUBTRACT)
    dbg.note("powerswitch_cut", powerswitch_cut)
