"""Cuts for the matrix wiring: the diode pockets, the trenches for the wires and the channel they end in.

The plan (duality_wave.wiring.plan) holds the numbers in the frame of the blank, so these cuts go in before the right half is mirrored.
The keyplate top face is at z = 0 and its underside at z = -keyplate_z. The bottom plate lies below it.
"""

from build123d import *

from duality_wave.builders.common import CaseContext
from duality_wave.models.diode import Diode, DiodeNotchSpec
from duality_wave.wiring.plan import Paths, SidePlan
from duality_wave.wiring.rounded import segments

# cutters reach this far past a face, so no cut ends in the plane of a face
OVERSHOOT = 0.1
# the pocket reaches this far into the cutout of its switch
POCKET_OVERLAP = 0.2


def notch_spec(ctx: CaseContext, diode: Diode) -> DiodeNotchSpec:
    dims = ctx.dims
    return DiodeNotchSpec.of(diode, dims.print_profile, dims.keyplate_z, dims.bottom_plate_z)


def cutout_half(ctx: CaseContext) -> float:
    return ctx.switch.below.d.X / 2 + ctx.dims.print_profile.switch_clearance + 0.5


def pocket_cutter(ctx: CaseContext, spec: DiodeNotchSpec, notches: dict[str, tuple[int, float]], z_from: float, z_to: float) -> Part:
    """Cutter for the diode pockets, from z_from (where the pocket opens) to z_to."""
    half = cutout_half(ctx)
    cutters = []
    for name, (side, y) in notches.items():
        x, py, width, length = spec.pocket(half, side, y, POCKET_OVERLAP)
        point = ctx.keys.points[name]
        placement = Location((point.p.X, point.p.Y, 0), (0, 0, point.r))
        with BuildPart() as cutter:
            with BuildSketch(Plane.XY.offset(z_from)):
                with Locations((x, py)):
                    Rectangle(width, length)
            extrude(amount=z_to - z_from)
        cutters.append(placement * cutter.part)
    return Part(Compound(cutters))


def trench_cutter(paths: Paths, width: float, z_from: float, z_to: float) -> Part:
    """Cutter for the trenches of the wires, from z_from to z_to. Lines and arcs make the path, an offset gives the width."""
    solids = []
    for net_paths in paths.values():
        for vertices in net_paths:
            with BuildLine() as line:
                for piece in segments(vertices):
                    if piece[0] == "line":
                        Line(tuple(piece[1]), tuple(piece[2]))
                    else:
                        ThreePointArc(tuple(piece[1]), tuple(piece[2]), tuple(piece[3]))
            outline = line.wire().offset_2d(width / 2, Kind.ARC)
            face = Face(outline[0] if isinstance(outline, list) else outline)
            solids.append(Solid.extrude(face.moved(Location((0, 0, z_from))), Vector(0, 0, z_to - z_from)))
    return Part(Compound(solids))


def channel_cutter(polygon, z_from: float, z_to: float) -> Part:
    """Cutter for the channel: the polygon from z_from to z_to."""
    face = Face(Wire.make_polygon([Vector(x, y, z_from) for x, y in polygon]))
    return Part(Compound([Solid.extrude(face, Vector(0, 0, z_to - z_from))]))


def cut_keyplate(ctx: CaseContext, keyplate: Part, plan: SidePlan, diode: Diode) -> Part:
    """Diode pockets, trenches and the channel in the underside, trenches in the top face."""
    dims = ctx.dims
    spec = notch_spec(ctx, diode)
    width, depth = dims.print_profile.trench_width, dims.print_profile.trench_depth
    floor = -dims.keyplate_z
    keyplate -= pocket_cutter(ctx, spec, plan.notches, floor - OVERSHOOT, floor + spec.keyplate_depth)
    keyplate -= trench_cutter(plan.underside, width, floor - OVERSHOOT, floor + depth)
    keyplate -= channel_cutter(plan.channel, floor - OVERSHOOT, floor + depth)
    keyplate -= trench_cutter(plan.top, width, OVERSHOOT, -depth)
    return keyplate


def cut_bottom(ctx: CaseContext, bottom: Part, plan: SidePlan, diode: Diode) -> Part:
    """Diode pockets in the top face of the bottom plate."""
    spec = notch_spec(ctx, diode)
    top = -ctx.dims.keyplate_z
    return bottom - pocket_cutter(ctx, spec, plan.notches, top + OVERSHOOT, top - spec.bottom_depth)
