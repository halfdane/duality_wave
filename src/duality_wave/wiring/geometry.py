"""Small 2D helpers on numpy arrays. A polygon is an array of corners, a path is an array of points."""

import math

import numpy as np

CIRCLE_SEGMENTS = 48


def rotation(angle_deg: float) -> np.ndarray:
    a = math.radians(angle_deg)
    return np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])


def rect(center, w: float, h: float, angle_deg: float) -> np.ndarray:
    """Corners of a rectangle with its centre at `center`, rotated about it."""
    corners = np.array([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]])
    return corners @ rotation(angle_deg).T + np.asarray(center)


def circle(center, radius: float) -> np.ndarray:
    t = np.linspace(0, 2 * math.pi, CIRCLE_SEGMENTS, endpoint=False)
    return np.asarray(center) + radius * np.column_stack([np.cos(t), np.sin(t)])


def point_segment_distance(p, a, b) -> float:
    ab = b - a
    t = np.clip(np.dot(p - a, ab) / np.dot(ab, ab), 0, 1)
    return float(np.linalg.norm(p - (a + t * ab)))


def points_segments_distance(points: np.ndarray, polygon: np.ndarray) -> np.ndarray:
    """Distance of each point to the nearest edge of a closed polygon."""
    a, b = polygon, np.roll(polygon, -1, axis=0)
    ab = b - a
    t = np.clip(((points[:, None, :] - a) * ab).sum(axis=2) / (ab * ab).sum(axis=1), 0, 1)
    return np.linalg.norm(points[:, None, :] - (a + t[..., None] * ab), axis=2).min(axis=1)


def boundary_distance(p: np.ndarray, q: np.ndarray) -> float:
    """Shortest distance between the boundaries of two closed polylines that do not cross."""
    return float(min(points_segments_distance(p, q).min(), points_segments_distance(q, p).min()))


def convex_overlap(p: np.ndarray, q: np.ndarray) -> bool:
    for poly in (p, q):
        for i in range(len(poly)):
            edge = poly[(i + 1) % len(poly)] - poly[i]
            axis = np.array([-edge[1], edge[0]])
            pp, qq = p @ axis, q @ axis
            if pp.max() <= qq.min() + 1e-9 or qq.max() <= pp.min() + 1e-9:
                return False
    return True


def inside(point, polygon: np.ndarray) -> bool:
    x, y = point
    result = False
    for i in range(len(polygon)):
        (x1, y1), (x2, y2) = polygon[i], polygon[(i + 1) % len(polygon)]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            result = not result
    return result


def inside_points(points: np.ndarray, polygon: np.ndarray) -> np.ndarray:
    """`inside` for many points at once."""
    points = np.asarray(points, dtype=float).reshape(-1, 2)
    x, y = points[:, 0:1], points[:, 1:2]
    x1, y1 = polygon[:, 0], polygon[:, 1]
    x2, y2 = np.roll(x1, -1), np.roll(y1, -1)
    crosses = (y1 > y) != (y2 > y)
    with np.errstate(divide="ignore", invalid="ignore"):
        at = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
    return ((crosses & (x < at)).sum(axis=1) % 2) == 1


def chain_points(segments: list[np.ndarray]) -> np.ndarray:
    """Join the edges of a wire to one closed polyline."""
    remaining = list(segments)
    chain = list(remaining.pop(0))
    while remaining:
        end = chain[-1]
        index, flip = min(
            ((i, f) for i in range(len(remaining)) for f in (False, True)),
            key=lambda c: np.linalg.norm((remaining[c[0]][-1] if c[1] else remaining[c[0]][0]) - end))
        seg = remaining.pop(index)
        chain.extend(list(seg[::-1] if flip else seg)[1:])
    return np.array(chain[:-1])


def wire_polyline(wire, step: float = 0.5) -> np.ndarray:
    """A build123d wire as a closed polyline."""
    segments = []
    for edge in wire.edges():
        n = max(2, int(edge.length / step) + 1)
        segments.append(np.array([[edge.position_at(t).X, edge.position_at(t).Y] for t in np.linspace(0, 1, n)]))
    return chain_points(segments)


def length(path: np.ndarray) -> float:
    return float(sum(np.linalg.norm(b - a) for a, b in zip(path[:-1], path[1:])))
