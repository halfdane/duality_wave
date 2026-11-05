import math
from dataclasses import dataclass

from build123d import *

from duality_wave.builders.viewer import NullScope
from duality_wave.models.keys import Point
from duality_wave.models.switch import Switch


@dataclass(frozen=True)
class ThumbCutSpec:
    """Shape of the sculpted slope that lowers the keywell around the thumb keys.

    The top edge of each slope sits run_* beyond the original floor edge, away from the keys.
    inset_* pulls the floor edge back towards the keys, so the slope spreads in both directions.
    The slope is lofted through the given number of layers.
    """

    run_inner: float = 5
    run_outer: float = 15
    inset_inner: float = 7
    inset_outer: float = 3
    layers: int = 16


def thumb_depth(switch: Switch) -> float:
    """How far the thumb floor sits below the top of the keywell."""
    return switch.cap.d.Z + switch.stem.d.Z


def thumb_floor_z(switch: Switch, top_z: float) -> float:
    return top_z - thumb_depth(switch)


def thumb_cutter(
    switch: Switch,
    thumb_clusters: list[list[list[Point]]],
    top_z: float,
    spec: ThumbCutSpec = ThumbCutSpec(),
    dbg=NullScope(),
) -> Part:
    """Cutter that spans from the thumb floor up to top_z and widens towards the top."""
    depth = thumb_depth(switch)
    floor_z = thumb_floor_z(switch, top_z)

    def rectangles(inner_grow: float, outer_grow: float):
        for thumb_cluster in thumb_clusters:
            for column_index, column in enumerate(thumb_cluster):
                for key_index, key in enumerate(column):
                    x = switch.above.d.X * 1.5
                    y = switch.above.d.Y * 0.75
                    loc = Location(key.p + (0, -y), key.r)
                    if key_index == 0 and column_index == 0:
                        # this is the innermost key - start the cut further to the right
                        loc.position += Vector(switch.above.d.X / 3, 0, 0).rotate(Axis.Z, key.r)

                    if key_index == 0:
                        # this is the first key in the column - make the cut taller
                        loc.position += Vector(0, -5, 0).rotate(Axis.Z, key.r)
                        y += 10

                    # only two edges of the cut slope: the inner end (-x) and the outer end (+y).
                    # the other two edges lie outside the case.
                    left = inner_grow if column_index == 0 else 0
                    back = outer_grow if key_index == len(column) - 1 else 0
                    loc.position += Vector(-left / 2, back / 2, 0).rotate(Axis.Z, key.r)
                    with Locations(loc):
                        Rectangle(x + left, y + back)

    # Stack the cut in layers. The slope grows evenly with the layer number while the height
    # follows a cosine ease, so the slope leaves the floor and meets the top tangentially.
    with BuildPart() as cutter:
        for layer in range(spec.layers + 1):
            progress = layer / spec.layers
            eased = 0.5 - 0.5 * math.cos(math.pi * progress)
            with BuildSketch(Plane.XY.offset(floor_z + depth * eased)) as layer_sketch:
                rectangles(
                    -spec.inset_inner + (spec.run_inner + spec.inset_inner) * progress,
                    -spec.inset_outer + (spec.run_outer + spec.inset_outer) * progress)
            if layer == 0:
                dbg.note("sketch", layer_sketch)
        loft()
    return cutter.part


def fillet_thumb_edges(keywell: BuildPart, body: Part, floor_z: float, top_z: float, dbg=NullScope()) -> None:
    """Round the outside edges of the keywell after the thumb cut. Call inside the keywell's BuildPart.

    body is the keywell block before any cut. Its side faces tell which edges are on the outside.
    """

    def touching(faces_to_touch: ShapeList[Face]):
        return lambda a_face: len([f for f in faces_to_touch if f.intersect(a_face) is not None]) > 0

    # every face thats not top or bottom
    outside = [f for f in body.faces() if f not in body.faces().filter_by(Axis.Z)]

    def outside_edges() -> list[Edge]:
        faces = ShapeList(f for f in keywell.faces().filter_by(touching(outside)) if f not in keywell.faces().filter_by(Axis.Z))
        dbg.note("outside_faces", faces)
        return faces.edges()

    # where the slope blends into the top or the floor it is tangent already, so there is no crease to round
    def is_slope_silhouette(edge: Edge) -> bool:
        return edge.geom_type == GeomType.BSPLINE and floor_z + 0.4 < edge.center().Z < top_z - 0.4

    # the fillet the curved slope edges and the rest of the thumb cut
    slope_edge_positions = [e.center() for e in outside_edges() if is_slope_silhouette(e)]
    for position in slope_edge_positions:
        # earlier fillets can have rounded this edge already, or replaced it
        edge = next((e for e in outside_edges() if is_slope_silhouette(e) and (e.center() - position).length < 0.05), None)
        if edge is None:
            continue
        fillet(edge, radius=1.0)
    fillet([e for e in outside_edges() if e.geom_type != GeomType.BSPLINE], radius=1)
