from __future__ import annotations

import json
import time
from typing import Any

import numpy as np
import pandas as pd

from .config import ARTIFACTS_DIR, FEATURES, SEED, TARGETS, TEST_FRAC
from .data import load_equilibrium, split_by_discharge
from .metrics import regression_report
from .models import build_regressor

SHAPE_TARGETS: list[str] = [t for t in TARGETS if t != "plasma_current"]
OUT_PATH = ARTIFACTS_DIR / "magnetic_ablation.json"


def mean_shape_mae(y: np.ndarray, p: np.ndarray) -> float:
    rows = regression_report(y, p, SHAPE_TARGETS)
    return float(np.mean([r["MAE"] for r in rows]))


def fit_eval(
    train: pd.DataFrame, test: pd.DataFrame, features: list[str]
) -> dict[str, Any]:
    mask_tr = train[SHAPE_TARGETS].notna().all(axis=1)
    mask_te = test[SHAPE_TARGETS].notna().all(axis=1)
    model = build_regressor()
    t0 = time.perf_counter()
    model.fit(train.loc[mask_tr, features], train.loc[mask_tr, SHAPE_TARGETS])
    train_time = time.perf_counter() - t0
    p = np.asarray(model.predict(test.loc[mask_te, features]))
    y = test.loc[mask_te, SHAPE_TARGETS].to_numpy()
    rows = regression_report(y, p, SHAPE_TARGETS)
    return {
        "features": features,
        "n_features": len(features),
        "mean_shape_MAE": float(np.mean([r["MAE"] for r in rows])),
        "per_target": rows,
        "train_time_s": train_time,
    }


def main() -> None:
    np.random.seed(SEED)
    df = load_equilibrium()
    train, test, _ = split_by_discharge(df, TEST_FRAC, SEED)
    ipr = [f for f in FEATURES if f.startswith("IPR")]
    fl = [f for f in FEATURES if f.startswith("FL")]

    print("=== magnetic input ablation ===")
    base = fit_eval(train, test, FEATURES)
    print(f"all 24      mean shape MAE={base['mean_shape_MAE']:.6f}")
    results: dict[str, Any] = {"all": base}

    for name, subset in [("IPR only", ipr), ("FL only", fl)]:
        row = fit_eval(train, test, subset)
        results[name] = row
        print(f"{name:12s} mean shape MAE={row['mean_shape_MAE']:.6f}")

    # Permutation importance of the full model on the test set.
    print("\ncomputing permutation importance")
    mask_tr = train[SHAPE_TARGETS].notna().all(axis=1)
    mask_te = test[SHAPE_TARGETS].notna().all(axis=1)
    full = build_regressor()
    full.fit(train.loc[mask_tr, FEATURES], train.loc[mask_tr, SHAPE_TARGETS])
    x_test = test.loc[mask_te, FEATURES].to_numpy()
    y_test = test.loc[mask_te, SHAPE_TARGETS].to_numpy()
    baseline = mean_shape_mae(y_test, np.asarray(full.predict(x_test)))
    rng = np.random.default_rng(SEED)
    importance: dict[str, float] = {}
    for j, name in enumerate(FEATURES):
        deltas = []
        for _ in range(5):
            x_perm = x_test.copy()
            rng.shuffle(x_perm[:, j])
            deltas.append(mean_shape_mae(y_test, np.asarray(full.predict(x_perm))) - baseline)
        importance[name] = float(np.mean(deltas))
        print(f"  {name:6s} delta MAE={importance[name]:+.6f}")

    order = sorted(importance, key=lambda k: importance[k], reverse=True)
    topk: dict[str, Any] = {}
    for k in [2, 4, 6, 8, 12, 16, 24]:
        subset = order[:k]
        row = fit_eval(train, test, subset)
        topk[str(k)] = row
        print(f"top-{k:2d}      mean shape MAE={row['mean_shape_MAE']:.6f}")

    payload: dict[str, Any] = {
        "baseline_mean_shape_MAE": baseline,
        "groups": results,
        "permutation_importance": importance,
        "importance_order": order,
        "top_k": topk,
        "note": "single fixed train/test split by discharge; MAE averaged over 9 shape targets",
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2))
    print(f"\nsaved: {OUT_PATH}")


if __name__ == "__main__":
    main()
