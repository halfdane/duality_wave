"""Poses of the built case: the assembled keyboard, the transport position and the exploded view.

A pose moves finished shapes. It builds nothing and changes no printed part.
"""
from build123d import Location, Pos, Rot, Shape

from duality_wave.builders.parts import GROUPS, side_parts

POSES = ("assembled", "transport", "exploded")
EXPLODE_STEP = 26.0


def transport_location(dims) -> Location:
    """Turn the right half over onto the left half. A point (x, y, z) of the right half lands on (offset - x, y, 2 * above_z - z).

    The right half is the left half mirrored about x = offset / 2, so the halves meet with their keywell tops at z = above_z.
    """
    return Pos(dims.right_side_offset, 0, 2 * dims.above_z) * Rot(0, 180, 0)


def transported(shape: Shape, dims) -> Shape:
    return shape.moved(transport_location(dims))


def exploded(parts: dict[str, Shape], step: float = EXPLODE_STEP) -> dict[str, Shape]:
    """Move each group down by its layer times the step."""
    return {name: shape.moved(Pos(0, 0, -GROUPS[name].level * step)) for name, shape in parts.items()}


def pose_scene(case, pose: str) -> dict[str, Shape]:
    """The shapes of a pose by name, for example keywell_left. Case must be built with a viewer that shows the accessories."""
    if pose not in POSES:
        raise ValueError(f"Unknown pose {pose!r}. Use one of {POSES}.")
    left = side_parts(case.left)
    if pose == "exploded":
        return {f"{name}_left": shape for name, shape in exploded(left).items()}
    scene = {f"{name}_left": shape for name, shape in left.items()}
    if case.right is not None:
        for name, shape in side_parts(case.right).items():
            scene[f"{name}_right"] = transported(shape, case.ctx.dims) if pose == "transport" else shape
    return scene
