"""Checks on the hand-written wiring of one half: terminals, keep-outs, parallel wires, walls next to the trenches and the channel."""

import math
from dataclasses import dataclass, field

import numpy as np

from duality_wave.builders.common import CaseContext
from duality_wave.wiring import nets as nets_module
from duality_wave.wiring.anchors import Anchor, named_points
from duality_wave.wiring.geometry import inside, inside_points, points_segments_distance
from duality_wave.wiring.nets import WIRE_RADIUS, Disc, Net
from duality_wave.wiring.plan import SidePlan, WiringPlan
from duality_wave.wiring.plate import MIN_WALL, Notch, Plate
from duality_wave.wiring.rounded import Vertex, sample, tangent_overlaps

SAMPLE_STEP = 0.25
# a wire touches a terminal or another wire of its net when the centre lines come this close
TOUCH = 0.1
# a trench ends inside the pocket that holds its terminal, so near that terminal the wall to that one pocket does not count (mm).
# The walls to every other feature count everywhere.
END_ZONE = 2.0
# a terminal belongs to a pocket when it lies inside it or this close to it
OWN_REACH = 0.5
# wires of different nets that run side by side keep this centre distance
MIN_APART = 0.5
# the file holds 3 decimals, so a wall may come out this much thinner than the editor showed (mm)
WALL_SLACK = 0.005
PARALLEL_ANGLE = 30.0


class Problem(str):
    """A message about the wiring. `at` is the place in the plate (x, y) when there is one, and `layer` is where it lies."""

    at: np.ndarray | None
    layer: str

    def __new__(cls, message: str, at=None, layer: str = "underside") -> "Problem":
        problem = super().__new__(cls, message)
        problem.at = None if at is None else np.asarray(at, dtype=float)
        problem.layer = layer
        return problem


@dataclass
class Half:
    """One half with its plate, its notches and the nets of the matrix with the trenches of the plan."""

    plate: Plate
    plan: SidePlan
    notches: dict[str, Notch]
    nets: list[Net]
    discs: list[Disc]

    @staticmethod
    def of(ctx: CaseContext, plan: WiringPlan, side: str) -> "Half":
        plate = Plate(ctx, plan.diode, side)
        notches = plate.place(plan.side(side).notches)
        return Half.build(plate, plan.side(side), notches)

    @staticmethod
    def build(plate: Plate, side_plan: SidePlan, notches: dict[str, Notch]) -> "Half":
        """A half from a plan. The editor builds its halves this way, from numbers it got over the wire."""
        nets, discs = nets_module.matrix_nets(plate, notches)
        for net in nets:
            net.paths = side_plan.underside.get(net.name, [])
        return Half(plate, side_plan, notches, nets, discs)

    def sleeves(self) -> list[str]:
        """The keys whose diode sends the anode lead across the cutout of the switch. That lead needs an insulating sleeve."""
        return [name for name, notch in self.notches.items() if self.plate.needs_sleeve(notch.side)]

    def anchors(self) -> dict[str, Anchor]:
        """The named points of the plate, with the corners and the middle of the channel."""
        low, high = self.plan.channel.min(axis=0), self.plan.channel.max(axis=0)
        channel = {"channel.from": Anchor(low), "channel.to": Anchor(high), "channel.mid": Anchor((low + high) / 2)}
        return {**named_points(self.plate, self.notches), **channel}


@dataclass
class Result:
    problems: list[Problem] = field(default_factory=list)
    # the thinnest wall to each kind of feature, with the place
    walls: dict[str, tuple[float, np.ndarray]] = field(default_factory=dict)
    trench_length: float = 0.0


def polyline(path: list[Vertex]) -> np.ndarray:
    """The path as points at most SAMPLE_STEP apart."""
    line = sample(path, SAMPLE_STEP)
    pieces = [a + (b - a) * np.linspace(0, 1, max(2, math.ceil(np.linalg.norm(b - a) / SAMPLE_STEP) + 1))[:-1, None] for a, b in zip(line[:-1], line[1:])]
    return np.vstack([*pieces, line[-1:]])


def polylines(net: Net) -> list[np.ndarray]:
    return [polyline(path) for path in net.paths]


def densify(polygon: np.ndarray, step: float = SAMPLE_STEP) -> np.ndarray:
    """Points along the boundary of a closed polygon."""
    points = []
    for a, b in zip(polygon, np.roll(polygon, -1, axis=0)):
        n = max(1, int(np.linalg.norm(b - a) / step))
        points.extend(a + (b - a) * t for t in np.linspace(0, 1, n, endpoint=False))
    return np.array(points)


