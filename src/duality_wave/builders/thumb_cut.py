import math
from dataclasses import dataclass

from build123d import *

from duality_wave.builders.viewer import NullScope
from duality_wave.geometry2d import bridge_gaps, close_concave, grow, rect_face, round_convex, union_faces
from duality_wave.models.keys import Point
from duality_wave.models.switch import Switch


@dataclass(frozen=True)
class ThumbCutSpec:
    """Shape of the sculpted slope that lowers the keywell around the thumb keys.

    The floor of the cut is one zone in plan view. The slope grows that zone evenly by taper
    while it rises to the top of the keywell, so it leaves the floor and meets the top tangentially.
    inset_* pulls the floor edge back towards the keys at the inner (-x) and the outer (+y) end.
    corner_radius rounds the corners of the zone in plan view. The slope is lofted through the given number of layers.
    bridge_gap closes a gap between two keys' zones that is narrower than this, the same way the keywell cutout does.
    A wider gap leaves the thumb cluster in more than one zone, which is a usage error.
    rim_chamfer is the chamfer on the outer edges of the keywell. 0 leaves them sharp. About 1 mm is the most that fits.
    """

    taper: float = 15
    inset_inner: float = 11
    inset_outer: float = 1
    corner_radius: float = 2
    layers: int = 16
    bridge_gap: float = 4.4
    rim_chamfer: float = 0.8


def thumb_floor_z(switch: Switch) -> float:
    """The thumb floor is the top of the switch housing. The caps float above it."""
    return switch.base.d.Z + switch.upper_housing.d.Z


def thumb_depth(switch: Switch, top_z: float) -> float:
    """How far the thumb floor sits below the top of the keywell."""
    return top_z - thumb_floor_z(switch)


def thumb_zone(switch: Switch, thumb_clusters: list[list[list[Point]]], spec: ThumbCutSpec = ThumbCutSpec()) -> Face:
    """The floor of the thumb cut in plan view, at z = 0.

    Every key contributes a rectangle set back behind it, in its own rotated frame. The later taper growth
    of thumb_cutter closes the remaining distance to the key. Keys that already touch fuse exactly, with
    no rounding. Zones closer than bridge_gap but not touching fuse the same way the keywell cutout closes
    a gap between key cells, which can round the corner where the bridge meets a zone.
    """
    raw_faces: list[Face] = []
    for thumb_cluster in thumb_clusters:
        for column_index, column in enumerate(thumb_cluster):
            for key_index, key in enumerate(column):
                x = switch.above.d.X * 1.5
                y = switch.above.d.Y * 0.75
                center = key.p + Vector(0, -y).rotate(Axis.Z, key.r)

                if key_index == 0 and column_index == 0:
                    # this is the innermost key - start the cut further to the right
                    center += Vector(switch.above.d.X / 3, 0, 0).rotate(Axis.Z, key.r)

                if key_index == 0:
                    # this is the first key in the column - make the cut taller
                    center += Vector(0, -5, 0).rotate(Axis.Z, key.r)
                    y += 10

                # only two edges of the zone matter: the inner end (-x) and the outer end (+y).
                # the other two edges lie outside the case.
                left = -spec.inset_inner if column_index == 0 else 0
                back = -spec.inset_outer if key_index == len(column) - 1 else 0
                center += Vector(-left / 2, back / 2, 0).rotate(Axis.Z, key.r)
                raw_faces.append(rect_face(center, x + left, y + back, key.r))

    faces = union_faces(raw_faces)
    if len(faces) != 1:
        faces = bridge_gaps(raw_faces, spec.bridge_gap)
    if len(faces) != 1:
        raise ValueError(f"The thumb keys give {len(faces)} zones more than {spec.bridge_gap} mm apart. They must form one region.")
    (result,) = round_convex(faces[0], spec.corner_radius)
    return result


def thumb_cutter(
    switch: Switch,
    thumb_clusters: list[list[list[Point]]],
    top_z: float,
    spec: ThumbCutSpec = ThumbCutSpec(),
    dbg=NullScope(),
) -> Solid:
    """Cutter that spans from the thumb floor up to top_z and widens towards the top.

    The loft needs sections with the same number of edges. Growing the zone towards the full taper would
    smooth away its concave notches gradually, changing a section's edge count partway through the loft
    and leaving OCC to stitch together sections it cannot reconcile, which fragments the lofted wall.
    Smoothing those notches by the full taper up front keeps every section at the same topology as the
    fully grown one, so the taper only changes its size, never its shape. Below 1 mm, the growth itself
    cannot meaningfully change the topology either, and the smoothing only adds numerical noise.
    """
    floor_z = thumb_floor_z(switch)
    depth = thumb_depth(switch, top_z)
    zone = thumb_zone(switch, thumb_clusters, spec)
    dbg.note("zone", zone)
    if spec.taper > 1:
        (section_zone,) = close_concave(zone, spec.taper * 1.001)
    else:
        section_zone = zone

    # The slope grows evenly with the layer number while the height follows a cosine ease.
    wires = []
    for layer in range(spec.layers + 1):
        progress = layer / spec.layers
        eased = 0.5 - 0.5 * math.cos(math.pi * progress)
        section = grow(section_zone, spec.taper * progress) if layer else section_zone
        wires.append(section.outer_wire().moved(Location((0, 0, floor_z + depth * eased))))
    return Solid.make_loft(wires, ruled=False)


def chamfer_rim(keywell: BuildPart, outline: Sketch | Face, length: float) -> None:
    """Chamfer the edges along the outer wall after the thumb cut. Call inside the keywell's BuildPart.

    The vertical edges stay as they are. They join walls that are tangent to each other.
    """
    if length <= 0:
        return
    outer = outline.faces()[0].outer_wire()

    def on_wall(edge: Edge) -> bool:
        points = (edge.position_at(u) for u in (0, 0.25, 0.5, 0.75, 1))
        return all(outer.distance_to(Vertex(p.X, p.Y, 0)) < 1e-4 for p in points)

    def vertical(edge: Edge) -> bool:
        start, end = edge.position_at(0), edge.position_at(1)
        return abs(start.X - end.X) < 1e-4 and abs(start.Y - end.Y) < 1e-4

    chamfer([edge for edge in keywell.edges() if on_wall(edge) and not vertical(edge)], length=length)
