"""Calibration coupons for the fit constants in models/print_profile.py.

Every coupon answers one question and is modelled in its real print orientation, so elephant
foot and bridging behave like they will on the case. Print them all on one plate with the same
settings as the final case, then copy the winning values into the PrintProfile.

  A  switch plate     switch cutout size, with and without corner relief
  B  plate in cavity  plate clearance (try each plate both ways round)
  C  insert pilots    heat-set insert pilot size
  D  pockets          XIAO pocket clearance and battery pocket clearance
  E  magnet pockets   magnet pocket size, and the skin that closes the pocket
  E  skin, mate       a second copy of the skin coupon, to feel the pull through two skins

The magnet coupons print with the skin on the bed and the pocket open upwards, like the keywell.
The mate of the skin coupon has its pockets on the centre line. Turn it over about the long axis and the
pockets of both coupons face each other, skin against skin.

Run `task export -- coupons` to write build/coupons.stl and `task view -- coupons` to look at the plate in the OCP viewer.
"""
from dataclasses import replace

from build123d import *
from build123d import Shape

from duality_wave.models.features import magnet_recess_cutter, switch_cutter, xiao_pocket_cutter
from duality_wave.models.model_types import RectDimensions, RoundDimensions
from duality_wave.models.print_profile import PrintProfile
from duality_wave.models.switch import Switch
from duality_wave.models.xiao import Xiao

LABEL_DEPTH = 0.4
LABEL_SIZE = 2.2
CORNER_RADIUS = 1.0


def to_bed(shape: Shape, face_z: float) -> Shape:
    """Flip a shape modelled like the case (y up, bed-side face at face_z) into its print frame."""
    return shape.rotate(Axis.X, 180).translate((0, 0, face_z))


def engrave(part: Shape, top_z: float, labels: list[tuple[str, float, float]], size: float = LABEL_SIZE) -> Part:
    with BuildPart() as engraved:
        insert(part)
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
    reliefs: tuple[float, ...] = (0.0, 0.2, 0.4),
    pitch: float = 18.0,
    margin: float = 8.0,
) -> Part:
    """A: switch cutouts of different sizes (columns) with different corner reliefs (rows)."""
    width = len(sizes) * pitch + margin
    height = len(reliefs) * pitch + margin

    with BuildPart() as coupon:
        insert(chamfered_plate(width, height, plate_z, profile))
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
                insert(to_bed(cutter, 0), mode=Mode.SUBTRACT)

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
            insert(plate)
            with BuildSketch():
                with Locations((width / 2, height / 2)):
                    Circle(3)
            extrude(amount=plate_z, mode=Mode.SUBTRACT)
        plates.append(engrave(pushable.part, plate_z, [(f"{clearance:.2f}", width / 2, height - 4)], size=3))
    return cavity.part, plates


def insert_pilot_coupon(
    profile: PrintProfile,
    pilot_depth: float,
    pilot_diameters: tuple[float, ...] = (2.9, 3.0, 3.1, 3.2, 3.3),
    pitch: float = 9.5,
    margin: float = 5.5,
) -> Part:
    """C: heat-set insert pilots of different diameters. The pilots open upwards like in the keywell."""
    block_z = profile.snap_up(pilot_depth + 1.5)
    width = (len(pilot_diameters) - 1) * pitch + 2 * margin
    pilot_y, height = 6.0, 16.0

    with BuildPart() as coupon:
        with BuildSketch():
            with Locations((width / 2, height / 2)):
                RectangleRounded(width, height, CORNER_RADIUS)
        extrude(amount=block_z)

        for index, diameter in enumerate(pilot_diameters):
            x = margin + index * pitch
            with BuildPart(Plane.XY.offset(block_z - pilot_depth), mode=Mode.SUBTRACT):
                with Locations((x, pilot_y)):
                    Cylinder(diameter / 2, pilot_depth, align=(Align.CENTER, Align.CENTER, Align.MIN))

    labels = [(f"{d:.1f}", margin + index * pitch, pilot_y + 5.5) for index, d in enumerate(pilot_diameters)]
    return engrave(coupon.part, block_z, labels, size=2.0)