def edge_distance(points: np.ndarray, polygon: np.ndarray) -> np.ndarray:
    """Distance from each point to the boundary of a closed polygon, negative for a point inside."""
    distance = points_segments_distance(points, polygon)
    return np.where(inside_points(points, polygon), -distance, distance)


def inside_any(points: np.ndarray, polygons: list[np.ndarray]) -> np.ndarray:
    result = np.zeros(len(points), dtype=bool)
    for poly in polygons:
        result |= inside_points(points, poly)
    return result


def min_distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a[:, None] - b[None], axis=2).min())


def check_nets(half: Half) -> list[Problem]:
    """Every terminal is reached, the trenches of a net join up, and the net ends in the channel."""
    problems = []
    for net in half.nets:
        if not net.paths:
            problems.append(Problem(f"{net.name}: no trench", net.terminals[0]))
            continue
        lines = polylines(net)
        for terminal in net.terminals:
            if min(min_distance(line, terminal[None]) for line in lines) >= TOUCH:
                problems.append(Problem(f"{net.name}: no trench reaches the terminal at {terminal.round(1)}", terminal))
        joined = {0}
        while True:
            grown = {i for i in range(len(lines)) if i not in joined and any(min_distance(lines[i], lines[j]) < TOUCH for j in joined)}
            if not grown:
                break
            joined |= grown
        if len(joined) < len(lines):
            loose = sorted(set(range(len(lines))) - joined)
            problems.append(Problem(f"{net.name}: trenches {loose} do not join the others", lines[loose[0]][0]))
        if not inside_any(np.vstack(lines), [half.plan.channel]).any():
            problems.append(Problem(f"{net.name}: does not reach the channel", np.vstack(lines)[-1]))
        for i, path in enumerate(net.paths):
            for j in tangent_overlaps(path):
                problems.append(Problem(f"{net.name}: trench {i}: the corners at vertex {j - 1} and {j} do not fit", path[j][:2]))
    return problems


def check_keepouts(half: Half) -> list[Problem]:
    """Wires that come closer to a disc than its radius. A disc with an owner counts for the nets of other names."""
    found = []
    for net in half.nets:
        if not net.paths:
            continue
        lines = np.vstack(polylines(net))
        for disc in half.discs:
            if disc.owner == net.name:
                continue
            d = float(np.linalg.norm(lines - disc.center, axis=1).min()) - WIRE_RADIUS
            if d < disc.radius:
                found.append(Problem(f"{net.name}: {d:.2f} mm from a keep-out at {disc.center.round(1)} (needs {disc.radius})", disc.center))
    return found


def check_parallel(half: Half) -> list[Problem]:
    """Wires of different nets that run side by side closer than MIN_APART. A crossing is fine."""
    points, owner, angle = [], [], []
    for i, net in enumerate(half.nets):
        for line in polylines(net):
            for a, b in zip(line[:-1], line[1:]):
                if np.linalg.norm(b - a) > 1e-9:
                    points.append((a + b) / 2)
                    owner.append(i)
                    angle.append(math.degrees(math.atan2(*(b - a)[::-1])))
    points, owner, angle = np.array(points), np.array(owner), np.array(angle)
    near = (np.linalg.norm(points[:, None] - points[None], axis=2) < MIN_APART) & (owner[:, None] != owner[None])
    parallel = np.abs((angle[:, None] - angle[None] + 90) % 180 - 90) < PARALLEL_ANGLE
    hits = np.argwhere(near & parallel)
    return [Problem(f"{half.nets[owner[i]].name} and {half.nets[owner[j]].name} run closer than {MIN_APART} mm at {points[i].round(1)}", points[i])
            for i, j in hits if i < j][:5]


def features(half: Half, with_pocket: bool) -> dict[str, list[np.ndarray]]:
    plate = half.plate
    result = {"outline": [plate.keyplate_outline], "screw": list(plate.screws.values()),
              "power switch": [plate.power.body, plate.power.pins], "notch": [n.poly for n in half.notches.values()]}
    if with_pocket:
        result["xiao pocket"] = [plate.xiao_pocket]
    return result


def thinnest(points: np.ndarray, polygons: list[np.ndarray], radius: float, outer: bool, terminals: np.ndarray | None = None) -> tuple[float, np.ndarray]:
    """The thinnest wall between voids of the given radius around the points and a feature. The outline is a feature to stay inside of.
    Within END_ZONE of a terminal that belongs to a feature, the points do not count for that feature."""
    best = (math.inf, points[0])
    for polygon in polygons:
        own = np.zeros(len(points), dtype=bool)
        if terminals is not None and len(terminals):
            held = terminals[inside_points(terminals, polygon) | (points_segments_distance(terminals, polygon) < OWN_REACH)]
            if len(held):
                own = np.linalg.norm(points[:, None] - held, axis=2).min(axis=1) <= END_ZONE
        if own.all():
            continue
        shown = points[~own]
        d = edge_distance(shown, polygon)
        d = (-d if outer else d) - radius
        i = int(d.argmin())
        if d[i] < best[0]:
            best = (float(d[i]), shown[i])
    return best


