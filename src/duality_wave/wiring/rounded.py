"""A path with rounded corners, stored as vertices (x, y, r). r is the radius of the arc at the vertex, 0 for a sharp corner.
A vertex written as [x, y] gets a radius of DEFAULT_RADIUS, or less where the neighbours are close.

The arc at a vertex touches both neighbouring segments. The builder and the drawing both rebuild it from the numbers.
"""

import math

import numpy as np

Vertex = tuple[float, float, float]

DEFAULT_RADIUS = 1.5


def corner_arc(a: np.ndarray, b: np.ndarray, c: np.ndarray, r: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Start, middle, end and centre of the arc of radius r that rounds the corner at b between a and c."""
    u, v = a - b, c - b
    u, v = u / np.linalg.norm(u), v / np.linalg.norm(v)
    half = math.acos(float(np.clip(np.dot(u, v), -1, 1))) / 2
    tangent = r / math.tan(half)
    bisector = (u + v) / np.linalg.norm(u + v)
    centre = b + bisector * r / math.sin(half)
    return b + u * tangent, centre - bisector * r, b + v * tangent, centre


def arc_samples(start: np.ndarray, mid: np.ndarray, end: np.ndarray, centre: np.ndarray, step: float) -> np.ndarray:
    r = float(np.linalg.norm(start - centre))
    a0 = math.atan2(*(start - centre)[::-1])
    a1 = math.atan2(*(end - centre)[::-1])
    delta = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    steps = max(3, int(abs(delta) * r / step))
    return np.array([centre + r * np.array([math.cos(a0 + delta * t), math.sin(a0 + delta * t)]) for t in np.linspace(0, 1, steps)])


# a corner whose two segments are straight on (or fold back, or have no length) has no arc
STRAIGHT = 0.02


def corner_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float | None:
    """The angle at b between a and c, or None where there is no arc to round: a segment without length, a straight line or a fold."""
    lu, lv = np.linalg.norm(a - b), np.linalg.norm(c - b)
    if lu < 1e-9 or lv < 1e-9:
        return None
    angle = math.acos(float(np.clip(np.dot(a - b, c - b) / (lu * lv), -1, 1)))
    return angle if STRAIGHT <= angle <= math.pi - STRAIGHT else None


def normalize(points: list[list[float]]) -> list[Vertex]:
    """Vertices from a file. [x, y, r] is kept, but a corner that has no arc is sharp. [x, y] gets the largest radius up to DEFAULT_RADIUS that fits between its neighbours."""
    result: list[Vertex] = []
    for i, v in enumerate(points):
        r = 0.0
        if 0 < i < len(points) - 1:
            a, b, c = (np.array(points[j][:2], dtype=float) for j in (i - 1, i, i + 1))
            angle = corner_angle(a, b, c)
            if angle is not None:
                r = float(v[2]) if len(v) == 3 else min(DEFAULT_RADIUS, 0.5 * min(np.linalg.norm(a - b), np.linalg.norm(c - b)) * math.tan(angle / 2))
        elif len(v) == 3:
            r = float(v[2])
        result.append((float(v[0]), float(v[1]), r))
    return result


def tangent_overlaps(vertices: list[Vertex]) -> list[int]:
    """Indices of the vertices whose arcs do not fit: the tangents on one segment add up to more than the segment."""
    points = [np.array(v[:2]) for v in vertices]
    tangents = [0.0] * len(vertices)
    for i in range(1, len(vertices) - 1):
        if vertices[i][2] > 0:
            start, _, _, _ = corner_arc(points[i - 1], points[i], points[i + 1], vertices[i][2])
            tangents[i] = float(np.linalg.norm(start - points[i]))
    return [i for i in range(1, len(vertices)) if tangents[i - 1] + tangents[i] > np.linalg.norm(points[i] - points[i - 1]) + 1e-6]


def segments(vertices: list[Vertex]) -> list[tuple]:
    """The pieces of the path: ("line", p0, p1) and ("arc", start, mid, end), in order."""
    points = [np.array(v[:2]) for v in vertices]
    pieces: list[tuple] = []
    cursor = points[0]
    for i in range(1, len(vertices) - 1):
        r = vertices[i][2]
        if r <= 0:
            if np.linalg.norm(points[i] - cursor) > 1e-9:
                pieces.append(("line", cursor, points[i]))
            cursor = points[i]
            continue
        start, mid, end, _ = corner_arc(points[i - 1], points[i], points[i + 1], r)
        if np.linalg.norm(start - cursor) > 1e-9:
            pieces.append(("line", cursor, start))
        pieces.append(("arc", start, mid, end))
        cursor = end
    if np.linalg.norm(points[-1] - cursor) > 1e-9:
        pieces.append(("line", cursor, points[-1]))
    return pieces


def sample(vertices: list[Vertex], step: float = 0.25) -> np.ndarray:
    """The path as a polyline. Arcs are cut into steps of about `step` mm."""
    points = [np.array(v[:2]) for v in vertices]
    result = [points[0]]
    for i in range(1, len(vertices) - 1):
        r = vertices[i][2]
        if r <= 0:
            result.append(points[i])
            continue
        start, mid, end, centre = corner_arc(points[i - 1], points[i], points[i + 1], r)
        result.extend(arc_samples(start, mid, end, centre, step))
    result.append(points[-1])
    return np.array(result)
