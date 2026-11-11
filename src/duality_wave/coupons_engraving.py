"""Calibration coupons for the emblems in the outer wall (builders/wall_engraving.py).

Each coupon is a slab of the front wall: as tall as the keywell wall, as thick as the wall, with the emblems
at the height they have in the keywell. The slab stands on its rim and the pockets face sideways, like on the
case. A low foot on the engraved side keeps the slab upright and carries the labels.
The emblems are upside down on the plate. The keywell prints upside down too.

One slab for each combination of pocket depth and roof. On a slab:

  three space invaders   pixel gap 0, half a line, one line (the label is the gap in mm)
  one symbol             the label is the depth in mm and the roof (45 = sloped, flat = straight)

Print the plate with the settings of the final case. Choose the smallest depth that stays legible and the
roof and gap that print cleanly. Then set engraving_lines, engraving_roof_slope and the pitch in the PrintProfile.

The slabs share the plate of the wiring coupons (see coupons.create_wiring_coupon_parts).
Run `task export-coupon` to write build/coupons/coupons_plate_wiring_engraving.stl and `task view -- coupons-plate-wiring-engraving` to look at the plate in the OCP viewer.
"""
from dataclasses import replace

from build123d import *
from build123d import Shape

from duality_wave.builders.wall_engraving import (
    WallSpot, emblem_sketch, emblem_z, engrave_wall)
from duality_wave.coupons import LABEL_DEPTH, to_bed
from duality_wave.print_profile import PrintProfile
from duality_wave.models.space_invader import SpaceInvader

MARGIN = 3.0
FOOT_DEPTH = 6.0
LABEL_SIZE = 1.8


def gap_sweep(profile: PrintProfile) -> tuple[float, ...]:
    """No gap, half a line and one line."""
    return (0.0, profile.line_width / 2, profile.engraving_gap)


def wall_engraving_coupon(
    dims,
    profile: PrintProfile,
    lines: int,
    roof_slope: bool,
    gaps: tuple[float, ...] | None = None,
) -> Part:
    """A wall slab with one invader for each gap and one symbol, engraved lines lines deep.

    The slab lies along x with its engraved face at y = 0, facing +y, and its bed face at z = 0.
    The foot lies on the engraved side. The labels are readable from the front, from above.
    """
    gaps = gap_sweep(profile) if gaps is None else gaps
    profile = replace(profile, engraving_lines=lines, engraving_roof_slope=roof_slope)
    thickness = dims.wall_thickness
    height = dims.above_z + dims.below_z
    pitch = profile.snap_up(profile.engraving_pitch)
    invader_width = SpaceInvader.columns * pitch
    cell = invader_width + 3.0
    cells = len(gaps) + 1
    width = cells * cell + 2 * MARGIN - 3.0

    # modelled like the keywell wall: y points into the case, z up, and the bed face at the top
    slab = Box(width, thickness, height, align=(Align.MIN, Align.MIN, Align.MIN))
    z = emblem_z(dims) + dims.below_z
    emblems = [(f"{gap:g}", SpaceInvader(pitch, gap).sketch) for gap in gaps]
    emblems.append((f"{profile.engraving_depth:g} {'45' if roof_slope else 'flat'}", emblem_sketch("symbol", profile)))
    labels = []
    for index, (text, sketch) in enumerate(emblems):
        x = MARGIN + invader_width / 2 + cell * index
        spot = WallSpot(Vector(x, 0, 0), Vector(0, -1, 0))
        slab = engrave_wall(slab, spot.plane(z), sketch, profile.engraving_depth, roof_slope)
        labels.append((text, x))

    foot_z = profile.snap_up(1.2)
    with BuildPart() as coupon:
        insert(to_bed(slab, height))
        with BuildPart(mode=Mode.ADD):
            with Locations((0, -thickness / 2)):
                Box(width, thickness / 2 + FOOT_DEPTH, foot_z, align=(Align.MIN, Align.MIN, Align.MIN))
        with BuildSketch(Plane.XY.offset(foot_z)):
            for text, x in labels:
                with Locations(Location((x, FOOT_DEPTH / 2, 0), (0, 0, 180))):
                    Text(text, font_size=LABEL_SIZE)
        extrude(amount=-LABEL_DEPTH, mode=Mode.SUBTRACT)
    return coupon.part


def engraving_coupon_slabs(dims, profile: PrintProfile | None = None) -> dict[str, Shape]:
    """One slab for each depth (1 and 2 lines) and roof (sloped and straight), not yet arranged on a print bed."""
    profile = profile or dims.print_profile
    parts = {}
    for lines in (1, 2):
        for roof_slope in (True, False):
            name = f"{lines * profile.line_width:g} mm, {'sloped' if roof_slope else 'straight'} roof"
            parts[name] = wall_engraving_coupon(dims, profile, lines, roof_slope)
    return parts
