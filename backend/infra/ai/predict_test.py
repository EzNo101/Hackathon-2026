from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from .config import (
    ARTIFACTS_DIR,
    CLASSIFICATION_TARGET,
    EQUIL_PATH,
    FEATURES,
    LIMITER_TARGETS,
    MODEL_PATH,
    TARGETS,
    XPOINT_TARGETS,
)
from .limiter import predict_limiter


def assign_predictions(
    out: pd.DataFrame,
    test: pd.DataFrame,
    mask: pd.Series,
    targets: list[str],
    pred: np.ndarray,
) -> None:
    for i, target in enumerate(targets):
        out[f"{target}_true"] = pd.NA
        out[f"{target}_pred"] = pd.NA
        out.loc[mask, f"{target}_true"] = test.loc[mask, target].to_numpy()
        out.loc[mask, f"{target}_pred"] = pred[:, i]


def main() -> None:
    split: dict[str, Any] = json.loads((ARTIFACTS_DIR / "split.json").read_text())
    df = pd.read_csv(EQUIL_PATH)
    test = df[df["discharge"].isin(split["test_discharges"])].reset_index(drop=True)

    models: dict[str, Any] = joblib.load(MODEL_PATH)

    out = test[["discharge", "time"]].copy()

    for group, targets in (("shape", TARGETS), ("xpoint", XPOINT_TARGETS)):
        mask = test[targets].notna().all(axis=1)
        pred = np.asarray(models[group].predict(test.loc[mask, FEATURES]))
        assign_predictions(out, test, mask, targets, pred)

    limiter_mask = test[LIMITER_TARGETS].notna().all(axis=1)
    p_r, p_z = predict_limiter(models["limiter"], test.loc[limiter_mask, FEATURES])
    assign_predictions(
        out, test, limiter_mask, LIMITER_TARGETS, np.column_stack([p_r, p_z])
    )

    out[f"{CLASSIFICATION_TARGET}_true"] = test[CLASSIFICATION_TARGET].to_numpy()
    out[f"{CLASSIFICATION_TARGET}_pred"] = models["is_limited"].predict(test[FEATURES])

    path: Path = ARTIFACTS_DIR / "test_predictions.csv"
    out.to_csv(path, index=False)

    print(f"test rows: {len(test)}")
    for group, targets in (("shape", TARGETS), ("xpoint", XPOINT_TARGETS)):
        print(f"{group} predictions: {test[targets].notna().all(axis=1).sum()}")
    print(f"limiter predictions: {int(limiter_mask.sum())}")
    print(f"saved: {path}")


if __name__ == "__main__":
    main()
