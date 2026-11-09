from build123d import *
from build123d import Shape

from duality_wave.builders.common import CaseContext, circle_sketch, powerswitch_plane
from duality_wave.builders.viewer import NullScope
from duality_wave.models.power_switch import PowerSwitch
from duality_wave.models.switch import Switch
from duality_wave.models.xiao import Xiao


# the XIAO processor pocket is this much larger than the processor, the board cutout this much smaller than the board
XIAO_PROCESSOR_SLACK = 0.5
XIAO_BOARD_INSET = 0.5


def build_bottom(ctx: CaseContext, dbg=NullScope()) -> Part:
    print("Creating bottom...")
    dims = ctx.dims
    with BuildPart() as bottom:
        outline = ctx.outline.create_inner_outline(offset_by=-dims.wall_thickness - dims.print_profile.plate_clearance)

        with BuildSketch(Plane.XY.offset(-dims.below_z)) as base:
            insert(outline)
        extrude(amount=dims.bottom_plate_z)
        # the outer face at -below_z is printed on the bed
        plate_faces = faces().filter_by(Axis.Z).sort_by(Axis.Z)
        chamfer(objects=plate_faces[0].edges(), length=dims.print_profile.plate_bed_chamfer)
        chamfer(objects=plate_faces[-1].edges(), length=dims.print_profile.plate_edge_chamfer)

        _cut_fasteners(ctx, dbg)
        _cut_xiao_support(ctx, dbg)
        _cut_bumpers(ctx)
        _cut_powerswitch(ctx, dbg)

    return bottom.part


def _cut_fasteners(ctx: CaseContext, dbg) -> None:
    print("  fastener holes...")
    dims = ctx.dims
    profile = dims.print_profile
    bottom_plane = Plane.XY.offset(-dims.below_z)
    hole_radius = ctx.screw.dims.shaft.radius + profile.screw_clearance
    fastener_holes = circle_sketch(dims.fastener_positions, hole_radius, bottom_plane)
    extrude(to_extrude=fastener_holes.sketch, amount=dims.bottom_plate_z, mode=Mode.SUBTRACT)
    dbg.note("fastener holes", fastener_holes)

    recess_radius = ctx.screw.dims.head.radius + profile.screw_head_clearance
    head_recesses = circle_sketch(dims.fastener_positions, recess_radius, bottom_plane)
    extrude(to_extrude=head_recesses.sketch, amount=ctx.screw.dims.head.Z, mode=Mode.SUBTRACT)
    dbg.note("head recesses", head_recesses)


def _cut_xiao_support(ctx: CaseContext, dbg) -> None:
    print("  xiao support...")
    dims = ctx.dims
    with BuildSketch(Plane.XY.offset(dims.xiao_position.Z)) as xiao_support:
        with Locations((dims.xiao_position.X, dims.xiao_position.Y - Xiao.processor.forward_y)):
            Rectangle(Xiao.processor.d.X + XIAO_PROCESSOR_SLACK, Xiao.processor.d.Y + XIAO_PROCESSOR_SLACK)
    extrude(to_extrude=xiao_support.sketch, amount=-(Xiao.dims.d.Z + Xiao.processor.d.Z + dims.clearance), mode=Mode.SUBTRACT)
    dbg.note("xiao support", xiao_support)
    with BuildSketch(Plane.XY.offset(dims.xiao_position.Z)) as xiao_cutout:
        with Locations((dims.xiao_position.X, dims.xiao_position.Y - Xiao.processor.forward_y)):
            Rectangle(Xiao.dims.d.X - XIAO_BOARD_INSET, Xiao.dims.d.Y - Xiao.processor.forward_y * 2 + 4)
    extrude(to_extrude=xiao_cutout.sketch, amount=-(Xiao.dims.d.Z + Xiao.processor.d.Z / 2), mode=Mode.SUBTRACT)
    dbg.note("xiao xiao_cutout", xiao_cutout)


def _cut_bumpers(ctx: CaseContext) -> None:
    print("  bumper cutouts...")
    bumper_cutouts = circle_sketch(ctx.dims.bumper_locations, ctx.bumper.dims.radius + ctx.dims.print_profile.bumper_clearance, Plane.XY.offset(-ctx.dims.below_z))
    bumper_cutout_z = ctx.dims.print_profile.snap_down(ctx.bumper.dims.base_z)
    extrude(to_extrude=bumper_cutouts.sketch, amount=bumper_cutout_z, mode=Mode.SUBTRACT)


def _cut_powerswitch(ctx: CaseContext, dbg) -> None:
    dims = ctx.dims
    with BuildSketch(powerswitch_plane(dims)) as powerswitch_cut:
        with Locations((0, PowerSwitch.dims.pin_length / 2)):
            Rectangle(PowerSwitch.dims.d.X + 1, PowerSwitch.dims.d.Y + 1 + PowerSwitch.dims.pin_length)
    extrude(to_extrude=powerswitch_cut.sketch, amount=-10, mode=Mode.SUBTRACT)

    with BuildSketch(powerswitch_plane(dims)) as powerswitch_lever_sketch:
        with Locations(-PowerSwitch.lever.p):
            RectangleRounded(PowerSwitch.lever.clearance + 0.5, PowerSwitch.lever.d.Y + 0.5, radius=0.5)
    powerswitch_lever_cut = extrude(to_extrude=powerswitch_lever_sketch.sketch, amount=dims.powerswitch_position.Z + dims.below_z, mode=Mode.SUBTRACT)
    dbg.note("powerswitch_lever_cut", powerswitch_lever_cut)
    chamfer(powerswitch_lever_cut.edges().group_by(Axis.Z)[0], length=1.5, length2=0.5)


def switch_post_cutter(switch: Switch, keyplate_z: float, placements: list[Location], post_clearance: float) -> Part:
    """Room for the posts of every placed switch in the bottom plate, plus the terminal channel.

    Each post gets a hole from the top of the plate down to its tip. A post that reaches below the plate gets a through hole.
    The hole is larger than the post by post_clearance on every side.
    """
    housing_z = switch.bottom_housing.d.Z
    top = Plane.XY.offset(-keyplate_z)
    with BuildPart() as cutter:
        for length in sorted({post.d.Z for post in switch.posts.posts}):
            depth = housing_z + length - keyplate_z
            if depth <= 0:
                continue
            with BuildSketch(top):
                with Locations(placements):
                    for post in switch.posts.posts:
                        if post.d.Z == length:
                            # The underside workplane flips local Y, not the physical footprint's X.
                            with Locations((post.p.X, -post.p.Y)):
                                Circle(post.d.radius + post_clearance)
            extrude(amount=-depth)
    return cutter.part


def add_switch_post_cutouts(
    bottom: Shape, switch: Switch, keyplate_z: float, placements: list[Location], post_clearance: float
) -> Part:
    print("  switch post cutouts...")
    return bottom.cut(switch_post_cutter(switch, keyplate_z, placements, post_clearance))
