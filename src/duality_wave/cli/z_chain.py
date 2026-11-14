"""Draw the Z chain of one key as an SVG and write it to docs/images/z_chain.svg.

Run `task z-chain`. Every height comes from CaseDimensions and the switch model, so the picture follows the code.
Heights are to scale. Widths are schematic.
"""
import argparse
import math
from dataclasses import dataclass
from pathlib import Path

from duality_wave.builders.parts import GROUPS
from duality_wave.cli.common import case_inputs
from duality_wave.models.choc import Choc
from duality_wave.models.model_types import WaveDimensions
from duality_wave.models.rubber_bumper import BumperDimensions
from duality_wave.paths import IMAGE_DIR

CAVITY_HALF_WIDTH = 10.5
CONTACT_X = 5.0
BUMPER_X = -6.5

SX = 22
SZ = 40
WIDTH = 1200
TOP = 100
CENTRE_X = 500
FONT = "Helvetica, Arial, sans-serif"
INK = "#1d1d20"
ACCENT = "#d6336c"
LABEL_X = 835


@dataclass(frozen=True)
class ZChain:
    """The levels of the chain in mm above the table."""

    bumper_dome: float
    bumper_base_top: float
    bed_face: float
    plate_top: float
    keyplate_top: float
    housing_bottom: float
    contact_tip: float
    centre_post_tip: float
    flange_top: float
    upper_housing_top: float
    stem_top: float
    cap_bottom: float
    cap_centre_top: float
    cap_top: float
    wall_top: float

    @classmethod
    def of(cls, switch: Choc, dims: WaveDimensions, bumper: BumperDimensions) -> "ZChain":
        table = -(dims.below_z + bumper.dome_z)

        def above_table(z: float) -> float:
            return round(z - table, 6)

        housing = switch.bottom_housing.d.Z
        upper_housing_top = switch.base.d.Z + switch.upper_housing.d.Z
        return cls(
            bumper_dome=bumper.dome_z,
            bumper_base_top=above_table(-dims.below_z + bumper.base_z),
            bed_face=above_table(-dims.below_z),
            plate_top=above_table(-dims.keyplate_z),
            keyplate_top=above_table(0),
            housing_bottom=above_table(-housing),
            contact_tip=above_table(-(housing + switch.posts.below_length)),
            centre_post_tip=above_table(-(housing + switch.posts.center.d.Z)),
            flange_top=above_table(switch.base.d.Z),
            upper_housing_top=above_table(upper_housing_top),
            stem_top=above_table(upper_housing_top + switch.stem.d.Z),
            cap_bottom=above_table(switch.cap_start_z),
            cap_centre_top=above_table(switch.cap_start_z + switch.cap.dish_low),
            cap_top=above_table(switch.above.d.Z),
            wall_top=above_table(dims.above_z),
        )

    @property
    def case_height(self) -> float:
        return round(self.wall_top - self.bed_face, 6)


def mm(value: float) -> str:
    return f"{value:.1f}"


