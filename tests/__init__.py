import os
from pathlib import Path

from OCP.OSD import OSD_ThreadPool

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
OSD_ThreadPool.DefaultPool_s().Init(1)

ROOT = Path(__file__).resolve().parent.parent
WAVE_LAYOUT = str(ROOT / "ergogen" / "wave.points.yaml")
COMPACT_LAYOUT = str(ROOT / "ergogen" / "compact.points.yaml")
PERF_FACTOR = float(os.environ.get("WAVE_PERF_FACTOR", "1"))
