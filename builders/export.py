from build123d import export_step


def export_steps(case, suffix: str = "") -> None:
    """Write a STEP file for every printable part of every built half, for example keywell_left.step."""
    for built in (case.left, case.right):
        if built is None:
            continue
        for name in ("keywell", "keyplate", "bottom"):
            export_step(getattr(built, name), f"{name}_{built.side.name}{suffix}.step")
