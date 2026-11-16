"""Find overlaps between shapes without a boolean operation on every pair."""


def solids_with_boxes(shape) -> list:
    """The solids of a shape with a quick bounding box. The quick box is larger than the exact one, and it costs far less on curved solids."""
    return [(solid, solid.bounding_box(optimal=False)) for solid in shape.solids()]


def boxes_overlap(a, b, tolerance) -> bool:
    return all(getattr(a.min, axis) < getattr(b.max, axis) - tolerance and getattr(b.min, axis) < getattr(a.max, axis) - tolerance for axis in "XYZ")


def overlap_volume(first: list, second: list, tolerance=1e-6) -> float:
    """The volume that two shapes share, given as solids with boxes. Only solids whose boxes overlap are intersected."""
    volume = 0.0
    for one, box_one in first:
        for other, box_other in second:
            if boxes_overlap(box_one, box_other, tolerance):
                shared = one & other
                volume += sum(solid.volume for solid in shared.solids()) if shared else 0.0
    return volume
