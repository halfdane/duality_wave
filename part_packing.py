import copy
from collections.abc import Callable

from build123d import Axis, BuildPart, Part, Plane, Shape, Solid, Vector, add


PartPointTransform = Callable[[Vector], Vector]


def _validate_case_parts(case) -> bool:
    left_names = ("keywell_left", "keyplate_left", "bottom_left")
    right_names = ("keywell_right", "keyplate_right", "bottom_right")

    missing_left = [name for name in left_names if not hasattr(case, name)]
    if missing_left:
        raise ValueError(f"case is missing required parts: {', '.join(missing_left)}")

    present_right = [hasattr(case, name) for name in right_names]
    if any(present_right) and not all(present_right):
        missing_right = [name for name in right_names if not hasattr(case, name)]
        raise ValueError(f"case has an incomplete right side: {', '.join(missing_right)}")

    return all(present_right)


def _place(
    shape: Shape,
    *,
    center: Vector,
    flip: bool = False,
    min_z: float | None = None,
    max_z: float | None = None,
) -> tuple[Shape, PartPointTransform]:
    source_box = shape.bounding_box()
    source_center = source_box.center()
    placed = copy.copy(shape)

    if flip:
        placed = placed.rotate(Axis(source_center, Axis.Y.direction), 180)

    box = placed.bounding_box()
    z_offset = 0
    if min_z is not None:
        z_offset = min_z - box.min.Z
    elif max_z is not None:
        z_offset = max_z - box.max.Z

    offset = Vector(center.X - box.center().X, center.Y - box.center().Y, z_offset)
    placed = placed.translate(offset)

    def transform_point(point: Vector) -> Vector:
        transformed = Vector(point)
        if flip:
            transformed = Vector(
                2 * source_center.X - transformed.X,
                transformed.Y,
                2 * source_center.Z - transformed.Z,
            )
        return transformed + offset

    return placed, transform_point


def _sprue(start: Vector, end: Vector, radius: float) -> Solid:
    direction = end - start
    if direction.length <= 0:
        raise ValueError("sprue endpoints must be distinct")

    overlap = min(radius / 2, direction.length / 4)
    unit = direction.normalized()
    return Solid.make_cylinder(
        radius,
        direction.length + 2 * overlap,
        Plane(origin=start - unit * overlap, z_dir=unit),
    )


def _exterior_stack_sprues(
    bottom: Shape, keyplate: Shape, radius: float, count: int = 8
) -> list[Solid]:
    bottom_box = bottom.bounding_box()
    keyplate_box = keyplate.bounding_box()
    x_min = max(bottom_box.min.X, keyplate_box.min.X) + radius / 2
    x_max = min(bottom_box.max.X, keyplate_box.max.X) - radius / 2
    y_min = max(bottom_box.min.Y, keyplate_box.min.Y) + radius / 2
    y_max = min(bottom_box.max.Y, keyplate_box.max.Y) - radius / 2
    z = (bottom_box.max.Z + keyplate_box.min.Z) / 2

    width = x_max - x_min
    height = y_max - y_min
    perimeter = 2 * (width + height)
    rods = []
    for i in range(count):
        # Walk clockwise around the overlap rectangle's perimeter.
        step = perimeter * i / count
        if step < width:
            x, y = x_min + step, y_min
        elif step < width + height:
            x, y = x_max, y_min + (step - width)
        elif step < 2 * width + height:
            x, y = x_max - (step - width - height), y_max
        else:
            x, y = x_min, y_max - (step - 2 * width - height)

        seed = Vector(x, y, z)
        _, bottom_point, _ = bottom.distance_to_with_closest_points(seed)
        _, keyplate_point, _ = keyplate.distance_to_with_closest_points(seed)
        attachment = 5 * (bottom_point + keyplate_point)
        inward = Vector(
            bottom_box.center().X - attachment.X,
            bottom_box.center().Y - attachment.Y,
            0,
        ).normalized() * radius
        rods.append(_sprue(bottom_point + inward, keyplate_point + inward, radius))
    return rods


def _horizontal_sprues(
    keywell: Shape, bottom: Shape, keyplate: Shape, radius: float
) -> list[Solid]:
    rods = []
    for target, fraction in ((bottom, 0.3), (keyplate, 0.5), (bottom, 0.7)):
        target_box = target.bounding_box()
        keywell_box = keywell.bounding_box()
        y_min = max(target_box.min.Y, keywell_box.min.Y)
        y_max = min(target_box.max.Y, keywell_box.max.Y)
        seed = Vector(
            (target_box.max.X + keywell_box.min.X) / 2,
            y_min + fraction * (y_max - y_min),
            target_box.center().Z,
        )
        _, target_point, _ = target.distance_to_with_closest_points(seed)
        _, keywell_point, _ = keywell.distance_to_with_closest_points(seed)
        rods.append(_sprue(target_point, keywell_point, radius))
    return rods


