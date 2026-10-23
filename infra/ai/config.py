import os
from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR: Path = Path(__file__).resolve().parent / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)

DATA_DIR: Path = Path(os.environ.get("COMPASS_DATA_DIR", str(REPO_ROOT / "data")))


def _find(*candidates: Path) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


EQUIL_PATH: Path = _find(
    DATA_DIR / "equil_data.csv",
    DATA_DIR / "uloha_1-magneticka_data" / "equil_data.csv",
)
EQUIL_NOISY_PATH: Path = _find(
    DATA_DIR / "equil_data_noisy.csv",
    DATA_DIR / "uloha_1-magneticka_data" / "equil_data_noisy.csv",
)
CAMERA_CSV: Path = _find(
    DATA_DIR / "camera_data.csv",
    DATA_DIR / "uloha_1-photron" / "camera_data.csv",
)
JPEG_DIR: Path = _find(
    DATA_DIR / "jpeg",
    DATA_DIR / "uloha_1-photron" / "jpeg",
)

FEATURES: list[str] = [f"IPR{i:02d}" for i in range(1, 17)] + [
    f"FL{i:02d}" for i in range(1, 9)
]

TARGETS: list[str] = [
    "R_mag_axis",
    "Z_mag_axis",
    "elongation",
    "triangularity",
    "triangularity_lower",
    "triangularity_upper",
    "a",
    "R_geom",
    "Z_geom",
    "plasma_current",
]

XPOINT_TARGETS: list[str] = [
    "R_x_point",
    "Z_x_point",
    "R_strike_point_1",
    "Z_strike_point_1",
    "R_strike_point_2",
    "Z_strike_point_2",
]

LIMITER_TARGETS: list[str] = ["R_limiter", "Z_limiter"]

CLASSIFICATION_TARGET: str = "is_limited"

SPLIT_PATH: Path = ARTIFACTS_DIR / "split.json"
MODEL_PATH: Path = ARTIFACTS_DIR / "magnetic_mlp.joblib"
METRICS_PATH: Path = ARTIFACTS_DIR / "magnetic_metrics.json"
CAMERA_MODEL_PATH: Path = ARTIFACTS_DIR / "camera_all_targets.joblib"
CAMERA_METRICS_PATH: Path = ARTIFACTS_DIR / "camera_all_targets.json"

TEST_FRAC: float = 0.2
SEED: int = 0
