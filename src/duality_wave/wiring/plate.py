"""The keyplate as flat shapes, and the diode notches.

A notch is a pocket for one through-hole diode. It sits beside the cutout of its switch, along the Y axis of the key,
and opens into that cutout. The planner picks a side and a Y offset for every key and checks the walls around the notch.
A Plate is made for one half. All coordinates are those of the blank (the left half). The blank of the right half
is mirrored later, but its switches are not: they stand mirrored in position and turned the other way, with their contacts
on the other side. The Plate of the right half puts the contacts of the switch where they land in the blank frame.
"""

import math
from dataclasses import dataclass

import numpy as np
from build123d import Pos

from duality_wave.builders import bottom
from duality_wave.builders.common import CaseContext, powerswitch_location, powerswitch_plane
from duality_wave.models.diode import Diode, DiodeNotchSpec
from duality_wave.models.power_switch import PowerSwitch, keyplate_cut
from duality_wave.models.xiao import Xiao
from duality_wave.wiring.geometry import (
    boundary_distance, circle, convex_overlap, inside, point_segment_distance, rect, rotation, wire_polyline)

# the wall to keep around a notch. A smaller wall is reported but not refused
MIN_WALL = 0.8
# on the side of p2 a thinner wall is accepted, to keep the anode lead short
SOFT_WALL = 0.5
# the bare anode lead keeps this far from the contact p1 and the centre post of its switch (edge to edge)
LEAD_CLEARANCE = 0.5
# Y offsets (in the frame of the key) that the planner tries, in this order. The first is the default place:
# the anode end (-Y end) sits just in front of the Y of pin p2 (-3.8), so the lead leaves the body and bends about 90 degrees towards p2
DEFAULT_Y = -1.5
Y_STEPS = [DEFAULT_Y + d for d in (0, 0.5, -0.5, 1.0, -1.0, 1.5, -1.5, 2.0, -2.0, 3.0, 4.0)]
SIDES = ("left", "right")

# key name -> (side, y). side -1 is the -X side of the key, +1 the other side
SPEC_OVERRIDES: dict[str, tuple[int, float]] = {}


@dataclass(frozen=True)
class Notch:
    key: str
    # -1 is the -X side of the key (in the frame of the blank), +1 the other side
    side: int
    # Y offset of the centre of the diode in the frame of the key
    y: float
    poly: np.ndarray
    center: np.ndarray
    angle: float
    wall: float
    closest: str


@dataclass(frozen=True)
class PowerCut:
    """The cut for the power switch in the keyplate, and the pins that reach the top face."""

    body: np.ndarray
    pins: np.ndarray
    # the pin tips at the top face, from low Y to high Y
    tips: list[np.ndarray]


