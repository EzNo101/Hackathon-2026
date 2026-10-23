from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from .config import (
    ARTIFACTS_DIR,
    CLASSIFICATION_TARGET,
    FEATURES,
    LIMITER_TARGETS,
    TARGETS,
    XPOINT_TARGETS,
)
from .data import canonicalize_strike_points, load_equilibrium
from .prepare_camera import INDEX_PATH

MATCH_PATH: Path = ARTIFACTS_DIR / "camera_targets.csv"
MATCH_META_PATH: Path = ARTIFACTS_DIR / "camera_targets_meta.json"

TARGET_COLUMNS: list[str] = TARGETS + XPOINT_TARGETS + LIMITER_TARGETS + [CLASSIFICATION_TARGET]


def match_frames(
    eq: pd.DataFrame, index: pd.DataFrame, tolerance: float = 0.02
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Attach plasma targets and magnetic features to each camera frame.

    Camera frames are denser than equilibrium samples, so nearest-neighbour
    matching in time within a discharge is used. Frames further than
    `tolerance` seconds from an equilibrium sample are dropped.
    """
    eq = canonicalize_strike_points(eq)
    available = [c for c in TARGET_COLUMNS + FEATURES if c in eq.columns]

    parts: list[pd.DataFrame] = []
    for discharge in sorted(set(eq["discharge"]) & set(index["discharge"])):
        left = (
            index[index["discharge"] == discharge]
            .sort_values("time")
            .rename(columns={"time": "t_cam"})
        )
        right = eq[eq["discharge"] == discharge].sort_values("time")
        right = right[["time"] + available].rename(columns={"time": "t_eq"})
        matched = pd.merge_asof(
            left,
            right,
            left_on="t_cam",
            right_on="t_eq",
            direction="nearest",
            tolerance=tolerance,  # pyright: ignore[reportArgumentType]
        )
        matched["discharge"] = discharge
        parts.append(matched)

    out = pd.concat(parts, ignore_index=True)
    used = out.dropna(subset=["R_mag_axis", "Z_mag_axis", "elongation"])
    dt = (used["t_cam"] - used["t_eq"]).abs() * 1e3

    meta: dict[str, Any] = {
        "tolerance_s": tolerance,
        "camera_frames": len(index),
        "matched_frames": len(used),
        "dropped_frames": int(len(index) - len(used)),
        "discharges": int(used["discharge"].nunique()),
        "dt_ms_median": float(dt.median()),
        "dt_ms_p95": float(dt.quantile(0.95)),
        "dt_ms_max": float(dt.max()),
    }
    return used.reset_index(drop=True), meta


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tolerance", type=float, default=0.02)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if MATCH_PATH.exists() and not args.force:
        print(f"already exists: {MATCH_PATH}")
        return

    eq = load_equilibrium()
    index = pd.read_csv(INDEX_PATH)
    out, meta = match_frames(eq, index, args.tolerance)
    out.to_csv(MATCH_PATH, index=False)
    MATCH_META_PATH.write_text(json.dumps(meta, indent=2))

    print(json.dumps(meta, indent=2))
    print(f"saved: {MATCH_PATH} ({MATCH_PATH.stat().st_size / 1e6:.1f} MB)")
    print(f"saved: {MATCH_META_PATH}")


if __name__ == "__main__":
    main()
