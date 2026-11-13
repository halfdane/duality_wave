"""2D helpers on top of build123d. All faces lie in the XY plane."""

from collections.abc import Iterable, Sequence

from build123d import Axis, Compound, Face, Location, Plane, Shape, Sketch, Vector, VectorLike, Wire
from OCP.BRepOffsetAPI import BRepOffsetAPI_MakeOffset
from OCP.GeomAbs import GeomAbs_Arc, GeomAbs_Intersection
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain


def merge_aligned_edges(sketch: Sketch, tolerance: float = 1e-6) -> Sketch:
    """Merge edges that lie on one line.

    ergogen rounds the points to 8 digits, so two rectangles in a row are off by about 1e-8.
    clean() keeps their edges apart. A later step, like the rounding of a corner, then acts on another corner.
    """
    unifier = ShapeUpgrade_UnifySameDomain(sketch.wrapped, True, True, True)
    unifier.AllowInternalEdges(False)
    unifier.SetLinearTolerance(tolerance)
    unifier.SetAngularTolerance(tolerance)
    unifier.Build()
    return Sketch(Compound(unifier.Shape()))


def upward(face: Face) -> Face:
    """Turn a face that looks down (clockwise wire) to look up. Faces that look the other way do not fuse and extrude downwards."""
    return face if face.normal_at().Z > 0 else -face


def _offset_wire(face: Face, amount: float, join) -> BRepOffsetAPI_MakeOffset:
    builder = BRepOffsetAPI_MakeOffset()
    builder.Init(join)
    builder.AddWire(face.outer_wire().wrapped)
    builder.Perform(amount)
    return builder


def _grow_pieces(face: Face, amount: float, sharp: bool) -> list[Face]:
    """The pieces of an outward (positive) or inward (negative) offset. Usually one, more if the offset splits the face.

    A mitred offset can fail outright when it shrinks a concave corner tighter than its local reach allows.
    When that happens, this falls back to a rounded corner there instead of raising.
    """
    builder = _offset_wire(face, amount, GeomAbs_Intersection if sharp else GeomAbs_Arc)
    if not builder.IsDone() and sharp:
        builder = _offset_wire(face, amount, GeomAbs_Arc)
    if not builder.IsDone():
        raise RuntimeError(f"2D offset failed with distance {amount}")
    wires = Shape.cast(builder.Shape()).wires()
    if not wires:
        raise RuntimeError(f"2D offset by {amount} removed the whole face")
    return [upward(Face(wire)) for wire in wires]


def grow(face: Face, amount: float, sharp: bool = False) -> Face:
    """Offset a face outward (positive) or inward (negative).

    Convex corners are round by default. With sharp=True they keep straight, mitred edges.
    Holes of the face are ignored. When the offset splits the shape, the region with the largest area is kept.
    """
    return max(_grow_pieces(face, amount, sharp), key=lambda f: f.area)


def round_convex(face: Face, radius: float) -> list[Face]:
    """Round all convex corners with at least the given radius (morphological opening).

    Erosion can sever a part that is attached through a neck narrower than radius. Every piece
    erosion leaves grows back independently and the result is re-fused, so a thinly-attached
    piece never disappears - it just keeps its thin neck instead of being rounded away there.
    """
    if radius <= 0:
        return [face]
    eroded = _grow_pieces(face, -radius, sharp=False)
    return union_faces([grow(piece, radius) for piece in eroded])


def close_concave(face: Face, radius: float) -> list[Face]:
    """Round all concave corners with at least the given radius (morphological closing).

    A concave region that a disc of this radius cannot enter is filled. The fill follows an arc that touches both sides.
    The dilation first can only ever grow the face into fewer, bigger pieces, never split it. The erosion after can still
    sever a part that is attached through a neck narrower than radius; every piece that leaves is kept, see round_convex.
    """
    if radius <= 0:
        return [face]
    grown = grow(face, radius)
    return _grow_pieces(grown, -radius, sharp=False)


def rect_face(center: VectorLike, width: float, height: float, rotation: float = 0.0) -> Face:
    """Rectangle around the center, turned counter-clockwise by rotation degrees."""
    x, y = Vector(center).X, Vector(center).Y
    return Face.make_rect(width, height).rotate(Axis.Z, rotation).moved(Location((x, y, 0)))


def circle_face(center: VectorLike, radius: float) -> Face:
    return upward(Face(Wire.make_circle(radius, Plane((Vector(center).X, Vector(center).Y, 0)))))


def polygon_face(points: Iterable[VectorLike]) -> Face:
    return upward(Face(Wire.make_polygon([Vector(p) for p in points])))


def union_faces(faces: Sequence[Face]) -> list[Face]:
    """Fuse faces. The result has one face for every separate region.

    ergogen rounds the points to 8 digits, so edges that should be aligned are off by about 1e-8. The fuzzy fuse treats them as aligned.
    """
    fused = faces[0].fuse(*faces[1:], tol=1e-5) if len(faces) > 1 else faces[0]
    return [upward(face) for face in merge_aligned_edges(Sketch([fused])).faces()]


def bridge_gaps(faces: Sequence[Face], gap: float) -> list[Face]:
    """Fuse faces and close every gap that is narrower than gap. The edges of the bridge are straight.

    Each face grows by half the gap with mitred corners, the grown faces fuse, and the result shrinks again.
    Two faces that stay at least gap apart stay separate regions. The shrink can itself split a fused region
    back apart, for example when it only touched another through a corner; every piece from that is kept.
    """
    if gap <= 0:
        return union_faces(faces)
    half = gap / 2
    regions = union_faces([grow(face, half, sharp=True) for face in faces])
    return [piece for region in regions for piece in _grow_pieces(region, -half, sharp=True)]


def sketch_of(*faces: Face) -> Sketch:
    return Sketch([upward(face) for face in faces])


def overlap_area(a: Face, b: Face) -> float:
    """Area where two faces in the same plane overlap."""
    common = a.intersect(b)
    return sum(face.area for face in common.faces()) if common is not None else 0.0
