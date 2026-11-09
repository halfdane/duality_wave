"""The nets of the matrix and of the power switch: where their terminals are and which keep-outs they have.

The matrix has one net per column and one per row. The thumb keys form one extra row. A thumb takes the column of the nearest
matrix column that no other thumb has. A column net joins the contacts p1 of its switches. A row net joins the cathode ends of
the diodes. The anode lead of a diode is not wired: it runs inside the notch and the cutout of its key to the contact p2.
"""

from dataclasses import dataclass, field
from itertools import permutations

import numpy as np

from duality_wave.wiring.geometry import rotation
from duality_wave.wiring.plate import Notch, Plate
from duality_wave.wiring.rounded import Vertex

# keys named thumb_* form one extra row
THUMB_PREFIX = "thumb"
# keep-out radii: the hole around the centre post (post + clearance), a solder blob on a contact, the end of a lead
CENTRE_POST_KEEPOUT = 1.0
CONTACT_KEEPOUT = 0.8
TIP_KEEPOUT = 0.5
# the radius of the wire itself
WIRE_RADIUS = 0.15
# the two pins of the power switch that carry wires: the two with the lowest Y in the top row of pins
POWER_PINS = 2

COLUMN_COLORS = [(230, 40, 40), (255, 150, 40), (70, 130, 255), (120, 70, 30), (200, 160, 255), (60, 200, 200), (255, 90, 200)]
ROW_COLORS = [(20, 200, 80), (0, 130, 60), (130, 235, 160), (0, 90, 45), (150, 200, 40), (40, 160, 120)]
POWER_COLORS = [(255, 60, 60), (60, 60, 60)]


@dataclass
class Net:
    name: str
    color: tuple[int, int, int]
    terminals: list[np.ndarray]
    paths: list[list[Vertex]] = field(default_factory=list)


@dataclass(frozen=True)
class Disc:
    """A round keep-out. A disc with an owner is free for the net of that name. A disc without owner is closed for all nets."""

    center: np.ndarray
    radius: float
    owner: str | None = None


def key_layout(plate: Plate) -> tuple[dict[str, tuple[int, int]], list[str], int]:
    """Column and row of every key, the names of the columns and the number of matrix rows.

    Columns count from the left of the underside picture (high X), matrix rows from the top (high Y).
    The thumb keys are row number `rows`."""
    matrix = {n: n.split("_")[1:] for n in plate.names if not n.startswith(THUMB_PREFIX)}
    thumbs = [n for n in plate.names if n.startswith(THUMB_PREFIX)]

    def mean(names: list[str], axis: int) -> float:
        return float(np.mean([(plate.points[n].p.X, plate.points[n].p.Y)[axis] for n in names]))

    columns = sorted({c for c, _ in matrix.values()}, key=lambda c: -mean([n for n, v in matrix.items() if v[0] == c], 0))
    rows = sorted({r for _, r in matrix.values()}, key=lambda r: -mean([n for n, v in matrix.items() if v[1] == r], 1))
    layout = {n: (columns.index(c), rows.index(r)) for n, (c, r) in matrix.items()}
    column_x = [mean([n for n, v in matrix.items() if v[0] == c], 0) for c in columns]
    # the columns for the thumbs that put them closest to their columns in total
    best = min(permutations(range(len(columns)), len(thumbs)),
               key=lambda cs: sum(abs(plate.points[t].p.X - column_x[c]) for t, c in zip(thumbs, cs)))
    for t, c in zip(thumbs, best):
        layout[t] = (c, len(rows))
    return layout, columns, len(rows)


def lead_tip(plate: Plate, notch: Notch) -> np.ndarray:
    """Where the cathode lead enters the wire: just inside the end of the notch."""
    return notch.center + rotation(notch.angle) @ np.array([0, plate.spec.length / 2 - 0.1])


def matrix_nets(plate: Plate, notches: dict[str, Notch]) -> tuple[list[Net], list[Disc]]:
    """The nets of the matrix, and the keep-out discs around the contacts, the posts and the lead tips."""
    posts = plate.switch.posts
    layout, _, n_rows = key_layout(plate)
    n_columns = max(c for c, _ in layout.values()) + 1
    nets: list[Net] = []
    discs: list[Disc] = []
    for column in range(n_columns):
        name = f"col {column + 1}"
        names = [n for n in plate.names if layout[n][0] == column]
        nets.append(Net(name, COLUMN_COLORS[column % len(COLUMN_COLORS)], [plate.pin(n, posts.p1) for n in names]))
        discs += [Disc(plate.pin(n, posts.p1), CONTACT_KEEPOUT, name) for n in names]
    # the thumb keys are the last row
    for row in range(n_rows + 1):
        name = f"row {row + 1}"
        tips = [lead_tip(plate, notches[n]) for n in plate.names if layout[n][1] == row]
        nets.append(Net(name, ROW_COLORS[row % len(ROW_COLORS)], tips))
        discs += [Disc(t, TIP_KEEPOUT, name) for t in tips]
    for name in plate.names:
        discs.append(Disc(plate.pin(name, posts.p2), CONTACT_KEEPOUT))
        discs.append(Disc(plate.pin(name, posts.center), CENTRE_POST_KEEPOUT))
    return nets, discs


def power_nets(plate: Plate) -> tuple[list[Net], list[Disc]]:
    """The nets of the two power wires: from the pins of the power switch towards the XIAO. The battery is wired by hand."""
    tips = plate.power.tips
    nets = [Net(f"power {i + 1}", POWER_COLORS[i % len(POWER_COLORS)], [tips[i]]) for i in range(POWER_PINS)]
    # the pins that carry no wire stay free of trenches
    discs = [Disc(t, CONTACT_KEEPOUT) for t in tips[POWER_PINS:]]
    return nets, discs