class Drawing:
    def __init__(self, height_mm: float):
        self.table_y = TOP + height_mm * SZ
        self.height = self.table_y + 70
        self.elements: list[str] = []

    def x(self, x_mm: float) -> float:
        return round(CENTRE_X + x_mm * SX, 2)

    def y(self, above_table: float) -> float:
        return round(self.table_y - above_table * SZ, 2)

    def add(self, element: str) -> None:
        self.elements.append(element)

    def points(self, points: list[tuple[float, float]]) -> str:
        return " ".join(f"{self.x(px)},{self.y(h)}" for px, h in points)

    def block(self, x0: float, x1: float, h0: float, h1: float, fill: str, stroke: str = INK, extra: str = "") -> None:
        self.add(
            f'<rect x="{self.x(x0)}" y="{self.y(h1)}" width="{round((x1 - x0) * SX, 2)}" height="{round((h1 - h0) * SZ, 2)}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="1.2" {extra}/>')

    def polygon(self, points: list[tuple[float, float]], fill: str, stroke: str = INK) -> None:
        self.add(f'<polygon points="{self.points(points)}" fill="{fill}" stroke="{stroke}" stroke-width="1.2" stroke-linejoin="round"/>')

    def line(self, x0: float, y0: float, x1: float, y1: float, extra: str = 'stroke="{ink}" stroke-width="1.2"') -> None:
        self.add(f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y1}" {extra.format(ink=INK)}/>')

    def text(self, x: float, y: float, content: str, size: int = 15, weight: str = "normal", anchor: str = "start",
             fill: str = INK, extra: str = "") -> None:
        self.add(
            f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" fill="{fill}" {extra}>{content}</text>')


def keycap_outline(chain: ZChain, switch: Choc) -> list[tuple[float, float]]:
    cap = switch.cap
    bottom, cavity = cap.d.X / 2, cap.cavity.X / 2
    top = bottom - (chain.cap_top - chain.cap_bottom) * math.tan(math.radians(cap.taper))
    roof = chain.cap_bottom + cap.overlap
    steps = 24
    dish = [
        (top * i / steps, chain.cap_centre_top + (chain.cap_top - chain.cap_centre_top) * (i / steps) ** 2)
        for i in range(steps, -steps - 1, -1)
    ]
    return [(-bottom, chain.cap_bottom), (-cavity, chain.cap_bottom), (-cavity, roof), (cavity, roof), (cavity, chain.cap_bottom),
            (bottom, chain.cap_bottom), *dish]


def bumper_outline(chain: ZChain, bumper: BumperDimensions) -> list[tuple[float, float]]:
    radius, dome = bumper.radius, bumper.dome_z
    sphere = (radius ** 2 + dome ** 2) / (2 * dome)
    steps = 16
    arc = [
        (BUMPER_X + radius * i / steps, sphere - math.sqrt(sphere ** 2 - (radius * i / steps) ** 2))
        for i in range(-steps, steps + 1)
    ]
    return [(BUMPER_X - radius, chain.bumper_base_top), (BUMPER_X - radius, chain.bed_face), *arc,
            (BUMPER_X + radius, chain.bed_face), (BUMPER_X + radius, chain.bumper_base_top)]


def colour(group: str) -> str:
    return GROUPS[group].color


def draw_parts(d: Drawing, chain: ZChain, switch: Choc, dims: WaveDimensions, bumper: BumperDimensions) -> None:
    wall = dims.wall_thickness
    housing_half = switch.bottom_housing.d.X / 2
    post_gap = dims.print_profile.post_clearance
    centre = switch.posts.center.d.radius
    centre_hole = centre + post_gap
    contact = switch.posts.p1.d.radius
    plate_colour, wall_colour = colour("bottom"), colour("keywell")

    d.block(-CAVITY_HALF_WIDTH - wall, -CAVITY_HALF_WIDTH, chain.bed_face, chain.wall_top, wall_colour)
    d.block(CAVITY_HALF_WIDTH, CAVITY_HALF_WIDTH + wall, chain.bed_face, chain.wall_top, wall_colour)

    d.block(-CAVITY_HALF_WIDTH, CAVITY_HALF_WIDTH, chain.bed_face, chain.plate_top, plate_colour)
    d.block(-centre_hole, centre_hole, chain.bed_face, chain.plate_top, "#ffffff", extra='stroke-dasharray="3 2"')
    d.block(CONTACT_X - contact - post_gap, CONTACT_X + contact + post_gap, chain.contact_tip, chain.plate_top, "#ffffff", extra='stroke-dasharray="3 2"')
    d.block(BUMPER_X - bumper.radius - dims.print_profile.bumper_clearance, BUMPER_X + bumper.radius + dims.print_profile.bumper_clearance,
            chain.bed_face, chain.bumper_base_top, "#ffffff", extra='stroke-dasharray="3 2"')
    d.polygon(bumper_outline(chain, bumper), colour("bumpers"))

    keyplate_colour = colour("keyplate")
    clear = housing_half + 0.1
    d.block(clear, CAVITY_HALF_WIDTH, chain.plate_top, chain.keyplate_top, keyplate_colour)
    d.block(-CAVITY_HALF_WIDTH, -clear, chain.plate_top, chain.keyplate_top, keyplate_colour)

    lower, upper = "#26262b", "#4b4b54"
    d.block(-centre, centre, chain.centre_post_tip, chain.housing_bottom, lower)
    d.block(CONTACT_X - contact, CONTACT_X + contact, chain.contact_tip, chain.housing_bottom, "#d9923a")
    d.block(-housing_half, housing_half, chain.housing_bottom, chain.keyplate_top, lower)
    d.block(-switch.base.d.X / 2, switch.base.d.X / 2, chain.keyplate_top, chain.flange_top, upper)
    d.block(-switch.upper_housing.d.X / 2, switch.upper_housing.d.X / 2, chain.flange_top, chain.upper_housing_top, upper)
    d.block(-switch.stem.d.X / 2, switch.stem.d.X / 2, chain.upper_housing_top, chain.stem_top, upper)
    d.polygon(keycap_outline(chain, switch), colour("keycaps"))


def draw_table(d: Drawing) -> None:
    left, right = d.x(-17.5), d.x(CAVITY_HALF_WIDTH + 2.0)
    d.add(
        '<defs><pattern id="hatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
        '<line x1="0" y1="0" x2="0" y2="8" stroke="#b9b9be" stroke-width="1.5"/></pattern>'
        '<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto-start-reverse">'
        f'<path d="M0,0 L10,5 L0,10 z" fill="{ACCENT}"/></marker></defs>')
    d.add(f'<rect x="{left}" y="{d.table_y}" width="{right - left}" height="16" fill="url(#hatch)" stroke="{INK}" stroke-width="1.2"/>')
    d.text(left + 10, d.table_y + 34, "Table", size=14, fill="#55555c", extra='font-style="italic"')


def draw_dimensions(d: Drawing, chain: ZChain) -> None:
    left_edge = d.x(-CAVITY_HALF_WIDTH - 1.8)
    cap_corner = d.x(-8.4)
    guide = f'stroke="{ACCENT}" stroke-width="1" stroke-dasharray="5 4"'

    for level in (chain.bed_face, chain.plate_top, chain.keyplate_top):
        y = d.y(level)
        d.line(left_edge - 26, y, left_edge, y, extra='stroke="#77777e" stroke-width="1"')
        d.text(left_edge - 32, y - 5, mm(level), size=13, anchor="end", fill="#55555c")

    table_bracket, case_bracket = 55, 125
    d.line(table_bracket, d.y(chain.cap_top), cap_corner, d.y(chain.cap_top), extra=guide)
    d.line(case_bracket, d.y(chain.wall_top), left_edge, d.y(chain.wall_top), extra=guide)
    d.line(case_bracket, d.y(chain.bed_face), left_edge, d.y(chain.bed_face), extra=guide)
    d.line(table_bracket, d.table_y, left_edge, d.table_y, extra=guide)

    for x, low, high, title, value in (
        (table_bracket, 0.0, chain.cap_top, "Table to keycap top", chain.cap_top),
        (case_bracket, chain.bed_face, chain.wall_top, "Bottom plate to top of keywell", chain.case_height),
    ):
        d.line(x, d.y(low), x, d.y(high), extra=f'stroke="{ACCENT}" stroke-width="2.2" marker-start="url(#arrow)" marker-end="url(#arrow)"')
        middle = (d.y(low) + d.y(high)) / 2
        d.text(x - 12, middle, f"{title}: {mm(value)} mm", size=17, weight="bold", anchor="middle", fill=ACCENT,
               extra=f'transform="rotate(-90 {x - 12} {middle})"')


def draw_callouts(d: Drawing, chain: ZChain, switch: Choc, dims: WaveDimensions, bumper: BumperDimensions) -> None:
    housing = switch.bottom_housing.d.Z
    callouts = [
        ("Top of the keywell wall", f"{mm(dims.above_z - switch.above.d.Z)} mm above the keycaps", 100,
         [(CAVITY_HALF_WIDTH + 0.9, chain.wall_top)]),
        ("Keycap", f"{mm(switch.cap.d.Z)} mm", 168, [(8.5, chain.cap_top - 1.5)]),
        ("Switch, upper part", f"{mm(chain.stem_top - chain.keyplate_top)} mm: flange, housing, stem", 340,
         [(switch.upper_housing.d.X / 2, (chain.flange_top + chain.upper_housing_top) / 2)]),
        ("Keyplate", f"{mm(chain.keyplate_top - chain.plate_top)} mm", 440, [(9.0, chain.keyplate_top - 0.9)]),
        ("Switch, lower part", f"housing {mm(housing)} mm, contacts cut to {mm(switch.posts.below_length)} mm", 520,
         [(switch.bottom_housing.d.X / 2 - 0.6, chain.keyplate_top - 1.2), (CONTACT_X, (chain.contact_tip + chain.housing_bottom) / 2)]),
        ("Bottom plate", f"{mm(chain.plate_top - chain.bed_face)} mm", 612, [(9.0, (chain.plate_top + chain.bed_face) / 2)]),
        ("Rubber bumper", f"{mm(bumper.dome_z)} mm stand-off", d.table_y - 8, [(BUMPER_X, chain.bumper_dome / 2)]),
    ]
    for title, subtitle, label_y, targets in callouts:
        d.text(LABEL_X, label_y + 5, title, size=17, weight="bold")
        d.text(LABEL_X, label_y + 23, subtitle, size=13, fill="#55555c")
        for x_mm, h in targets:
            tx, ty = d.x(x_mm), d.y(h)
            d.line(LABEL_X - 10, label_y, tx, ty, extra=f'stroke="{INK}" stroke-width="1.3"')
            d.add(f'<circle cx="{tx}" cy="{ty}" r="3.6" fill="{INK}" stroke="#ffffff" stroke-width="1.2"/>')


def render_svg(switch: Choc, dims: WaveDimensions, bumper: BumperDimensions) -> str:
    chain = ZChain.of(switch, dims, bumper)
    d = Drawing(chain.wall_top)
    d.add(f'<rect width="{WIDTH}" height="{d.height}" fill="#ffffff"/>')
    draw_table(d)
    draw_dimensions(d, chain)
    draw_parts(d, chain, switch, dims, bumper)
    draw_callouts(d, chain, switch, dims, bumper)
    d.text(40, 42, "The Z chain of one key", size=24, weight="bold")
    d.text(40, d.height - 18, "Section through one key. Heights are to scale, widths are schematic.", size=13, fill="#77777e")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{d.height}" viewBox="0 0 {WIDTH} {d.height}">'
        + "\n".join(d.elements) + "</svg>\n")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="z-chain", description=__doc__.splitlines()[0])
    parser.add_argument("out", nargs="?", default=str(IMAGE_DIR / "z_chain.svg"), help="the SVG file to write")
    out = Path(parser.parse_args(argv).out)
    switch, _, _, dims = case_inputs()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_svg(switch, dims, BumperDimensions()))
    print(out)
