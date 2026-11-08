"""Write the printable files to build/: STEP files of the case, or the STL of a coupon plate.

Run `task export` or `task export -- coupons`. This shows nothing in the viewer.
"""
import argparse
from pathlib import Path

from build123d import Compound, export_stl

from duality_wave.builders.export import export_steps
from duality_wave.cli.common import COUPON_TARGETS, build_case, coupon_parts
from duality_wave.paths import BUILD_DIR

TARGETS = ("case", *COUPON_TARGETS)


def export_coupons(target: str, out_dir: Path = BUILD_DIR) -> Path:
    parts = coupon_parts(target)
    coupons = Compound(list(parts.values()))
    size = coupons.bounding_box().size
    out_path = Path(out_dir) / f"{target.replace('-', '_')}.stl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    export_stl(coupons, str(out_path))
    print(f"{out_path}: {len(coupons.solids())} parts, {size.X:.0f} x {size.Y:.0f} x {size.Z:.1f} mm")
    return out_path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="export", description=__doc__.splitlines()[0])
    parser.add_argument("target", nargs="?", default="case", choices=TARGETS, help="what to write (default: case)")
    parser.add_argument("--compact", action="store_true", help="the compact variant of the case")
    args = parser.parse_args(argv)

    if args.target != "case":
        if args.compact:
            parser.error("--compact applies to the case only")
        export_coupons(args.target)
        return
    case = build_case(compact=args.compact)
    for path in export_steps(case, suffix="_compact" if args.compact else ""):
        print(path)

