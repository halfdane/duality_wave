"""Emblems on the two faces that lie on the print bed: the symbol on the top of the keywell, the invader under the bottom plate.

An emblem is a thin solid that lies inside its part and ends flush with the bed face. The part has no pocket for it.
The slicer prints the overlap in the colour of the emblem, if the emblem comes after the part.
"""
from build123d import Compound, Location, Pos, Solid, Sketch, Vector

from duality_wave.builders.common import CaseContext
from duality_wave.models.space_invader import SpaceInvader
from duality_wave.models.symbol import Symbol


def inlay(sketch: Sketch, location: Location, face_z: float, depth: float) -> Compound:
    """The sketch placed at location and extruded from the plane z = face_z by depth. A negative depth goes down."""
    placed = sketch.moved(location).moved(Pos(0, 0, face_z))
    return Compound([Solid.extrude(face, Vector(0, 0, depth)) for face in placed.faces()])


def face_emblems(ctx: CaseContext) -> dict[str, Compound]:
    """The emblems of the left half by the name of the part they belong to, in the assembled frame."""
    dims, profile = ctx.dims, ctx.dims.print_profile
    depth = profile.emblem_depth
    symbol = Symbol(total_height=profile.symbol_height).sketch
    invader = SpaceInvader(pitch=profile.invader_height / SpaceInvader.rows, gap=0).sketch
    return {
        "keywell": inlay(symbol, dims.symbol_location, dims.above_z, -depth),
        "bottom": inlay(invader, dims.invader_location, -dims.below_z, depth),
    }
