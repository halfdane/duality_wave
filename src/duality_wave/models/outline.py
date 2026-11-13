from dataclasses import dataclass

from build123d import *

from duality_wave.geometry2d import (
    bridge_gaps, circle_face, close_concave, grow, overlap_area, polygon_face, rect_face, round_convex, sketch_of, union_faces)
from duality_wave.layout import get_points
from duality_wave.models.keys import ErgoKeys
from duality_wave.models.switch import Switch


@dataclass(frozen=True)
class OutlineSpec:
    """Rounding and bridging of the outlines. All lengths are in mm.

    corner_radius rounds the corners of the outer outline, convex and concave.
    sweep_ratio times the height of the right wall above the thumb cluster is the radius of a disc that rolls along the right wall and the thumb cluster.
    The disc fills the corner between them with an arc. The height runs from the top of the outline to the top corner of the thumb cluster.
    bridge_gap closes the gaps between key cells that are narrower than this. The edges of the bridge are straight.
    cutout_concave_radius rounds the inner corners of the keywell cutout, where the wall pokes into the cutout.
    cutout_convex_radius rounds the outer corners of the cutout.
    """

    corner_radius: float = 5.0
    sweep_ratio: float = 0.5
    bridge_gap: float = 4.4
    cutout_concave_radius: float = 1
    cutout_convex_radius: float = 1