class Plate:
    """Everything on the keyplate that a notch or a wire must keep away from, and the keys that carry notches."""

    def __init__(self, ctx: CaseContext, diode: Diode, side: str = "left"):
        assert side in SIDES, side
        self.ctx = ctx
        self.side = side
        self.diode = diode
        self.switch = ctx.switch
        self.dims = dims = ctx.dims
        profile = dims.print_profile
        self.profile = profile
        self.spec = DiodeNotchSpec.of(diode, profile, dims.keyplate_z, dims.bottom_plate_z)
        # the contacts of a switch of the right half sit on the other side of the key, in the frame of the blank
        self.mirror = -1 if side == "right" else 1
        self.default_side = int(math.copysign(1, self.local(ctx.switch.posts.p2)[0]))

        self.names = list(ctx.keys.points)
        self.points = ctx.keys.points
        # the cutout below the clamp level, where the notch opens into it, and the top part of the cutout
        self.cutout_half = self.switch.below.d.X / 2 + profile.switch_clearance + 0.5
        self.top_half = self.switch.below.d.X / 2 + profile.switch_clearance
        self.cutouts = {name: rect((p.p.X, p.p.Y), 2 * self.cutout_half, 2 * self.cutout_half, p.r) for name, p in self.points.items()}
        self.top_cutouts = {name: rect((p.p.X, p.p.Y), 2 * self.top_half, 2 * self.top_half, p.r) for name, p in self.points.items()}

        self.keyplate_outline = wire_polyline(
            ctx.outline.create_inner_outline(offset_by=-dims.wall_thickness - profile.plate_clearance).faces()[0].outer_wire())
        screw_radius = ctx.screw.dims.shaft.radius + profile.screw_clearance
        self.screws = {f"screw {i}": circle((v.X, v.Y), screw_radius) for i, v in enumerate(dims.fastener_positions)}
        xiao = dims.xiao_position
        self.xiao_pocket = rect((xiao.X, xiao.Y), Xiao.dims.d.X + 2 * profile.xiao_clearance, Xiao.dims.d.Y + 2 * profile.xiao_clearance, 0)
        # the window in the top face of the keyplate, above the ledge that holds the board
        self.xiao_window = rect((xiao.X, xiao.Y), Xiao.dims.d.X - 1.5, Xiao.dims.d.Y - 4, 0)
        self.fixed: dict[str, np.ndarray] = {**self.screws, "xiao": self.xiao_pocket}

        self.power = self.power_cut()
        self.bottom_features = self.bottom_plate_features()

    @property
    def xiao(self):
        return self.dims.xiao_position

    def local(self, post) -> tuple[float, float]:
        """Place of a post in the frame of its key. The underside is seen mirrored, so Y flips."""
        return self.mirror * post.p.X, -post.p.Y

    def local_to_world(self, name: str, local) -> np.ndarray:
        p = self.points[name]
        return rotation(p.r) @ np.asarray(local, dtype=float) + np.array([p.p.X, p.p.Y])

    def pin(self, name: str, post) -> np.ndarray:
        return self.local_to_world(name, self.local(post))

    def power_cut(self) -> PowerCut:
        dims = self.dims
        plane = powerswitch_plane(dims)
        polys = []
        for x, y, w, h in keyplate_cut(dims.clearance):
            corners = [(x + sx * w / 2, y + sy * h / 2) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
            polys.append(np.array([[q.X, q.Y] for q in (plane.from_local_coords(c) for c in corners)]))
        location = powerswitch_location(dims)
        tips = [(location * Pos(t)).position for t in PowerSwitch().pin_tips]
        top = max(t.Z for t in tips)
        # the pins of the top row lie in the top face of the keyplate, where the wires run
        upper = sorted((t for t in tips if abs(t.Z - top) < 1e-6), key=lambda t: t.Y)
        assert -self.profile.trench_depth < top <= 0, f"the pins of the power switch are not reachable from the top face (z = {top})"
        return PowerCut(polys[0], polys[1], [np.array([t.X, t.Y]) for t in upper])

    def bottom_plate_features(self) -> dict[str, np.ndarray]:
        """Pockets and recesses of the bottom plate that a diode pocket in the bottom plate must keep away from."""
        dims, profile = self.dims, self.profile
        xiao = self.xiao
        shapes: dict[str, np.ndarray] = {}
        centre = (xiao.X, xiao.Y - Xiao.processor.forward_y)
        shapes["processor recess"] = rect(
            centre, Xiao.processor.d.X + bottom.XIAO_PROCESSOR_SLACK, Xiao.processor.d.Y + bottom.XIAO_PROCESSOR_SLACK, 0)
        shapes["board recess"] = rect(
            centre, Xiao.dims.d.X - bottom.XIAO_BOARD_INSET, Xiao.dims.d.Y - 2 * Xiao.processor.forward_y + 4, 0)
        radius = self.ctx.bumper.dims.radius + profile.bumper_clearance
        for i, v in enumerate(dims.bumper_locations):
            shapes[f"bumper {i}"] = circle((v.X, v.Y), radius)
        head = self.ctx.screw.dims.head.radius + profile.screw_head_clearance
        for i, v in enumerate(dims.fastener_positions):
            shapes[f"screw head {i}"] = circle((v.X, v.Y), head)
        return shapes

    def notch_poly(self, name: str, side: int, y: float) -> tuple[np.ndarray, np.ndarray]:
        x, poly_y, width, length = self.spec.pocket(self.cutout_half, side, y)
        r = self.points[name].r
        center = self.local_to_world(name, (x, y))
        return rect(self.local_to_world(name, (x, poly_y)), width, length, r), center

    def y_range(self) -> tuple[float, float]:
        """The lowest and the highest Y of a diode centre (frame of the key) for which the whole pocket still lies along the wall of the cutout."""
        _, pocket_y, _, length = self.spec.pocket(self.cutout_half, 1, 0.0)
        return -self.cutout_half - (pocket_y - length / 2), self.cutout_half - (pocket_y + length / 2)

    def needs_sleeve(self, side: int) -> bool:
        """A notch on the side away from the contact p2 sends the anode lead across the cutout, so the lead needs an insulating sleeve."""
        return side != self.default_side

    def wall(self, name: str, poly: np.ndarray, placed: dict[str, "Notch"]) -> tuple[float, str]:
        """Thinnest wall around a notch and what it is next to. An overlap counts as -1."""
        worst, closest = math.inf, ""
        obstacles = {f"cutout {k}": v for k, v in self.cutouts.items() if k != name}
        obstacles.update({f"notch {k}": n.poly for k, n in placed.items() if k != name})
        obstacles.update(self.fixed)
        obstacles.update({"power switch": self.power.body, "power switch pins": self.power.pins})
        obstacles.update({k: v for k, v in self.bottom_features.items() if k != f"channel {name}"})
        for label, other in obstacles.items():
            d = -1.0 if convex_overlap(poly, other) else boundary_distance(poly, other)
            if d < worst:
                worst, closest = d, label
        if not all(inside(v, self.keyplate_outline) for v in poly):
            return -1.0, "outline"
        d = boundary_distance(poly, self.keyplate_outline)
        if d < worst:
            worst, closest = d, "outline"
        return worst, closest

    def lead_clearance(self, name: str, center: np.ndarray, angle: float) -> float:
        """Smallest distance of the bare anode lead (body end, straight part, pin p2) to the contact p1 and the centre post of its own switch."""
        r = rotation(angle)
        body_end = center + r @ np.array([0, -self.diode.body_l / 2])
        tip = center + r @ np.array([0, -self.diode.body_l / 2 - self.spec.lead_straight])
        lead = np.array([body_end, tip, self.pin(name, self.switch.posts.p2)])
        posts = (self.pin(name, self.switch.posts.p1), self.pin(name, self.switch.posts.center))
        radii = (self.switch.posts.p1.d.radius, self.switch.posts.center.d.radius)
        return min(
            min(point_segment_distance(post, a, b) for a, b in zip(lead[:-1], lead[1:])) - radius
            for post, radius in zip(posts, radii)) - self.diode.lead_d / 2

    def candidate(self, name: str, side: int, y: float, placed: dict[str, Notch]) -> tuple[Notch, bool]:
        poly, center = self.notch_poly(name, side, y)
        wall, closest = self.wall(name, poly, placed)
        angle = self.points[name].r
        return Notch(name, side, y, poly, center, angle, wall, closest), self.lead_clearance(name, center, angle) >= LEAD_CLEARANCE

    def choose(self, name: str, placed: dict[str, Notch]) -> Notch:
        """The first place with a full wall and a clear lead. On the side of p2 a thinner wall (SOFT_WALL) is better than a long lead across the cutout."""
        if name in SPEC_OVERRIDES:
            return self.candidate(name, *SPEC_OVERRIDES[name], placed)[0]
        best: Notch | None = None
        for side in (self.default_side, -self.default_side):
            soft: Notch | None = None
            for y in Y_STEPS:
                notch, clear = self.candidate(name, side, y, placed)
                if not clear:
                    continue
                if notch.wall >= MIN_WALL:
                    return notch
                if soft is None or notch.wall > soft.wall:
                    soft = notch
            if soft is not None and side == self.default_side and soft.wall >= SOFT_WALL:
                return soft
            if soft is not None and (best is None or soft.wall > best.wall):
                best = soft
        return best if best is not None else self.candidate(name, self.default_side, DEFAULT_Y, placed)[0]

    def plan(self) -> dict[str, Notch]:
        placed: dict[str, Notch] = {}
        for name in self.names:
            placed[name] = self.choose(name, placed)
        # the first keys chose without the later notches, so measure every wall again with all notches in place
        final: dict[str, Notch] = {}
        for name, notch in placed.items():
            wall, closest = self.wall(name, notch.poly, placed)
            final[name] = Notch(name, notch.side, notch.y, notch.poly, notch.center, notch.angle, wall, closest)
        return final

    def notch_at(self, name: str, side: int, y: float) -> Notch:
        """A notch at the given place, with its wall not measured yet."""
        poly, center = self.notch_poly(name, side, y)
        return Notch(name, side, y, poly, center, self.points[name].r, math.inf, "")

    def place(self, places: dict[str, tuple[int, float]]) -> dict[str, Notch]:
        """The notches of a plan that was read from a file, with their walls measured."""
        notches = {name: self.notch_at(name, side, y) for name, (side, y) in places.items()}
        measured = {}
        for name, notch in notches.items():
            wall, closest = self.wall(name, notch.poly, notches)
            measured[name] = Notch(name, notch.side, notch.y, notch.poly, notch.center, notch.angle, wall, closest)
        return measured
