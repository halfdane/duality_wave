if __name__ == "__main__":
    import sys, os
    # add parent directory to path
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import math
from build123d import *
from models.switch import Switch
from models.keys import ErgoKeys
from ergogen import Point, get_points

class Outline:
    def __init__(self, switch: Switch, keys: ErgoKeys, wall_thickness=1.8, additional_top_space=10):
        self.switch = switch
        self.keys = keys
        
        self.wall_thickness = wall_thickness

        self.cirque_recess_radius = 22
        self.cirque_recess_position = Vector(30, -24)
        
        self.d_x = switch.cap.d.X / 2 + 2*wall_thickness
        self.d_y = switch.cap.d.Y / 2 + 2*wall_thickness

        self.keywell_sketch, fingers_sketch = self.create_keywell_outline()
        # find left, right, top, bottom points
        finger_outer_points = ShapeList({e.start_point() for e in fingers_sketch.edges()} | {e.end_point() for e in fingers_sketch.edges()})
        self.left = finger_outer_points.sort_by(Axis.X)[0].X - self.wall_thickness
        self.right = finger_outer_points.sort_by(Axis.X)[-1].X + self.wall_thickness
        self.bottom = finger_outer_points.sort_by(Axis.Y)[0].Y - self.wall_thickness
        self.top = finger_outer_points.sort_by(Axis.Y)[-1].Y + self.wall_thickness + additional_top_space

        self.bottom_left = Vector(self.left, self.bottom)
        self.top_left = Vector(self.left, self.top) 
        self.top_right = Vector(self.right, self.top) 
        self.bottom_right = Vector(self.right, self.bottom) 
        self.mid_right = (self.top_right + self.bottom_right) / 2

        self.sketch = self.create_outline()
        self.inner_sketch = self.create_inner_outline(-self.wall_thickness)

    def is_crossing_keywell(self, edges: list[Edge]) -> bool:
        for e in edges: 
            for edge in self.keywell_sketch.edges():
                inter = e.intersect(edge)
                if inter:
                    return True
        return False

    def create_outline(self):
        bottom_left_thumb_key = self.keys.thumb_clusters[0][0][0]
        bottom_right_thumb_key = self.keys.thumb_clusters[0][len(self.keys.thumb_clusters[0])-1][0]

        self.thumb_bottom_left = bottom_left_thumb_key.p + Vector(-self.d_x+self.wall_thickness, -self.d_y+1).rotate(Axis.Z, bottom_left_thumb_key.r)
        self.thumb_bottom_right = bottom_right_thumb_key.p + Vector(self.d_x, -self.d_y).rotate(Axis.Z, bottom_right_thumb_key.r)

        
        with BuildSketch() as outline:
            with BuildLine() as line:
                l1 = Line(self.bottom_left, self.top_left)
                l2 = Line(self.top_left, self.top_right)
                l3 = Line(self.top_right, self.mid_right)

                # just try every top thumb key until there's one that doesn't intersect the keywell
                for thumb_col_index in range(len(self.keys.thumb_clusters[0])):
                    top_right_thumb_key = self.keys.thumb_clusters[0][thumb_col_index][len(self.keys.thumb_clusters[0][thumb_col_index])-1]
                    self.thumb_top = top_right_thumb_key.p + Vector(self.d_x, self.d_y).rotate(Axis.Z, top_right_thumb_key.r)
                    t = TangentArc([self.mid_right, self.thumb_top], tangent=l3 % 1, mode=Mode.PRIVATE)
                    if not self.is_crossing_keywell(t.edges()):
                        add(t)
                        break

                l4 = Line(self.thumb_top, self.thumb_bottom_left)
                l5 = Line(self.thumb_bottom_left, self.bottom_left)
            make_face()

            # add rectangles for all thumb keys to add them to the outline
            for thumb_key in self.keys.thumb_keys:
                with Locations(thumb_key.p):
                    Rectangle(2*self.d_x, 2*self.d_y, rotation=thumb_key.r)

            # position the circle in a way that it touches self.thumb_bottom_left
            # iterate over lowest keys to find a good place
            found_position = False
            for cluster in self.keys.clusters:
                if found_position:
                    break
                for col in cluster:
                    if found_position:
                        break
                    for key in col:
                        if found_position:
                            break

                        key_bottom_right = key.p + Vector(self.d_x, -self.d_y).rotate(Axis.Z, key.r)
                        midpoint = (key_bottom_right + self.thumb_bottom_left) / 2
                        chord_vec = self.thumb_bottom_left - key_bottom_right

                        loc = Vector(midpoint.X, self.cirque_recess_position.Y)
                        with Locations(loc):
                            c = Circle(self.cirque_recess_radius, mode=Mode.PRIVATE)
                        if self.cirque_recess_radius < chord_vec.length / 2 and not self.is_crossing_keywell(c.edges()):
                            # there's definitelly enough space for the circle here - just position it next to the thumb cluster
                            add(c, mode=Mode.SUBTRACT)
                            self.cirque_recess_position = loc
                            found_position = True
            # fillet all vertices except self.mid_right: there's no corner, it's a tangent arc
            # Vertex.__eq__ compares OCCT TShape identity, not position, so compare coordinates instead
            fillet(
                vertices().filter_by(
                    lambda v: (Vector(v.X, v.Y, v.Z) - self.mid_right).length > 1e-6
                ),
                radius=1,
            )
        return outline.sketch
    
    def fillet_sharp_corners(self, radius: float, min_angle: float = 1.0):
        """Fillet every sharp corner of the sketch that is currently being built.

        Corners are handled one at a time in a fixed (x, y) order, and the vertices are looked up
        again after every fillet: filleting a stale vertex changes the result depending on the
        order in which OCCT happens to return the vertices, which differs from run to run.
        """
        attempted: set[tuple[float, float]] = set()

        def is_sharp(vertex: Vertex) -> bool:
            position = Vector(vertex.X, vertex.Y, vertex.Z)
            directions = []
            for edge in edges():
                if (edge.start_point() - position).length < 1e-6:
                    directions.append(edge.tangent_at(0))
                elif (edge.end_point() - position).length < 1e-6:
                    directions.append(-edge.tangent_at(1))
            return len(directions) == 2 and directions[0].get_angle(directions[1]) < 180 - min_angle

        while True:
            candidates = sorted(
                (v for v in vertices() if (round(v.X, 4), round(v.Y, 4)) not in attempted and is_sharp(v)),
                key=lambda v: (round(v.X, 4), round(v.Y, 4)),
            )
            if not candidates:
                return
            vertex = candidates[0]
            attempted.add((round(vertex.X, 4), round(vertex.Y, 4)))
            try:
                fillet(vertex, radius=radius)
            except Exception:
                # corners that cannot be rounded stay sharp
                pass

    def create_inner_outline(self, offset_by=-1.8):
        with BuildSketch() as inner_outline:
            add(self.sketch)
            if offset_by != 0:
                offset(amount=offset_by)
                self.fillet_sharp_corners(radius=1)

            rect_y = 15
            with Locations(self.cirque_recess_position + (0, self.cirque_recess_radius - rect_y/3)):
                r = RectangleRounded(25, rect_y, radius=rect_y/2 - 0.01, mode=Mode.PRIVATE)
                if not self.is_crossing_keywell(r.edges()):
                    RectangleRounded(25, rect_y, radius=rect_y/2 - 0.01, mode=Mode.SUBTRACT)

        return inner_outline.sketch

    def create_keywell_outline(self):
        # how much should key-dims be scaled for the outline, so there's no interference with the keywell
        clearance_scale = 1.5
        with BuildSketch() as fingers_outline:
            for key in self.keys.finger_keys:
                with BuildSketch():
                    with Locations(key.p):
                        Rectangle(self.d_x*clearance_scale, self.d_y*clearance_scale, rotation=key.r)
        with BuildSketch() as thumbs_outline:
            for key in self.keys.thumb_keys:
                with BuildSketch():
                    with Locations(key.p):
                        Rectangle(self.d_x*clearance_scale, self.d_y*clearance_scale, rotation=key.r)

        with BuildSketch() as keywell_outline:
            add(fingers_outline)
            add(thumbs_outline)

            # remove small areas
            for wire in wires().filter_by(lambda w: w.area < 20):
                with BuildLine() as line:
                    add(wire)
                make_face()

            # iterate over pairs of edges and fillet acute angles
            t = edges()
            pairs = zip(t, t[1:] + t[:1])
            for e1, e2 in pairs:
                angle = e1.tangent_at(0).get_angle(e2.tangent_at(0))
                if angle < 30 or angle > 150:
                    v = vertices().filter_by(lambda v: v in e1.vertices() and v in e2.vertices())
                    if v:
                        try:
                            fillet(v, radius=0.7)
                        except Exception as e:
                            pass

        return keywell_outline.sketch, fingers_outline.sketch

