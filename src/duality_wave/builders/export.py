from pathlib import Path

from build123d import Axis, Shape, export_step

from duality_wave.paths import CASE_DIR

# These parts have their bed face on top in the assembled frame.
UPSIDE_DOWN_PARTS = ("keywell", "keyplate")


def print_pose(name: str, shape: Shape) -> Shape:
    """Turn a part into its print orientation: bed face down, lowest point at z = 0."""
    if name in UPSIDE_DOWN_PARTS:
        shape = shape.rotate(Axis.X, 180)
    return shape.translate((0, 0, -shape.bounding_box().min.Z))


def export_steps(case, suffix: str = "", out_dir: Path = CASE_DIR) -> list[Path]:
    """Write a STEP file for every printable part of every built half, for example keywell_left.step.

    Every file is in its print orientation, so the slicer needs no flip.
    The magnet spacer is one disc for all pockets of both halves.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for built in (case.left, case.right):
        if built is None:
            continue
        for name in ("keywell", "keyplate", "bottom"):
            path = out_dir / f"{name}_{built.side.name}{suffix}.step"
            export_step(print_pose(name, getattr(built, name)), str(path))
            written.append(path)
    if case.magnet_spacer is not None:
        path = out_dir / f"magnet_spacer{suffix}.step"
        export_step(print_pose("magnet_spacer", case.magnet_spacer), str(path))
        written.append(path)
    return written
