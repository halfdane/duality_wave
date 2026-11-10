"""Write the STEP files of the case to build/case and print their paths.

Run `task export-case`. This shows nothing in the viewer.
"""
import argparse

from duality_wave.builders.export import export_steps
from duality_wave.cli.common import build_case


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="export-case", description=__doc__.splitlines()[0])
    parser.add_argument("--compact", action="store_true", help="the compact variant of the case")
    args = parser.parse_args(argv)

    case = build_case(compact=args.compact)
    for path in export_steps(case, suffix="_compact" if args.compact else ""):
        print(path)