def magnet_block(
    profile: PrintProfile,
    magnet: RoundDimensions,
    pockets: list[tuple[float, float]],
    labels: list[str],
    margin: float = 3.0,
    wall: float = 2.0,
    label_room: float = 5.0,
) -> Part:
    """A block with one magnet pocket for each (clearance, skin) pair, in a row along x.

    The skin is on the bed at z=0 and the pocket opens at the top. The pocket is deep enough for the two
    stacked magnets and 1 mm more. The pockets sit on the centre line, so a copy turned over about the x axis
    puts pocket i on top of pocket i of the original.
    """
    skins = [profile.snap_up(skin) for _, skin in pockets]
    block_z = profile.snap_up(max(skins) + 2 * magnet.Z + 1.0)
    diameter = 2 * (magnet.radius + max(clearance for clearance, _ in pockets))
    pitch = diameter + wall
    width = len(pockets) * pitch - wall + 2 * margin
    height = diameter + 2 * (margin + label_room)

    with BuildPart() as block:
        with BuildSketch():
            with Locations((width / 2, height / 2)):
                RectangleRounded(width, height, CORNER_RADIUS)
        extrude(amount=block_z)
        for index, ((clearance, _), skin) in enumerate(zip(pockets, skins)):
            x = margin + diameter / 2 + index * pitch
            cutter = magnet_recess_cutter(
                magnet, replace(profile, magnet_clearance=clearance), [Vector(x, height / 2)],
                top_z=block_z, depth=block_z - skin)
            insert(cutter, mode=Mode.SUBTRACT)

    texts = [(text, margin + diameter / 2 + index * pitch, margin + label_room / 2) for index, text in enumerate(labels)]
    return engrave(block.part, block_z, texts, size=2.0)


def magnet_pocket_coupon(
    profile: PrintProfile,
    magnet: RoundDimensions,
    clearances: tuple[float, ...] = (0.0, 0.05, 0.10, 0.15, 0.20),
) -> Part:
    """E: magnet pockets of different sizes under the skin of the case. Labelled with the pocket diameter."""
    pockets = [(clearance, profile.magnet_skin) for clearance in clearances]
    labels = [f"{2 * (magnet.radius + clearance):.2f}" for clearance in clearances]
    return magnet_block(profile, magnet, pockets, labels)


def magnet_skin_coupon(
    profile: PrintProfile,
    magnet: RoundDimensions,
    skins: tuple[float, ...] = (0.2, 0.4, 0.6, 0.8),
) -> Part:
    """E: magnet pockets with different skins. Labelled with the skin.

    Put two stacked magnets in a pocket and hold a loose magnet on the skin side to feel the pull.
    Two copies of this coupon, skin against skin, show the pull through two skins like between the halves.
    """
    pockets = [(profile.magnet_clearance, skin) for skin in skins]
    return magnet_block(profile, magnet, pockets, [f"s{skin:g}" for skin in skins])


