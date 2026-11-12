from pathlib import Path

from build123d import Location, Pos, Rot, Shape, export_step

from duality_wave.paths import CASE_DIR

# These parts have their bed face on top in the assembled frame.
UPSIDE_DOWN_PARTS = ("keywell", "keyplate")


def print_transform(name: str, shape: Shape) -> Location:
    """The move that turns a part into its print orientation: bed face down, lowest point at z = 0."""
    flip = Rot(180, 0, 0) if name in UPSIDE_DOWN_PARTS else Location()
    return Pos(0, 0, -shape.moved(flip).bounding_box().min.Z) * flip


def print_pose(name: str, shape: Shape) -> Shape:
    """Turn a part into its print orientation: bed face down, lowest point at z = 0."""
    return shape.moved(print_transform(name, shape))


def print_pose_emblem(name: str, shape: Shape, emblem: Shape) -> Shape:
    """The emblem of a part in the print orientation of the part. Both files share one frame, so they load on top of each other."""
    return emblem.moved(print_transform(name, shape))


def export_steps(case, suffix: str = "", out_dir: Path = CASE_DIR) -> list[Path]:
    """Write a STEP file for every printable part of every built half, for example keywell_left.step.

    Every file is in its print orientation, so the slicer needs no flip.
    A part with an emblem and its emblem get the prefixes 01_ and 02_, for example 01_keywell_left.step and 02_keywell_left_emblem.step.
    Both files are in the same frame. Load them together in the slicer as one object with two parts.
    The part has no pocket for the emblem, so the two overlap. The slicer gives the overlap to the later part,
    which is why the prefixes put the emblem after the part in the file dialog.
    The magnet spacer is one disc for all pockets of both halves.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for built in (case.left, case.right):
        if built is None:
            continue
        for name in ("keywell", "keyplate", "bottom"):
            body = getattr(built, name)
            prefix = "01_" if name in built.emblems else ""
            path = out_dir / f"{prefix}{name}_{built.side.name}{suffix}.step"
            export_step(print_pose(name, body), str(path))
            written.append(path)
            if name in built.emblems:
                path = out_dir / f"02_{name}_{built.side.name}_emblem{suffix}.step"
                export_step(print_pose_emblem(name, body, built.emblems[name]), str(path))
                written.append(path)
    if case.magnet_spacer is not None:
        path = out_dir / f"magnet_spacer{suffix}.step"
        export_step(print_pose("magnet_spacer", case.magnet_spacer), str(path))
        written.append(path)
    return written