def check_walls(half: Half, result: Result) -> None:
    """Walls between the trenches over solid plate and the features, and between the channel and the features."""
    plate, width = half.plate, half.plate.profile.trench_width
    free = [*plate.cutouts.values(), plate.xiao_pocket, half.plan.channel]
    points = np.vstack([line for net in half.nets for line in polylines(net)])
    terminals = np.array([t for net in half.nets for t in net.terminals])
    solid = points[~inside_any(points, free)]
    edge = densify(half.plan.channel)
    edge = edge[~inside_any(edge, [plate.xiao_pocket])]
    for label, polygons in features(half, with_pocket=True).items():
        for source, radius in (("trench", width / 2), ("channel", 0.0)):
            sample_points = solid if source == "trench" else edge
            if len(sample_points) == 0 or (source == "channel" and label == "xiao pocket"):
                continue
            wall, at = thinnest(sample_points, polygons, radius, outer=label == "outline", terminals=None if label == "outline" or source == "channel" else terminals)
            key = f"{source} to {label}"
            result.walls[key] = (wall, at)
            if wall < MIN_WALL - WALL_SLACK:
                result.problems.append(Problem(f"wall from the {source} to the {label} is {wall:.2f} mm at {at.round(1)}", at))
    if not inside_any(densify(half.plan.channel), [plate.xiao_pocket]).any():
        result.problems.append(Problem("the channel does not open into the XIAO pocket", half.plan.channel.mean(axis=0)))
    for disc in half.discs:
        if inside(disc.center, half.plan.channel):
            result.problems.append(Problem(f"a contact or post lies in the channel at {disc.center.round(1)}", disc.center))
    lengths = [np.linalg.norm(np.diff(line, axis=0), axis=1) for net in half.nets for line in polylines(net)]
    mids = [(line[:-1] + line[1:]) / 2 for net in half.nets for line in polylines(net)]
    result.trench_length = float(sum(l[~inside_any(m, free)].sum() for l, m in zip(lengths, mids)))


TOP_END_REACH = 0.5


def check_top(half: Half) -> list[Problem]:
    """The power wires on the top face: each starts at its pin, stays out of the pockets, and ends at the window of the XIAO."""
    plate, found = half.plate, []
    blocked = [plate.power.body, *plate.top_cutouts.values(), *(n.poly for n in half.notches.values())]
    for i, (name, paths) in enumerate(half.plan.top.items()):
        if i >= len(plate.power.tips):
            found.append(Problem(f"{name}: the power switch has no pin for it", layer="top"))
            continue
        tip = plate.power.tips[i]
        if not paths:
            found.append(Problem(f"{name}: no trench", tip, "top"))
            continue
        ends = [np.array(v[:2]) for path in paths for v in (path[0], path[-1])]
        if min(np.linalg.norm(e - tip) for e in ends) >= TOUCH:
            found.append(Problem(f"{name}: no trench starts at the pin at {tip.round(1)}", tip, "top"))
        window_edge = densify(plate.xiao_window)
        if not any(inside(path[-1][:2], plate.xiao_window) or np.linalg.norm(window_edge - np.array(path[-1][:2]), axis=1).min() < TOP_END_REACH for path in paths):
            found.append(Problem(f"{name}: does not end at the window of the XIAO", paths[-1][-1][:2], "top"))
        for path in paths:
            line = polyline(path)
            hit = inside_any(line, blocked)
            if hit.any():
                found.append(Problem(f"{name}: runs into a pocket at {line[hit][0].round(1)}", line[hit][0], "top"))
            for j in tangent_overlaps(path):
                found.append(Problem(f"{name}: the corners at vertex {j - 1} and {j} do not fit", path[j][:2], "top"))
    return found


def check(half: Half) -> Result:
    result = Result()
    names = {net.name for net in half.nets}
    result.problems += [Problem(f"the plan has trenches for {name}, which is no net") for name in half.plan.underside if name not in names]
    result.problems += check_nets(half)
    result.problems += check_top(half)
    if any(not net.paths for net in half.nets):
        return result
    result.problems += check_keepouts(half) + check_parallel(half)
    check_walls(half, result)
    return result