def _pack_one_side(case, part_gap: float, radius: float) -> tuple[list[Shape], list[Solid]]:
    plate_center = Vector(0, 0, 0)
    bottom, _ = _place(case.bottom_left, center=plate_center)
    keyplate, _ = _place(
        case.keyplate_left,
        center=plate_center,
        min_z=bottom.bounding_box().max.Z + part_gap,
    )
    stack_box = bottom.fuse(keyplate).bounding_box()
    keywell_width = case.keywell_left.bounding_box().size.X
    keywell_center = Vector(stack_box.max.X + part_gap + keywell_width / 2, 0, 0)
    keywell, _ = _place(case.keywell_left, center=keywell_center)

    parts = [bottom, keyplate, keywell]
    rods = _exterior_stack_sprues(bottom, keyplate, radius)
    rods.extend(_horizontal_sprues(keywell, bottom, keyplate, radius))
    return parts, rods


def _pack_two_sides(case, part_gap: float, radius: float) -> tuple[list[Shape], list[Solid]]:
    plate_center = Vector(0, 0, 0)
    left_bottom, left_bottom_point = _place(
        case.bottom_left, center=plate_center, flip=True, max_z=-part_gap / 2
    )
    right_bottom, right_bottom_point = _place(
        case.bottom_right, center=plate_center, min_z=part_gap / 2
    )
    left_keyplate, _ = _place(
        case.keyplate_left,
        center=plate_center,
        flip=True,
        max_z=left_bottom.bounding_box().min.Z - part_gap,
    )
    right_keyplate, _ = _place(
        case.keyplate_right,
        center=plate_center,
        min_z=right_bottom.bounding_box().max.Z + part_gap,
    )

    stack_max_x = max(
        shape.bounding_box().max.X
        for shape in (left_bottom, right_bottom, left_keyplate, right_keyplate)
    )
    keywell_width = case.keywell_left.bounding_box().size.X
    keywell_center = Vector(stack_max_x + part_gap + keywell_width / 2, 0, 0)
    right_keywell, right_keywell_point = _place(
        case.keywell_right, center=keywell_center, max_z=-part_gap / 2
    )
    left_keywell, left_keywell_point = _place(
        case.keywell_left, center=keywell_center, flip=True, min_z=part_gap / 2
    )

    parts = [left_bottom, left_keyplate, right_keywell, right_bottom, right_keyplate, left_keywell]
    rods = _exterior_stack_sprues(left_keyplate, left_bottom, radius)
    rods.extend(_exterior_stack_sprues(right_bottom, right_keyplate, radius))
    rods.extend(_horizontal_sprues(right_keywell, left_bottom, left_keyplate, radius))
    rods.extend(_horizontal_sprues(left_keywell, right_bottom, right_keyplate, radius))

    for location in case.dims.bumper_locations:
        recess_floor_z = -case.dims.below_z + case.bumper.dims.base_z
        left = left_bottom_point(Vector(location.X, location.Y, recess_floor_z))
        right_location = Vector(
            case.dims.right_side_offset - location.X, location.Y, recess_floor_z
        )
        right = right_bottom_point(right_location)
        rods.append(_sprue(left, right, radius))

    for location in case.dims.magnet_positions[1:]:
        recess_floor_z = case.dims.above_z - 3 * case.dims.magnet_d.Z
        left_location = Vector(location.X, location.Y, recess_floor_z)
        left = left_keywell_point(left_location)
        right_location = Vector(
            case.dims.right_side_offset - location.X, location.Y, recess_floor_z
        )
        right = right_keywell_point(right_location)
        rods.append(_sprue(right, left, radius))

    return parts, rods


def pack_parts_for_jlcpcb(
    case, part_gap: float = 5.0, sprue_diameter: float = 3.0
) -> Part:
    """Pack three or six case parts into one sprued JLC3DP assembly."""
    if part_gap <= 0 or sprue_diameter <= 0:
        raise ValueError("part_gap and sprue_diameter must be positive")

    both_sides = _validate_case_parts(case)
    radius = sprue_diameter / 2
    if both_sides:
        parts, rods = _pack_two_sides(case, part_gap, radius)
    else:
        parts, rods = _pack_one_side(case, part_gap, radius)

    with BuildPart() as packed:
        for shape in (*parts, *rods):
            add(shape)
    return packed.part
