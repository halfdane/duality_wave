"""Record or compare the geometry and the build time of the case.

    python scripts/baseline.py write docs/baseline/step0.json
    python scripts/baseline.py compare docs/baseline/step0.json [--rel-tol 1e-6]

The record has one entry per variant and part: validity, solid count, volume and bounding box.
It also has the wall-clock time of each build stage.
"""

import argparse
import json
import sys
import time

from duality_wave.case import WaveCase
from duality_wave.models.case_dimensions import CaseDimensions, CompactCaseDimensions
from duality_wave.models.choc import Choc
from duality_wave.models.keys import ErgoKeys, get_points
from duality_wave.models.outline import Outline
from duality_wave.paths import LAYOUT_DIR


def make_variant(name: str):
    switch = Choc()
    if name == "full":
        keys = ErgoKeys(points=get_points(file_path=LAYOUT_DIR / "wave.points.yaml"))
        outline = Outline(switch=switch, keys=keys, wall_thickness=CaseDimensions.wall_thickness)
        dims = CaseDimensions(switch=switch, outline=outline, keys=keys)
        both_sides = True
    else:
        keys = ErgoKeys(points=get_points(file_path=LAYOUT_DIR / "compact.points.yaml"))
        outline = Outline(
            switch=switch, keys=keys, wall_thickness=CompactCaseDimensions.wall_thickness, additional_top_space=22)
        dims = CompactCaseDimensions(switch=switch, outline=outline, keys=keys)
        both_sides = False
    return switch, keys, outline, dims, both_sides


def describe(shape) -> dict:
    box = shape.bounding_box()
    return {
        "valid": bool(shape.is_valid),
        "solids": len(shape.solids()),
        "volume": round(shape.volume, 3),
        "bbox_min": [round(box.min.X, 3), round(box.min.Y, 3), round(box.min.Z, 3)],
        "bbox_max": [round(box.max.X, 3), round(box.max.Y, 3), round(box.max.Z, 3)],
    }


def record() -> dict:
    result: dict = {"build123d": None, "variants": {}}
    import build123d

    result["build123d"] = build123d.__version__
    for variant in ("full", "compact"):
        switch, keys, outline, dims, both_sides = make_variant(variant)
        start = time.perf_counter()
        case = WaveCase(
            switch=switch, keys=keys, caseDimensions=dims, outline=outline, debug=False, both_sides=both_sides)
        total = time.perf_counter() - start
        parts = {}
        for side_name, side in (("left", case.left), ("right", case.right)):
            if side is None:
                continue
            for part_name in ("keywell", "keyplate", "bottom"):
                parts[f"{side_name}.{part_name}"] = describe(getattr(side, part_name))
        result["variants"][variant] = {
            "total_seconds": round(total, 2),
            "stage_seconds": {k: round(v, 2) for k, v in case.timings.items()},
            "parts": parts,
        }
    return result


def compare(old: dict, new: dict, rel_tol: float) -> list[str]:
    problems = []
    for variant, old_variant in old["variants"].items():
        new_variant = new["variants"].get(variant)
        if new_variant is None:
            problems.append(f"{variant}: missing")
            continue
        for part, old_part in old_variant["parts"].items():
            new_part = new_variant["parts"].get(part)
            if new_part is None:
                problems.append(f"{variant}.{part}: missing")
                continue
            for key in ("valid", "solids"):
                if old_part[key] != new_part[key]:
                    problems.append(f"{variant}.{part}.{key}: {old_part[key]} -> {new_part[key]}")
            if abs(old_part["volume"] - new_part["volume"]) > rel_tol * max(1.0, abs(old_part["volume"])):
                problems.append(f"{variant}.{part}.volume: {old_part['volume']} -> {new_part['volume']}")
            for key in ("bbox_min", "bbox_max"):
                if any(abs(a - b) > 1e-3 for a, b in zip(old_part[key], new_part[key])):
                    problems.append(f"{variant}.{part}.{key}: {old_part[key]} -> {new_part[key]}")
        print(
            f"{variant}: total {old_variant['total_seconds']} s -> {new_variant['total_seconds']} s, "
            f"stages {old_variant['stage_seconds']} -> {new_variant['stage_seconds']}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("write", "compare"))
    parser.add_argument("path")
    parser.add_argument("--rel-tol", type=float, default=1e-6)
    args = parser.parse_args()
    new = record()
    if args.mode == "write":
        with open(args.path, "w") as f:
            json.dump(new, f, indent=2)
            f.write("\n")
        print(f"wrote {args.path}")
        return 0
    with open(args.path) as f:
        old = json.load(f)
    problems = compare(old, new, args.rel_tol)
    for problem in problems:
        print("DIFF", problem)
    print("identical" if not problems else f"{len(problems)} differences")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
