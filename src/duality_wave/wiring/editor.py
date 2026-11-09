"""The logic behind the visual wiring editor (scripts/wiring_editor.py): geometry, checks and saving as plain data.

The editor works on coordinates of the plate. A vertex is [x, y, r]. r is None when the corner has no radius of its own
(it gets the automatic one). `Editor.save` writes the vertices as plain coordinates (duality_wave.wiring.export).
"""

import shutil
import tempfile
from pathlib import Path

import numpy as np

from duality_wave.builders.common import CaseContext
from duality_wave.paths import BUILD_DIR, WIRING_FILE
from duality_wave.wiring import check, export
from duality_wave.wiring import nets as nets_module
from duality_wave.wiring.geometry import rect, rotation
from duality_wave.wiring.plan import LAYERS, SIDES, SidePlan, WiringPlan, read_file
from duality_wave.wiring.plate import MIN_WALL, Plate
from duality_wave.wiring.rounded import normalize

VERIFY_TOLERANCE = 0.03
# the anchors the editor snaps to
SNAP_SUFFIXES = (".p1", ".cathode")


class EditorError(ValueError):
    """The editor cannot do what was asked. The message says why."""


def r2(values) -> list:
    return np.round(np.asarray(values, dtype=float), 3).tolist()


def hex_color(color) -> str:
    return "#%02x%02x%02x" % tuple(color)


def plain(path: list) -> list[list[float]]:
    """The vertices of a trench as the file writes them: [x, y], or [x, y, r] where the editor holds a radius."""
    return [[v[0], v[1]] if v[2] is None else [v[0], v[1], v[2]] for v in path]


def rectangle(low, high) -> np.ndarray:
    return np.array([low, [high[0], low[1]], high, [low[0], high[1]]], dtype=float)


# a vertex this close to its neighbour, or to the line between its neighbours, does nothing (mm)
TIDY_DISTANCE = 0.005


def tidy_path(path: list) -> list:
    """The trench without the interior vertices that repeat a neighbour or lie on the straight line between their neighbours.
    The first and the last vertex stay, because they sit on a terminal or on another trench."""
    path = [list(v) for v in path]
    changed = True
    while changed and len(path) > 2:
        changed = False
        for i in range(1, len(path) - 1):
            a, b, c = (np.array(path[j][:2], dtype=float) for j in (i - 1, i, i + 1))
            if np.linalg.norm(b - a) < TIDY_DISTANCE or np.linalg.norm(c - b) < TIDY_DISTANCE:
                drop = True
            else:
                u, v = b - a, c - b
                drop = float(np.dot(u, v)) > 0 and abs(float(u[0] * v[1] - u[1] * v[0])) / np.linalg.norm(c - a) < TIDY_DISTANCE
            if drop:
                del path[i]
                changed = True
                break
    return path


