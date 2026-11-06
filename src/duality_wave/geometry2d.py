"""2D helpers on top of build123d. All faces lie in the XY plane."""

from build123d import Face, Shape, Sketch, Compound
from OCP.BRepOffsetAPI import BRepOffsetAPI_MakeOffset
from OCP.GeomAbs import GeomAbs_Arc, GeomAbs_Intersection
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain


def merge_aligned_edges(sketch: Sketch, tolerance: float = 1e-6) -> Sketch:
    """Merge edges that lie on one line.

    ergogen rounds the points to 8 digits, so two rectangles in a row are off by about 1e-8.
    clean() keeps their edges apart. Later steps, like the acute-angle fillets of the outline, then act on another corner.
    """
    unifier = ShapeUpgrade_UnifySameDomain(sketch.wrapped, True, True, True)
    unifier.AllowInternalEdges(False)
    unifier.SetLinearTolerance(tolerance)
    unifier.SetAngularTolerance(tolerance)
    unifier.Build()
    return Sketch(Compound(unifier.Shape()))


def grow(face: Face, amount: float, sharp: bool = False) -> Face:
    """Offset a face outward (positive) or inward (negative).

    Convex corners are round by default. With sharp=True they keep straight, mitred edges.
    Holes of the face are ignored. When the offset splits the shape, the region with the largest area is kept.
    """
    builder = BRepOffsetAPI_MakeOffset()
    builder.Init(GeomAbs_Intersection if sharp else GeomAbs_Arc)
    builder.AddWire(face.outer_wire().wrapped)
    builder.Perform(amount)
    if not builder.IsDone():
        raise RuntimeError(f"2D offset failed with distance {amount}")
    wires = Shape.cast(builder.Shape()).wires()
    if not wires:
        raise RuntimeError(f"2D offset by {amount} removed the whole face")
    return max((Face(wire) for wire in wires), key=lambda f: f.area)


def round_convex(face: Face, radius: float) -> Face:
    """Round all convex corners with at least the given radius (morphological opening)."""
    return grow(grow(face, -radius), radius)
