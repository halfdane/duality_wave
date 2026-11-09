"""Named points of the plate: the places the wiring editor snaps to.

The names are `<key>`, `<key>.p1` (contact of the column), `<key>.p2`, `<key>.post` (centre post),
`<key>.cathode` (where the row wire meets the diode), `xiao`, `power.pin1` and `power.pin2`.
The wiring file itself holds plain coordinates (duality_wave.wiring.plan).
"""

from dataclasses import dataclass

import numpy as np

from duality_wave.wiring import nets as nets_module
from duality_wave.wiring.plate import Notch, Plate


@dataclass(frozen=True)
class Anchor:
    point: np.ndarray
    # rotation of the key the point belongs to
    angle: float = 0.0


def named_points(plate: Plate, notches: dict[str, Notch]) -> dict[str, Anchor]:
    """Every named point of the plate."""
    posts = plate.switch.posts
    result: dict[str, Anchor] = {}
    for name in plate.names:
        key = plate.points[name]
        result[name] = Anchor(np.array([key.p.X, key.p.Y]), key.r)
        result[f"{name}.p1"] = Anchor(plate.pin(name, posts.p1), key.r)
        result[f"{name}.p2"] = Anchor(plate.pin(name, posts.p2), key.r)
        result[f"{name}.post"] = Anchor(plate.pin(name, posts.center), key.r)
        result[f"{name}.cathode"] = Anchor(nets_module.lead_tip(plate, notches[name]), key.r)
    result["xiao"] = Anchor(np.array([plate.xiao.X, plate.xiao.Y]))
    for i, tip in enumerate(plate.power.tips[:nets_module.POWER_PINS]):
        result[f"power.pin{i + 1}"] = Anchor(tip)
    return result
