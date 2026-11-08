"""The groups of parts that the views show: how each group looks and where it sits in the exploded view."""
import colorsys
from dataclasses import dataclass

from build123d import Shape

from duality_wave.builders.side import BuiltSide


@dataclass(frozen=True)
class PartGroup:
    name: str
    color: str  # sRGB hex of the left half
    metallic: bool = False
    # the layer in the exploded view, in steps. Layer 0 stays in place and each step moves a layer down.
    level: float = 0.0


GROUPS: dict[str, PartGroup] = {group.name: group for group in (
    PartGroup("keywell", "#307390", level=0),
    PartGroup("magnets", "#ededf1", metallic=True, level=0.5),
    PartGroup("spacers", "#7d9bb0", level=0.5),
    PartGroup("inserts", "#b08d57", metallic=True, level=0.5),
    PartGroup("battery", "#8e6fb0", level=0.5),
    PartGroup("keyplate", "#e1bc59", level=1),
    PartGroup("switches", "#303035", level=1),
    PartGroup("keycaps", "#bcbdc2", level=1),
    PartGroup("xiao", "#275945", level=1),
    PartGroup("usb", "#ededf1", metallic=True, level=1),
    PartGroup("power_switch", "#b9b9bd", level=1.5),
    PartGroup("bottom", "#595d61", level=2),
    PartGroup("screws", "#9aa0a6", metallic=True, level=3),
    PartGroup("bumpers", "#202020", level=3),
)}

# how far the lightness of the right half differs from the left half
SIDE_TINT = 0.07


def colour(group: str, side: str) -> str:
    """The sRGB hex colour of a group on a side. The right half has the hue of the left half and a little more or less lightness."""
    base = GROUPS[group].color
    if side == "left":
        return base
    red, green, blue = (int(base[i:i + 2], 16) / 255 for i in (1, 3, 5))
    hue, lightness, saturation = colorsys.rgb_to_hls(red, green, blue)
    lightness += -SIDE_TINT if lightness > 0.5 else SIDE_TINT
    return "#" + "".join(f"{round(c * 255):02x}" for c in colorsys.hls_to_rgb(hue, lightness, saturation))


def side_parts(built: BuiltSide) -> dict[str, Shape]:
    """Every part group of one half by name. Groups that the half does not have are left out.

    The accessories exist only when the case was built with a viewer that shows them.
    """
    if built.accessories is None:
        raise ValueError("The case was built without accessories. Build it with a viewer that is enabled.")
    fixtures = built.accessories.fixtures
    parts = {
        "keywell": built.keywell,
        "keyplate": built.keyplate,
        "bottom": built.bottom,
        "switches": built.accessories.switches,
        "keycaps": built.accessories.keycaps,
        "xiao": built.xiao.model - built.xiao.usb_connector,
        "usb": built.xiao.usb_connector,
        "battery": fixtures.battery,
        "power_switch": fixtures.power_switch,
        "magnets": fixtures.magnets,
        "spacers": fixtures.spacers,
        "inserts": fixtures.inserts,
        "screws": fixtures.screws,
        "bumpers": fixtures.bumpers,
    }
    return {name: shape for name, shape in parts.items() if shape is not None}
