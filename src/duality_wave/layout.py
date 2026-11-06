from dataclasses import dataclass, field

import yaml
from build123d import Vector


@dataclass
class Point:
    p: Vector = Vector(0, 0)
    r: float = 0
    meta: dict = field(default_factory=dict)


def get_points(file_path: str) -> dict[str, Point]:
    """Read the points.yaml that ergogen writes (task layout). The keys keep the order of the file."""
    with open(file_path) as f:
        raw = yaml.safe_load(f)
    points = {name: Point(p=Vector(data["x"], data["y"]), r=data["r"], meta=data.get("meta", {})) for name, data in raw.items()}
    return {name: point for name, point in points.items() if not point.meta.get("skip", False)}
