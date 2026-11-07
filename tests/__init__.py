import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WAVE_LAYOUT = str(ROOT / "ergogen" / "wave.points.yaml")
COMPACT_LAYOUT = str(ROOT / "ergogen" / "compact.points.yaml")
PERF_FACTOR = float(os.environ.get("WAVE_PERF_FACTOR", "1"))
