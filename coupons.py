"""Calibration coupons for the fit constants in models/print_profile.py.

Every coupon answers one question and is modelled in its real print orientation, so elephant
foot and bridging behave like they will on the case. Print them all on one plate with the same
settings as the final case, then copy the winning values into the PrintProfile.

  A  switch plate     switch cutout size, with and without corner relief
  B  plate in cavity  plate clearance (try each plate both ways round)
  C  round holes      magnet recess size and heat-set insert pilot size
  D  pockets          weight pocket clearance and the battery pocket

Run `task coupons` to export coupons.stl.
"""
from dataclasses import replace

from build123d import *
from build123d import Shape

from models.choc import Choc
from models.features import magnet_recess_cutter, switch_cutter
from models.model_types import RectDimensions, RoundDimensions
from models.print_profile import PrintProfile
from models.switch import Switch

LABEL_DEPTH = 0.4
LABEL_SIZE = 2.2
CORNER_RADIUS = 1.0


def to_bed(shape: Shape, face_z: float) -> Shape:
    """Flip a shape modelled like the case (y up, bed-side face at face_z) into its print frame."""
    return shape.rotate(Axis.X, 180).translate((0, 0, face_z))


def engrave(part: Shape, top_z: float, labels: list[tuple[str, float, float]], size: float = LABEL_SIZE) -> Part:
    with BuildPart() as engraved:
        add(part)
        with BuildSketch(Plane.XY.offset(top_z)):
            for text, x, y in labels:
                with Locations((x, y)):
                    Text(text, font_size=size)
        extrude(amount=-LABEL_DEPTH, mode=Mode.SUBTRACT)
    return engraved.part


def chamfered_plate(width: float, height: float, thickness: float, profile: PrintProfile) -> Part:
    """Rounded plate with its bed face at z=0, chamfered like the keyplate and bottom plate."""
    with BuildPart() as plate:
        with BuildSketch():
            with Locations((width / 2, height / 2)):
                RectangleRounded(width, height, CORNER_RADIUS)
        extrude(amount=thickness)
        plate_faces = faces().filter_by(Axis.Z).sort_by(Axis.Z)
        chamfer(objects=plate_faces[0].edges(), length=profile.plate_bed_chamfer)
        chamfer(objects=plate_faces[-1].edges(), length=profile.plate_edge_chamfer)
    return plate.part


def switch_plate_coupon(
    switch: Switch,
    profile: PrintProfile,
    plate_z: float,
    sizes: tuple[float, ...] = (13.8, 13.9, 14.0, 14.1),
    reliefs: tuple[float, ...] = (0.0, 0.3),
    pitch: float = 18.0,
    margin: float = 8.0,
) -> Part:
    """A: switch cutouts of different sizes (columns) with different corner reliefs (rows)."""
    width = len(sizes) * pitch + margin
    height = len(reliefs) * pitch + margin

    with BuildPart() as coupon:
        add(chamfered_plate(width, height, plate_z, profile))
        for column, size in enumerate(sizes):
            for row, relief in enumerate(reliefs):
                hole = replace(
                    profile,
                    switch_clearance=(size - switch.below.d.X) / 2,
                    switch_corner_relief=relief,
                )
                x = margin + pitch * (column + 0.5)
                y = margin + pitch * (row + 0.5)
                # the cutter is modelled like the keyplate, so y is mirrored by the flip
                cutter = switch_cutter(switch, hole, [Location((x, -y))], plate_z)
                add(to_bed(cutter, 0), mode=Mode.SUBTRACT)

    labels = [(f"{size:.2f}", margin + pitch * (column + 0.5), margin / 2) for column, size in enumerate(sizes)]
    labels += [(f"R{relief:g}", margin / 2, margin + pitch * (row + 0.5)) for row, relief in enumerate(reliefs)]
    return engrave(coupon.part, plate_z, labels, size=2.0)


def plate_fit_coupon(
    profile: PrintProfile,
    plate_z: float,
    wall_thickness: float,
    clearances: tuple[float, ...] = (0.0, 0.05, 0.10, 0.15, 0.20),
    inner: tuple[float, float] = (36.0, 26.0),
) -> tuple[Part, list[Part]]:
    """B: a cavity like the keywell's and plates with different clearances.

    The cavity is exactly as deep as the plates are thick, so a plate sits flush like the bottom
    plate. The same plate can be inserted either way round to feel the chamfered and the plain edge.
    """
    inner_width, inner_height = inner
    ceiling = wall_thickness
    with BuildPart() as cavity:
        with BuildSketch():
            RectangleRounded(inner_width + 2 * wall_thickness, inner_height + 2 * wall_thickness, CORNER_RADIUS + wall_thickness)
        extrude(amount=ceiling + plate_z)
        with BuildSketch(Plane.XY.offset(ceiling)):
            RectangleRounded(inner_width, inner_height, CORNER_RADIUS)
        extrude(amount=plate_z, mode=Mode.SUBTRACT)

    plates = []
    for clearance in clearances:
        width = inner_width - 2 * clearance
        height = inner_height - 2 * clearance
        plate = chamfered_plate(width, height, plate_z, profile)
        with BuildPart() as pushable:
            add(plate)
            with BuildSketch():
                with Locations((width / 2, height / 2)):
                    Circle(3)
            extrude(amount=plate_z, mode=Mode.SUBTRACT)
        plates.append(engrave(pushable.part, plate_z, [(f"{clearance:.2f}", width / 2, height - 4)], size=3))
    return cavity.part, plates