class Editor:
    def __init__(self, ctx: CaseContext, path: Path = WIRING_FILE):
        self.ctx, self.path = ctx, path
        self.reload()
        self.plates = {side: Plate(ctx, self.plan.diode, side) for side in SIDES}

    def reload(self) -> None:
        self.plan = WiringPlan.load(self.path)

    def plate(self, side: str) -> Plate:
        if side not in SIDES:
            raise EditorError(f"there is no half {side!r}")
        return self.plates[side]

    def power(self, side: str):
        return nets_module.power_nets(self.plate(side))

    # --- what the picture needs

    def geometry(self, side: str) -> dict:
        """The parts of the plate that do not change while the wiring is edited."""
        plate = self.plate(side)
        diode = plate.diode
        return {
            "side": side,
            "outline": r2(plate.keyplate_outline),
            "screws": [r2(p) for p in plate.screws.values()],
            "xiao": {"x": float(plate.xiao.X), "y": float(plate.xiao.Y), "pocket": r2(plate.xiao_pocket), "window": r2(plate.xiao_window)},
            "power": {"body": r2(plate.power.body), "pins": r2(plate.power.pins), "tips": r2(plate.power.tips)},
            "bottom": {k: r2(v) for k, v in plate.bottom_features.items() if not k.startswith("channel")},
            "keys": [{"name": n, "x": float(plate.points[n].p.X), "y": float(plate.points[n].p.Y), "r": float(plate.points[n].r),
                      "cutout": r2(plate.cutouts[n]), "top": r2(plate.top_cutouts[n]),
                      "p1": r2(plate.pin(n, plate.switch.posts.p1)), "p2": r2(plate.pin(n, plate.switch.posts.p2)),
                      "post": r2(plate.pin(n, plate.switch.posts.center))} for n in plate.names],
            "posts": {"p1": plate.switch.posts.p1.d.radius, "p2": plate.switch.posts.p2.d.radius, "post": plate.switch.posts.center.d.radius},
            "diode": {"body_d": diode.body_d, "body_l": diode.body_l, "lead_d": diode.lead_d},
            "diode_y": r2(plate.y_range()),
            "trench_width": plate.profile.trench_width,
            "min_wall": MIN_WALL,
        }

    def notch_data(self, plate: Plate, notches: dict) -> dict:
        diode = plate.diode
        result = {}
        for name, notch in notches.items():
            r = rotation(notch.angle)
            body_end = notch.center + r @ np.array([0, -diode.body_l / 2])
            tip = notch.center + r @ np.array([0, -diode.body_l / 2 - plate.spec.lead_straight])
            result[name] = {
                "side": notch.side, "y": notch.y, "sleeve": plate.needs_sleeve(notch.side), "poly": r2(notch.poly), "center": r2(notch.center), "angle": notch.angle,
                "wall": round(float(notch.wall), 3), "closest": notch.closest,
                "body": r2(rect(notch.center, diode.body_d, diode.body_l, notch.angle)),
                "band": r2(rect(notch.center + r @ np.array([0, diode.body_l / 2 - 0.45]), diode.body_d, 0.7, notch.angle)),
                "lead": r2([body_end, tip, plate.pin(name, plate.switch.posts.p2)]),
            }
        return result

    # --- the file as vertices

    def document(self) -> dict:
        """The file as the editor shows it: the channel, and per half the notches and the vertices of every trench.
        A vertex is [x, y, r]. r is None when the corner has no radius of its own."""
        data = read_file(self.path)
        low, high = data["channel"]
        sides = {}
        for side in SIDES:
            source = data["sides"][side]
            sides[side] = {"notches": {k: list(v) for k, v in source["notches"].items()}}
            for layer in LAYERS:
                sides[side][layer] = {net: [[[v[0], v[1], v[2] if len(v) == 3 else None] for v in path] for path in paths]
                                      for net, paths in source[layer].items()}
        return {"channel": {"low": r2(low), "high": r2(high)}, "sides": sides}

    # --- tidy

    @staticmethod
    def tidy(state: dict) -> tuple[dict, int]:
        """The trenches of one half without vertices that do nothing, and how many were taken away. See `tidy_path`."""
        removed = 0
        out = {}
        for layer in LAYERS:
            out[layer] = {}
            for net, paths in state[layer].items():
                out[layer][net] = []
                for path in paths:
                    tidy = tidy_path(path)
                    removed += len(path) - len(tidy)
                    out[layer][net].append(tidy)
        return out, removed

    # --- the checks

    def half_of(self, side: str, state: dict) -> check.Half:
        """A half from the numbers that the editor holds."""
        plate = self.plate(side)
        places = {k: (int(v[0]), float(v[1])) for k, v in state["notches"].items()}
        if set(places) != set(plate.names):
            raise EditorError("every key needs a notch")
        notches = plate.place(places)
        channel = rectangle(state["channel"]["low"][:2], state["channel"]["high"][:2])

        def paths(source: dict):
            return {net: [normalize(plain(path)) for path in ps]
                    for net, ps in source.items()}

        return check.Half.build(plate, SidePlan(places, paths(state["underside"]), paths(state["top"]), channel), notches)

    def analyze(self, side: str, state: dict, fast: bool = False) -> dict:
        half = self.half_of(side, state)
        plate = half.plate
        power, power_discs = nets_module.power_nets(plate)
        anchors = {name: r2(a.point) for name, a in half.anchors().items() if name.endswith(SNAP_SUFFIXES) or name == "xiao" or name.startswith(("power", "channel"))}
        out = {
            "notches": self.notch_data(plate, half.notches),
            "nets": [{"name": n.name, "color": hex_color(n.color), "terminals": r2(n.terminals), "layer": "underside"} for n in half.nets]
                    + [{"name": n.name, "color": hex_color(n.color), "terminals": r2(n.terminals), "layer": "top"} for n in power],
            "discs": [{"x": float(d.center[0]), "y": float(d.center[1]), "r": d.radius, "owner": d.owner} for d in half.discs + power_discs],
            "anchors": anchors,
        }
        if fast:
            return out
        result = check.check(half)
        out.update({
            "problems": [{"text": str(p), "at": None if p.at is None else r2(p.at), "layer": p.layer} for p in result.problems],
            "walls": {k: {"value": round(float(w), 3), "at": r2(at)} for k, (w, at) in result.walls.items()},
            "trench_length": round(result.trench_length, 1),
        })
        return out

    # --- saving

    def save(self, state: dict) -> dict:
        """Write the file, if what it says is what the editor shows. The old file goes to build/."""
        for side in SIDES:
            self.analyze(side, {**state["sides"][side], "channel": state["channel"]})
        sides = {side: {"notches": {k: (int(v[0]), float(v[1])) for k, v in state["sides"][side]["notches"].items()},
                        **{layer: state["sides"][side][layer] for layer in LAYERS}} for side in SIDES}
        text = export.write_text(export.header(self.path), export.diode_line(self.path), state["channel"], sides)
        with tempfile.TemporaryDirectory() as tmp:
            probe = Path(tmp) / "wiring.yaml"
            probe.write_text(text)
            self.verify(WiringPlan.load(probe), state)
        BUILD_DIR.mkdir(exist_ok=True)
        shutil.copyfile(self.path, BUILD_DIR / f"{self.path.stem}.backup.yaml")
        self.path.write_text(text)
        self.reload()
        return self.document()

    def verify(self, plan: WiringPlan, state: dict) -> None:
        """The text must read back as the vertices that the editor shows."""
        worst = 0.0
        for side in SIDES:
            data = state["sides"][side]
            got = plan.side(side)
            if {k: tuple(v) for k, v in data["notches"].items()} != {k: (v[0], v[1]) for k, v in got.notches.items()}:
                raise EditorError(f"the notches of the {side} half do not survive the file")
            if not np.allclose(got.channel, rectangle(state["channel"]["low"][:2], state["channel"]["high"][:2]), atol=VERIFY_TOLERANCE):
                raise EditorError(f"the channel of the {side} half does not survive the file")
            for layer in LAYERS:
                read = getattr(got, layer)
                for net, paths in data[layer].items():
                    if not paths:
                        continue
                    if len(read.get(net, [])) != len(paths):
                        raise EditorError(f"{side} {layer} {net}: the number of trenches changed")
                    for i, (path, other) in enumerate(zip(paths, read[net])):
                        if len(path) != len(other):
                            raise EditorError(f"{side} {layer} {net} trench {i + 1}: the number of vertices changed")
                        shown = normalize(plain(path))
                        for v, s, w in zip(path, shown, other):
                            worst = max(worst, float(np.hypot(v[0] - w[0], v[1] - w[1])))
                            if abs(s[2] - w[2]) > 0.01:
                                raise EditorError(f"{side} {layer} {net} trench {i + 1}: a radius changed when it was written to the file")
        if worst > VERIFY_TOLERANCE:
            raise EditorError(f"a vertex moved {worst:.3f} mm when it was written to the file. Nothing was saved.")