class Outline:
    def __init__(self, switch: Switch, keys: ErgoKeys, wall_thickness=1.8, additional_top_space=10, spec: OutlineSpec = OutlineSpec()):
        self.switch = switch
        self.keys = keys
        self.spec = spec

        self.wall_thickness = wall_thickness

        self.cirque_recess_radius = 22
        self.cirque_recess_position = Vector(30, -24)
        self.has_cirque_notch = False

        self.d_x = switch.cap.d.X / 2 + 2*wall_thickness
        self.d_y = switch.cap.d.Y / 2 + 2*wall_thickness

        self._raw_keywell = self._create_keywell_outline()

        finger_corners = [v for key in keys.finger_keys for v in self._cell(key, 1.5).vertices()]
        self.left = min(v.X for v in finger_corners) - wall_thickness
        self.right = max(v.X for v in finger_corners) + wall_thickness
        self.bottom = min(v.Y for v in finger_corners) - wall_thickness
        self.top = max(v.Y for v in finger_corners) + wall_thickness + additional_top_space

        self.bottom_left = Vector(self.left, self.bottom)
        self.top_left = Vector(self.left, self.top)
        self.top_right = Vector(self.right, self.top)

        first_thumb = keys.thumb_clusters[0][0][0]
        last_column = keys.thumb_clusters[0][-1]
        self.thumb_bottom_left = first_thumb.p + Vector(-self.d_x + self.wall_thickness, -self.d_y + 1).rotate(Axis.Z, first_thumb.r)
        self.thumb_top = last_column[-1].p + Vector(self.d_x, self.d_y).rotate(Axis.Z, last_column[-1].r)
        self.sweep_radius = spec.sweep_ratio * (self.top - self.thumb_top.Y)

        self._outer_face = self._create_outer_face()
        self.sketch = sketch_of(self._outer_face)
        self._inner_sketches: dict[float, Sketch] = {}
        self.inner_sketch = self.create_inner_outline(-self.wall_thickness)
        self.keywell_sketch = self._clip_to_cavity(self._raw_keywell)

    def _cell(self, key, scale: float) -> Face:
        return rect_face(key.p, self.d_x * scale, self.d_y * scale, key.r)

    def _create_keywell_outline(self) -> Sketch:
        """The cutout for the keys, before it is clipped to the cavity."""
        # the cells are 1.5 times the key dimensions, so there is no interference with the keycaps
        cells = [self._cell(key, 1.5) for key in self.keys.keys]
        regions = bridge_gaps(cells, self.spec.bridge_gap)
        finished = [
            rounded
            for region in regions
            for closed in close_concave(region, self.spec.cutout_concave_radius)
            for rounded in round_convex(closed, self.spec.cutout_convex_radius)]
        return sketch_of(*finished)

    def _overlaps_keywell(self, face: Face) -> bool:
        return any(overlap_area(face, cutout) > 1e-6 for cutout in self._raw_keywell.faces())

    def _create_body(self) -> Face:
        """Fingers and thumbs inside the walls, without the cirque notch and without rounding."""
        thumb_cells = [self._cell(key, 2) for key in self.keys.thumb_keys]
        # the right wall ends level with the thumb corner. The closing fills the corner between wall and cluster
        shoulder = Vector(self.right, self.thumb_top.Y)
        polygon = polygon_face([self.bottom_left, self.top_left, self.top_right, shoulder, self.thumb_top, self.thumb_bottom_left])
        (body,) = close_concave(union_faces([polygon, *thumb_cells])[0], self.sweep_radius)
        return body

    def _create_cirque_notch(self) -> tuple[Face, Vector] | None:
        """The round recess of the trackpad and its center, in the first place that fits between a key and the thumb cluster.

        The recess moves sideways to that place.
        """
        for key in self.keys.keys:
            key_bottom_right = key.p + Vector(self.d_x, -self.d_y).rotate(Axis.Z, key.r)
            chord = self.thumb_bottom_left - key_bottom_right
            if self.cirque_recess_radius >= chord.length / 2:
                continue
            center = Vector(((key_bottom_right + self.thumb_bottom_left) / 2).X, self.cirque_recess_position.Y)
            notch = circle_face(center, self.cirque_recess_radius)
            if not self._overlaps_keywell(notch):
                return notch, center
        return None

    @staticmethod
    def _round(face: Face, radius: float) -> Face:
        rounded = [piece for closed in close_concave(face, radius) for piece in round_convex(closed, radius)]
        (result,) = rounded
        return result

    def _create_outer_face(self) -> Face:
        face = self._create_body()
        found = self._create_cirque_notch()
        if found is not None:
            notch, self.cirque_recess_position = found
            self.has_cirque_notch = True
            face = face.cut(notch)
        return self._round(face, self.spec.corner_radius)

    def create_inner_outline(self, offset_by=-1.8) -> Sketch:
        """The outline moved inwards (negative) or outwards.

        An offset keeps the center of a corner arc, so a corner of radius r gets r - |offset_by| on the side that shrinks.
        Rounding with that radius changes nothing there. When that radius gets small, the corner would turn (nearly) sharp.
        Then the rounding keeps it at half of r.
        """
        assert offset_by != 0, "Offset by zero is not allowed for inner outline."
        if offset_by not in self._inner_sketches:
            face = grow(self._outer_face, offset_by)
            face = self._round(face, max(self.spec.corner_radius - abs(offset_by), self.spec.corner_radius / 2))
            self._inner_sketches[offset_by] = sketch_of(face)
        return self._inner_sketches[offset_by]

    def _clip_to_cavity(self, cutout: Sketch) -> Sketch:
        """The rounded wall can poke into the cutout at a corner. The cutout keeps out of the wall."""
        cavity = self.inner_sketch.faces()[0]
        parts = [part for face in cutout.faces() for part in (face.intersect(cavity).faces() if face.intersect(cavity) else [])]
        return sketch_of(*parts)


# main method
if __name__ == "__main__":
    from ocp_viewer import *
    set_port(3939)
    show_clear()
    set_defaults(ortho=True, default_edgecolor="#121212", reset_camera=Camera.KEEP)
    set_colormap(ColorMap.accent())

    from duality_wave.models.choc import Choc
    from duality_wave.paths import LAYOUT_DIR

    switch = Choc()
    config_path = LAYOUT_DIR / 'wave.points.yaml'
    points = get_points(file_path=config_path)
    keys = ErgoKeys(points=points)
    
    outline = Outline(switch=switch, keys=keys, wall_thickness=1.8)
    with BuildSketch() as choc_key_holes:
        for key in keys.keys:
            with BuildSketch():
                with Locations(key.p):
                    Rectangle(switch.below.d.X, switch.below.d.Y, rotation=key.r)
    choc_sketch = outline.sketch
    choc_inner_sketch = outline.inner_sketch
    choc_keywell = outline.keywell_sketch

    show_all()


