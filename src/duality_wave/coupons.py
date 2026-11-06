"""Calibration coupons for the fit constants in models/print_profile.py.

Every coupon answers one question and is modelled in its real print orientation, so elephant
foot and bridging behave like they will on the case. Print them all on one plate with the same
settings as the final case, then copy the winning values into the PrintProfile.

  A  switch plate     switch cutout size, with and without corner relief
  B  plate in cavity  plate clearance (try each plate both ways round)
  C  round holes      magnet recess size and heat-set insert pilot size
  D  pockets          XIAO pocket clearance and the battery pocket

Run `task coupons` to export build/coupons.stl and to preview the coupons in the OCP viewer.
"""
from dataclasses import replace

from build123d import *
from build123d import Shape

from duality_wave.models.choc import Choc
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
            insert(to_bed(cutter, block_z), mode=Mode.SUBTRACT)

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
    xiao_z: float,
    plate_z: float,
    battery: RectDimensions,
    xiao_clearances: tuple[float, ...] = (0.0, 0.05, 0.10, 0.15),
    battery_depth: float = 2.0,
    margin: float = 3.0,
) -> Part:
    """D: XIAO pockets with different clearances in a keyplate-like plate, plus the battery pocket.

    Everything opens upwards. The XIAO pockets have the window and the pocket of the keyplate.
    """
    columns = 2
    rows = -(-len(xiao_clearances) // columns)
    pitch_x = Xiao.dims.d.X + 2 * max(xiao_clearances) + 4
    pitch_y = Xiao.dims.d.Y + 2 * max(xiao_clearances) + 5
    battery_x = battery.X + 2 * profile.battery_clearance
    battery_y = battery.Y + 2 * profile.battery_clearance
    width = columns * pitch_x + battery_x + 3 * margin
    height = max(rows * pitch_y, battery_y + 8) + 2 * margin

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

        battery_center = (width - margin - battery_x / 2, height / 2)
        with BuildSketch(Plane.XY.offset(plate_z)):
            with Locations(battery_center):
                Rectangle(battery_x, battery_y)
        extrude(amount=-battery_depth, mode=Mode.SUBTRACT)
        labels.append(("battery", battery_center[0], battery_center[1] - battery_y / 2 - 3))
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
    parts = {
        "A switch plate": switch_plate_coupon(switch, profile, dims.keyplate_z),
        "B cavity": cavity,
        **{f"B plate {index + 1}": plate for index, plate in enumerate(plates)},
        "C round holes": round_hole_coupon(profile, dims.magnet_d, dims.above_z, dims.heat_insert_z),
        "D pockets": pocket_coupon(profile, dims.xiao_position.Z, dims.keyplate_z, dims.battery_pd.d),
    }
    return arrange(parts)


def create_coupons(switch: Switch, dims, profile: PrintProfile | None = None) -> Compound:
    return Compound(list(create_coupon_parts(switch, dims, profile).values()))


def preview(parts: dict[str, Shape]) -> None:
    """Show the coupons in the OCP viewer (`task viewer`). Does nothing if no viewer is running."""
    try:
        from ocp_vscode import Camera, set_defaults, set_port, show_clear, show_object

        set_port(3939)
        show_clear()
        set_defaults(ortho=True, default_edgecolor="#121212", reset_camera=Camera.KEEP)
        show_object(parts, name="coupons")
    except Exception as error:
        print(f"No preview: could not reach the OCP viewer ({error}). Start it with `task viewer`.")


if __name__ == "__main__":
    from duality_wave.models.case_dimensions import CaseDimensions
    from duality_wave.models.keys import ErgoKeys, get_points
    from duality_wave.models.outline import Outline
    from duality_wave.paths import BUILD_DIR, LAYOUT_DIR

    switch = Choc()
    config_path = LAYOUT_DIR / "wave.points.yaml"
    keys = ErgoKeys(points=get_points(file_path=config_path))
    outline = Outline(switch=switch, keys=keys, wall_thickness=CaseDimensions.wall_thickness)
    dims = CaseDimensions(switch=switch, outline=outline, keys=keys)

    parts = create_coupon_parts(switch, dims)
    coupons = Compound(list(parts.values()))
    size = coupons.bounding_box().size
    out_path = BUILD_DIR / "coupons.stl"
    out_path.parent.mkdir(exist_ok=True)
    print(f"{out_path}: {len(coupons.solids())} parts, {size.X:.0f} x {size.Y:.0f} x {size.Z:.1f} mm")
    export_stl(coupons, str(out_path))
    preview(parts)
