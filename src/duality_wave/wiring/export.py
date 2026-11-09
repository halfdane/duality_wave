"""Writes the wiring file from the vertices that a person placed in the editor.

The file holds plain coordinates (duality_wave.wiring.plan). A vertex is [x, y], or [x, y, r] when the corner has a radius of its own.
"""

from pathlib import Path

from duality_wave.wiring.plan import LAYERS

DECIMALS = 3


def num(v: float) -> str:
    text = f"{v:.{DECIMALS}f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def vertex(v) -> str:
    """One vertex as [x, y] or [x, y, r]. A radius of None is left out."""
    return "[" + ", ".join(num(c) for c in v if c is not None) + "]"


def header(path: Path) -> str:
    """The comment at the top of the file, which the editor keeps."""
    lines = []
    for line in path.read_text().splitlines():
        if not line.startswith("#"):
            break
        lines.append(line)
    return "\n".join(lines)


def diode_line(path: Path) -> str:
    """The line of the file that describes the diode, which the editor does not change."""
    return next(line for line in path.read_text().splitlines() if line.startswith("diode:"))


def write_text(head: str, diode: str, channel: dict, sides: dict[str, dict]) -> str:
    """The file as text. channel is {low, high}. sides maps a half to {notches, underside, top}, with vertices [x, y, r or None]."""
    out = [head, ""] if head else []
    out += [diode, ""]
    out += ["# One wide recess in the underside of the keyplate, from two opposite corners.",
            "# It starts at the inner column, runs along the top edge, and opens into the pocket of the XIAO. The wires of all nets lie in it.",
            "channel:", f"  from: {vertex(channel['low'][:2])}", f"  to: {vertex(channel['high'][:2])}", ""]
    for name, data in sides.items():
        out.append(f"{name}:")
        out.append("  notches:")
        out += [f"    {key}: {{side: {side}, y: {num(y)}}}" for key, (side, y) in data["notches"].items()]
        for layer in LAYERS:
            out.append(f"  {layer}:")
            for net, paths in data[layer].items():
                if not paths:
                    continue
                out.append(f"    {net}:")
                for path in paths:
                    out.append("      - [" + ",\n         ".join(vertex(v) for v in path) + "]")
        out.append("")
    return "\n".join(out).rstrip("\n") + "\n"
