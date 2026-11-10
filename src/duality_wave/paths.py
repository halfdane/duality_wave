from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAYOUT_DIR = ROOT / "ergogen"
BUILD_DIR = ROOT / "build"
CASE_DIR = BUILD_DIR / "case"
COUPON_DIR = BUILD_DIR / "coupons"
WIRING_FILE = LAYOUT_DIR / "wave.wiring.yaml"