def round_hole_coupon(
    profile: PrintProfile,
    magnet: RoundDimensions,
    block_z: float,
    pilot_depth: float,
    magnet_clearances: tuple[float, ...] = (0.0, 0.05, 0.10, 0.15, 0.20),
    pilot_diameters: tuple[float, ...] = (2.9, 3.0, 3.1, 3.2, 3.3),
    pitch: float = 9.5,
    margin: float = 5.5,
) -> Part:
    """C: magnet recesses open towards the bed, heat-set insert pilots open upwards."""
    count = max(len(magnet_clearances), len(pilot_diameters))
    width = (count - 1) * pitch + 2 * margin
    pilot_y, magnet_y, height = 6.0, 19.0, 26.0

    with BuildPart() as coupon:
        with BuildSketch():
            with Locations((width / 2, height / 2)):
                RectangleRounded(width, height, CORNER_RADIUS)
        extrude(amount=block_z)

        for index, clearance in enumerate(magnet_clearances):
            x = margin + index * pitch
            cutter = magnet_recess_cutter(magnet, replace(profile, magnet_clearance=clearance), [Vector(x, -magnet_y)], top_z=block_z)
            add(to_bed(cutter, block_z), mode=Mode.SUBTRACT)

        for index, diameter in enumerate(pilot_diameters):
            x = margin + index * pitch
            with BuildPart(Plane.XY.offset(block_z - pilot_depth), mode=Mode.SUBTRACT):
                with Locations((x, pilot_y)):
                    Cylinder(diameter / 2, pilot_depth, align=(Align.CENTER, Align.CENTER, Align.MIN))

    labels = [(f"{2 * (magnet.radius + c):.2f}", margin + index * pitch, magnet_y) for index, c in enumerate(magnet_clearances)]
    labels += [(f"{d:.1f}", margin + index * pitch, pilot_y + 5.5) for index, d in enumerate(pilot_diameters)]
    return engrave(coupon.part, block_z, labels, size=2.0)


def pocket_coupon(
    profile: PrintProfile,
    weight: Vector,
    battery: RectDimensions,
    clearances: tuple[float, ...] = (0.05, 0.15, 0.25),
    depth: float = 2.0,
    thickness: float = 3.0,
    margin: float = 3.0,
) -> Part:
    """D: pockets open upwards, one per weight clearance plus the battery pocket at the profile clearance."""
    row = weight.Y + 2 * margin + 1.5
    width = max(weight.X, battery.X) + 2 * margin + 1
    battery_height = battery.Y + 2 * margin
    height = len(clearances) * row + battery_height

    pockets = [(weight.X + 2 * c, weight.Y + 2 * c, f"{c:.2f}") for c in clearances]
    pockets.append((battery.X + 2 * profile.battery_clearance, battery.Y + 2 * profile.battery_clearance, "battery"))

    labels = []
    with BuildPart() as coupon:
        with BuildSketch():
            with Locations((width / 2, height / 2)):
                RectangleRounded(width, height, CORNER_RADIUS)
        extrude(amount=thickness)
        y = margin
        for pocket_x, pocket_y, label in pockets:
            labels.append((label, width / 2, y + pocket_y + 1.2))
            with BuildSketch(Plane.XY.offset(thickness)):
                with Locations((width / 2, y + pocket_y / 2)):
                    Rectangle(pocket_x, pocket_y)
            extrude(amount=-depth, mode=Mode.SUBTRACT)
            y += pocket_y + margin + 1.5
    return engrave(coupon.part, thickness, labels, size=1.8)


def arrange(parts: list[Shape], max_width: float = 240.0, gap: float = 6.0) -> Compound:
    """Lay the parts out in rows on one print bed."""
    x = y = row_height = 0.0
    placed = []
    for part in parts:
        box = part.bounding_box()
        if x > 0 and x + box.size.X > max_width:
            x, y, row_height = 0.0, y + row_height + gap, 0.0
        placed.append(part.translate((x - box.min.X, y - box.min.Y, -box.min.Z)))
        x += box.size.X + gap
        row_height = max(row_height, box.size.Y)
    return Compound(placed)


def create_coupons(switch: Switch, dims, profile: PrintProfile | None = None) -> Compound:
    profile = profile or dims.print_profile
    cavity, plates = plate_fit_coupon(profile, dims.keyplate_z, dims.wall_thickness)
    return arrange([
        switch_plate_coupon(switch, profile, dims.keyplate_z),
        cavity,
        *plates,
        round_hole_coupon(profile, dims.magnet_d, dims.above_z, dims.heat_insert_z),
        pocket_coupon(profile, dims.weight_d, dims.battery_pd.d),
    ])


if __name__ == "__main__":
    import os

    from duality_wave import CaseDimensions
    from models.keys import ErgoKeys, get_points
    from models.outline import Outline

    switch = Choc()
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ergogen", "wave.yml")
    keys = ErgoKeys(points=get_points(file_path=config_path))
    outline = Outline(switch=switch, keys=keys, wall_thickness=CaseDimensions.wall_thickness)
    dims = CaseDimensions(switch=switch, outline=outline, keys=keys)

    coupons = create_coupons(switch, dims)
    size = coupons.bounding_box().size
    print(f"coupons.stl: {len(coupons.solids())} parts, {size.X:.0f} x {size.Y:.0f} x {size.Z:.1f} mm")
    export_stl(coupons, "coupons.stl")
