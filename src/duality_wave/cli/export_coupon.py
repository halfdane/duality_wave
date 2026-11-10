"""Write the STL of every coupon plate to build/coupons and print their paths.

Run `task export-coupon`. This shows nothing in the viewer.
"""
import argparse
from pathlib import Path

from build123d import Compound, export_stl

from duality_wave.cli.common import COUPON_TARGETS, coupon_parts
from duality_wave.paths import COUPON_DIR


def export_coupon(target: str, out_dir: Path = COUPON_DIR) -> Path:
    coupons = Compound(list(coupon_parts(target).values()))
    out_path = Path(out_dir) / f"{target.replace('-', '_')}.stl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    export_stl(coupons, str(out_path))
    return out_path


def export_coupons(out_dir: Path = COUPON_DIR) -> list[Path]:
    return [export_coupon(target, out_dir) for target in COUPON_TARGETS]


def main(argv: list[str] | None = None) -> None:
    argparse.ArgumentParser(prog="export-coupon", description=__doc__.splitlines()[0]).parse_args(argv)
    for path in export_coupons():
        print(path)