def pocket_coupon(
    profile: PrintProfile,
    xiao_z: float,
    plate_z: float,
    battery: RectDimensions,
    xiao_clearances: tuple[float, ...] = (0.0, 0.05, 0.10, 0.15),
    battery_clearances: tuple[float, ...] = (0.0, 0.10, 0.20),
    battery_depth: float = 2.0,
    margin: float = 3.0,
) -> Part:
    """D: XIAO pockets with different clearances in a keyplate-like plate, plus battery pockets.

    Everything opens upwards. The XIAO pockets have the window and the pocket of the keyplate.
    The battery pockets have the size of the real battery, so the battery itself is the gauge.
    """
    columns = 2
    rows = -(-len(xiao_clearances) // columns)
    pitch_x = Xiao.dims.d.X + 2 * max(xiao_clearances) + 4
    pitch_y = Xiao.dims.d.Y + 2 * max(xiao_clearances) + 5
    tallest = battery.Y + 2 * max(battery_clearances)
    widest = battery.X + 2 * max(battery_clearances)
    battery_pitch = tallest + 6
    width = columns * pitch_x + widest + 3 * margin
    height = max(rows * pitch_y, len(battery_clearances) * battery_pitch) + 2 * margin

    labels = []
    with BuildPart() as coupon:
        with BuildSketch():
            with Locations((width / 2, height / 2)):
                RectangleRounded(width, height, CORNER_RADIUS)
        extrude(amount=plate_z)

        for index, clearance in enumerate(xiao_clearances):
            row, column = divmod(index, columns)
            x = margin + pitch_x * (column + 0.5)
            y = margin + pitch_y * (row + 0.5)
            # the cutter is modelled like the keyplate, so y is mirrored by the flip
            cutter = xiao_pocket_cutter(replace(profile, xiao_clearance=clearance), Vector(x, -y, xiao_z), plate_z)
            insert(to_bed(cutter, 0), mode=Mode.SUBTRACT)
            labels.append((f"{clearance:.2f}", x, y - pitch_y / 2 + 1.5))

        center_x = width - margin - widest / 2
        top = (height + len(battery_clearances) * battery_pitch) / 2
        for index, clearance in enumerate(battery_clearances):
            size_x, size_y = battery.X + 2 * clearance, battery.Y + 2 * clearance
            center_y = top - battery_pitch * (index + 0.5) + 3
            with BuildSketch(Plane.XY.offset(plate_z)):
                with Locations((center_x, center_y)):
                    Rectangle(size_x, size_y)
            extrude(amount=-battery_depth, mode=Mode.SUBTRACT)
            labels.append((f"{clearance:.2f}", center_x, center_y - size_y / 2 - 3))
    return engrave(coupon.part, plate_z, labels, size=1.8)


def arrange(parts: dict[str, Shape], max_width: float = 172.0, gap: float = 6.0) -> dict[str, Shape]:
    """Pack the parts onto one print bed, turning a part by 90 degrees where that helps.

    Several simple packing orders are tried and the lowest layout wins. The default width leaves
    room on a 180 mm bed. A part wider than max_width gets a spot above the rest.
    """
    sizes = {name: part.bounding_box().size for name, part in parts.items()}
    orders = [
        sorted(parts, key=lambda n: -sizes[n].X * sizes[n].Y),
        sorted(parts, key=lambda n: -max(sizes[n].X, sizes[n].Y)),
        sorted(parts, key=lambda n: -min(sizes[n].X, sizes[n].Y)),
    ]
    scores = [
        lambda x, y, depth, height: (max(height, y + depth), y + depth, x),
        lambda x, y, depth, height: (y, x),
    ]

    def pack(order, score):
        taken: list[tuple[float, float, float, float]] = []
        layout = {}
        for name in order:
            height = max((box[3] for box in taken), default=0.0)
            best = None
            for angle in (0, 90):
                width, depth = (sizes[name].X, sizes[name].Y) if angle == 0 else (sizes[name].Y, sizes[name].X)
                for y in sorted({0.0, *(other[3] + gap for other in taken)}):
                    for x in sorted({0.0, *(other[2] + gap for other in taken)}):
                        if x + width > max_width and x > 0:
                            continue
                        if any(x < o[2] + gap and o[0] < x + width + gap and y < o[3] + gap and o[1] < y + depth + gap for o in taken):
                            continue
                        candidate = (score(x, y, depth, height), angle, x, y, width, depth)
                        if best is None or candidate[0] < best[0]:
                            best = candidate
            if best is None:
                best = (None, 0, 0.0, height + gap if taken else 0.0, sizes[name].X, sizes[name].Y)
            _, angle, x, y, width, depth = best
            layout[name] = (angle, x, y)
            taken.append((x, y, x + width, y + depth))
        return max(box[3] for box in taken), max(box[2] for box in taken), layout

    _, _, layout = min((pack(order, score) for order in orders for score in scores), key=lambda r: r[:2])
    placed = {}
    for name, (angle, x, y) in layout.items():
        part = parts[name].rotate(Axis.Z, angle) if angle else parts[name]
        box = part.bounding_box()
        placed[name] = part.translate((x - box.min.X, y - box.min.Y, -box.min.Z))
    return placed


def create_coupon_parts(switch: Switch, dims, profile: PrintProfile | None = None) -> dict[str, Shape]:
    """All coupon parts by name, arranged on one print bed."""
    profile = profile or dims.print_profile
    cavity, plates = plate_fit_coupon(profile, dims.keyplate_z, dims.wall_thickness)
    skin = magnet_skin_coupon(profile, dims.magnet_d)
    parts = {
        "A switch plate": switch_plate_coupon(switch, profile, dims.keyplate_z),
        "B cavity": cavity,
        **{f"B plate {index + 1}": plate for index, plate in enumerate(plates)},
        "C insert pilots": insert_pilot_coupon(profile, dims.heat_insert_z),
        "D pockets": pocket_coupon(profile, dims.xiao_position.Z, dims.keyplate_z, dims.battery_pd.d),
        "E magnet pockets": magnet_pocket_coupon(profile, dims.magnet_d),
        "E skin": skin,
        "E skin, mate": skin,
    }
    return arrange(parts)


def create_coupons(switch: Switch, dims, profile: PrintProfile | None = None) -> Compound:
    return Compound(list(create_coupon_parts(switch, dims, profile).values()))
