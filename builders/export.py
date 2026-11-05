from pathlib import Path

from build123d import export_step

STEP_DIR = Path(__file__).resolve().parent.parent / "build" / "step"


def export_steps(case, suffix: str = "", out_dir: Path = STEP_DIR) -> list[Path]:
    """Write a STEP file for every printable part of every built half, for example keywell_left.step."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for built in (case.left, case.right):
        if built is None:
            continue
        for name in ("keywell", "keyplate", "bottom"):
            path = out_dir / f"{name}_{built.side.name}{suffix}.step"
            export_step(getattr(built, name), str(path))
            written.append(path)
    return written
