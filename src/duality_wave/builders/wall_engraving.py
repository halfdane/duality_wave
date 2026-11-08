"""Emblems in the outer wall of the keywell.

The keywell prints upside down. A pocket in the top face or in the bed face of a part has no floor under it, and the
slicer bridges it with strings or fills it with support. A pocket in the outer wall is an ordinary notch of the perimeter.
Its roof slopes at 45 degrees, so every layer rests on the one before it.
"""
from dataclasses import dataclass

from build123d import *
from build123d import Shape

from duality_wave.models.print_profile import PrintProfile
from duality_wave.models.space_invader import SpaceInvader
from duality_wave.models.symbol import Symbol

# the cutter starts this far outside of the wall, so the cut does not end on the wall face
LEAD = 0.1
UP = Vector(0, 0, 1)


@dataclass(frozen=True)
class WallSpot:
    """The middle of a straight wall on its outer face (z = 0) and the direction that points out of the case."""

    origin: Vector
    outward: Vector

    def mirrored(self, offset: float) -> "WallSpot":
        """The spot of the right half. The right half is the left half mirrored about x = offset / 2."""
        return WallSpot(
            Vector(offset - self.origin.X, self.origin.Y, self.origin.Z),
            Vector(-self.outward.X, self.outward.Y, self.outward.Z))

    def plane(self, z: float) -> Plane:
        """Looking at the wall from outside: x runs to the right, y runs up, the normal points out of the case."""
        return Plane(
            origin=(self.origin.X, self.origin.Y, z),
            x_dir=UP.cross(self.outward),
            z_dir=self.outward)


def find_wall_spot(outline_sketch: Sketch) -> WallSpot:
    """The middle of the leftmost straight wall that faces to the front (-y).

    That is the wall of the lowest key of the pinky column, left of the trackpad notch.
    """
    face = outline_sketch.faces()[0]
    candidates = []
    for edge in face.outer_wire().edges():
        if edge.geom_type != GeomType.LINE:
            continue
        middle = edge.position_at(0.5)
        tangent = edge.tangent_at(0.5)
        outward = Vector(tangent.Y, -tangent.X, 0).normalized()
        if face.is_inside(middle + outward * 0.01):
            outward = -outward
        if outward.Y < -0.9:
            candidates.append(WallSpot(Vector(middle.X, middle.Y, 0), outward))
    if not candidates:
        raise ValueError("The outline has no straight wall that faces to the front.")
    return min(candidates, key=lambda spot: spot.origin.X)


def emblem_sketch(name: str, profile: PrintProfile) -> Sketch:
    """The emblem, centered on the origin and as high as the invader."""
    pitch = profile.snap_up(profile.engraving_pitch)
    if name == "invader":
        return SpaceInvader(pitch, profile.engraving_gap).sketch
    if name == "symbol":
        return Symbol(total_height=SpaceInvader.rows * pitch).sketch
    raise ValueError(f"Unknown emblem {name!r}")


def emblem_height(profile: PrintProfile) -> float:
    return SpaceInvader.rows * profile.snap_up(profile.engraving_pitch)


def emblem_z(dims) -> float:
    """The height of the emblem center. The rows start and end on layer boundaries, counted from the bed.

    The keywell prints upside down, so the bed is at above_z. dims.snap_z counts from -below_z, which is the same grid.
    """
    half = emblem_height(dims.print_profile) / 2
    middle = (dims.above_z - dims.below_z) / 2
    return round(dims.snap_z(middle + half) - half, 6)


def engrave_wall(part: Shape, plane: Plane, emblem: Sketch, depth: float, roof_slope: bool = True) -> Shape:
    """Cut the emblem into the wall to depth. The sketch lies in the XY plane and moves onto the plane.

    The part prints with its +z side up. The roof of a pocket is the side that prints last. For the keywell
    that is the low side, so the roof of a pixel rises from its mouth to its back. The pocket is the straight
    prism cut by a prism that leans up by one unit for each unit of depth.
    """
    out, inward = plane.z_dir, -plane.z_dir
    cutters = []
    for face in emblem.moved(plane.location).faces():
        start = face.moved(Location(out * LEAD))
        straight = Solid.extrude(start, inward * (depth + LEAD))
        if roof_slope:
            lean = (inward + UP) * (depth + LEAD)
            leaning = Solid.extrude(start.moved(Location(UP * -LEAD)), lean)
            cutters.extend(solid for piece in straight.intersect(leaning) for solid in piece.solids())
        else:
            cutters.append(straight)
    return part.cut(Compound(cutters))


def engrave_emblem(part: Shape, dims, spot: WallSpot, name: str) -> Shape:
    profile = dims.print_profile
    plane = spot.plane(emblem_z(dims))
    return engrave_wall(part, plane, emblem_sketch(name, profile), profile.engraving_depth, profile.engraving_roof_slope)