def add_arrows(edges):
    with BuildSketch() as arrows:
        for edge in edges:
            with Locations(edge.center()):
                # get rotation angle in degrees
                angle = math.degrees(math.atan2(edge.end_point().Y - edge.start_point().Y, edge.end_point().X - edge.start_point().X))
                ArrowHead(size=5, rotation=angle)
    return arrows.sketch

# main method
if __name__ == "__main__":
    from ocp_vscode import *
    set_port(3939)
    show_clear()
    set_defaults(ortho=True, default_edgecolor="#121212", reset_camera=Camera.KEEP)
    set_colormap(ColorMap.accent())

    from models.choc import Choc
    from models.cherry import Cherry

    switch = Choc()
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'ergogen', 'wave.yml')
    points = get_points(file_path=config_path)
    keys = ErgoKeys(points=points)
    
    outline = Outline(switch=switch, keys=keys, wall_thickness=1.8)
    with BuildSketch() as choc_key_holes:
        for key in keys.keys:
            with BuildSketch():
                with Locations(key.p):
                    Rectangle(switch.below.d.X, switch.below.d.Y, rotation=key.r)
    choc_sketch = outline.sketch
    choc_sketch_arrows = add_arrows(choc_sketch.edges())
    choc_inner_sketch = outline.inner_sketch
    choc_inner_sketch_arrows = add_arrows(choc_inner_sketch.edges())
    choc_keywell = outline.keywell_sketch
    choc_keywell_arrows = add_arrows(choc_keywell.edges())

    # # switch = Cherry()
    # # keys = Keys(switch=switch)
    # # outline = Outline(switch=switch, keys=keys, wall_thickness=1.8)
    # # with BuildSketch() as cherry_key_holes:
    # #     for keycol in keys.keycols:
    # #         with BuildSketch():
    # #             with Locations(keycol.locs):
    # #                 Rectangle(switch.below.d.X, switch.below.d.Y, rotation=keycol.rotation)
    # # cherry_sketch = outline.sketch
    # # cherry_inner_sketch = outline.inner_sketch
    # # cherry_keywell = outline.keywell_sketch

    show_all()


