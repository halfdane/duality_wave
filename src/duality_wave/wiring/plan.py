"""The wiring of the keyplate as it is stored in ergogen/wave.wiring.yaml: the diode notches, the trenches and the channel.
The file is written by the wiring editor (`task wiring-editor`). The editor and tests/test_wiring.py check it.

All coordinates are in mm, in the frame of the blank (the left half). The builder mirrors the right keyplate afterwards.
The contacts of the switches sit on the other side of the key in the right half, so each half has its own notches and trenches.
A vertex of a trench is [x, y] or [x, y, r]. A coordinate does not follow the layout. The checks show the ends that miss their terminals.
The channel is one wide shallow recess along the top edge of the keyplate, from two opposite corners.
All the wires of the matrix end in it, and it opens into the pocket of the XIAO.
"""

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml

from duality_wave.models.diode import Diode
from duality_wave.wiring.rounded import Vertex, normalize

SIDES = ("left", "right")
LAYERS = ("underside", "top")

Paths = dict[str, list[list[Vertex]]]


class WiringFileError(ValueError):
    """The wiring file holds something that cannot be read. The message says where."""


@dataclass
class SidePlan:
    """What the builder cuts into one half, in coordinates of the blank.

    notches maps a key to (side, y). underside and top map the name of a net to its trenches, as vertices (x, y, r).
    channel is a polygon.
    """

    notches: dict[str, tuple[int, float]] = field(default_factory=dict)
    underside: Paths = field(default_factory=dict)
    top: Paths = field(default_factory=dict)
    channel: np.ndarray = field(default_factory=lambda: np.zeros((0, 2)))


@dataclass
class WiringPlan:
    """The file for both halves, and the diode it was made for."""

    left: SidePlan
    right: SidePlan
    diode: Diode = field(default_factory=Diode)

    def side(self, name: str) -> SidePlan:
        return getattr(self, name)

    @staticmethod
    def load(path: Path) -> "WiringPlan":
        data = read_file(path)
        channel = channel_polygon(*data["channel"])
        return WiringPlan(*(side_plan(data["sides"][name], channel) for name in SIDES), diode=data["diode"])


def coordinates(value, where: str, allow_radius: bool) -> list[float]:
    sizes = (2, 3) if allow_radius else (2,)
    if not isinstance(value, (list, tuple)) or len(value) not in sizes or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in value):
        shape = "[x, y] or [x, y, r]" if allow_radius else "[x, y]"
        raise WiringFileError(f"{where}: write {shape} with numbers, not {value!r}")
    return [float(v) for v in value]


def read_file(path: Path) -> dict:
    """The file as numbers, checked for its shape: {diode, channel: (low, high), sides: {half: {notches, underside, top}}}.
    The vertices are [x, y] or [x, y, r] as the file has them, so a corner without r stays without r."""
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise WiringFileError(f"{path.name}: the file is not a mapping")
    for key in ("diode", "channel", *SIDES):
        if key not in data:
            raise WiringFileError(f"{path.name}: `{key}` is missing")
    unknown = set(data) - {"diode", "channel", *SIDES}
    if unknown:
        raise WiringFileError(f"{path.name}: unknown keys {sorted(unknown)}. The file has diode, channel, left and right.")
    try:
        diode = Diode(**data["diode"])
    except TypeError as error:
        raise WiringFileError(f"diode: {error}") from error
    if not isinstance(data["channel"], dict) or set(data["channel"]) != {"from", "to"}:
        raise WiringFileError(f"channel: write {{from: [x, y], to: [x, y]}}, not {data['channel']!r}")
    a, b = (np.array(coordinates(data["channel"][k], f"channel {k}", False)) for k in ("from", "to"))
    low, high = np.minimum(a, b), np.maximum(a, b)
    if np.any(high - low <= 0):
        raise WiringFileError("channel: `from` and `to` must differ in X and in Y")
    return {"diode": diode, "channel": (low, high), "sides": {name: read_side(name, data[name]) for name in SIDES}}


def read_side(name: str, data) -> dict:
    if not isinstance(data, dict):
        raise WiringFileError(f"{name}: expected notches, underside and top")
    unknown = set(data) - {"notches", *LAYERS}
    if unknown:
        raise WiringFileError(f"{name}: unknown keys {sorted(unknown)}. A half has notches, underside and top. The channel is for both halves, at the top of the file.")
    for key in ("notches", *LAYERS):
        if not isinstance(data.get(key), dict):
            raise WiringFileError(f"{name}: `{key}` is missing")
    notches = {}
    for key, value in data["notches"].items():
        if not isinstance(value, dict) or set(value) != {"side", "y"} or value["side"] not in (-1, 1) or not isinstance(value["y"], (int, float)):
            raise WiringFileError(f"{name} notch {key}: write {{side: -1 or 1, y: <mm>}}, not {value!r}")
        notches[key] = (int(value["side"]), float(value["y"]))
    out: dict = {"notches": notches}
    for layer in LAYERS:
        out[layer] = {}
        for net, trenches in data[layer].items():
            if not isinstance(trenches, list):
                raise WiringFileError(f"{name} {layer} {net}: expected a list of trenches")
            out[layer][net] = []
            for i, trench in enumerate(trenches):
                where = f"{name} {layer} {net} trench {i + 1}"
                if not isinstance(trench, list) or len(trench) < 2:
                    raise WiringFileError(f"{where}: a trench has at least two vertices")
                out[layer][net].append([coordinates(v, f"{where}, vertex {j + 1}", True) for j, v in enumerate(trench)])
    return out


def channel_polygon(low: np.ndarray, high: np.ndarray) -> np.ndarray:
    return np.array([low, [high[0], low[1]], high, [low[0], high[1]]])


def side_plan(data: dict, channel: np.ndarray) -> SidePlan:
    def paths(layer: str) -> Paths:
        return {net: [normalize(trench) for trench in trenches] for net, trenches in data[layer].items()}

    return SidePlan(data["notches"], paths("underside"), paths("top"), channel)
