from __future__ import annotations

import argparse
import json
import time
import warnings
from typing import Any

import joblib
import numpy as np
import pandas as pd

from .config import (
    CLASSIFICATION_TARGET,
    FEATURES,
    LIMITER_TARGETS,
    METRICS_PATH,
    MODEL_PATH,
    SEED,
    SPLIT_PATH,
    TARGETS,
    TEST_FRAC,
    XPOINT_TARGETS,
)
from .data import check_split, load_equilibrium, save_split, split_by_discharge
from .limiter import fit_limiter_models, predict_limiter
from .metrics import classification_report, regression_report
from .models import build_classifier, build_regressor

warnings.filterwarnings("ignore")

ModelBundle = dict[str, Any]


def fit_regressor(
    train: pd.DataFrame, test: pd.DataFrame, targets: list[str]
) -> tuple[Any, np.ndarray, np.ndarray]:
    mask_tr = train[targets].notna().all(axis=1)
    mask_te = test[targets].notna().all(axis=1)
    model = build_regressor()
    model.fit(train.loc[mask_tr, FEATURES], train.loc[mask_tr, targets])
    pred = model.predict(test.loc[mask_te, FEATURES])
    y = test.loc[mask_te, targets].to_numpy()
    return model, y, pred


def fit_classifier(
    train: pd.DataFrame, test: pd.DataFrame
) -> tuple[Any, np.ndarray, np.ndarray, np.ndarray]:
    model = build_classifier()
    model.fit(train[FEATURES], train[CLASSIFICATION_TARGET])
    pred = np.asarray(model.predict(test[FEATURES]))
    prob_raw = model.predict_proba(test[FEATURES])
    assert prob_raw is not None
    prob = np.asarray(prob_raw)[:, 1]
    y = np.asarray(test[CLASSIFICATION_TARGET].to_numpy())
    return model, y, pred, prob


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--noisy", action="store_true", help="load noisy magnetic data")
    args = parser.parse_args()

    df = load_equilibrium(noisy=args.noisy)
    train, test, split = split_by_discharge(df, TEST_FRAC, SEED)
    check_split(train, test, len(df))
    save_split(split)

    t0 = time.perf_counter()

    shape_model, y_shape, p_shape = fit_regressor(train, test, TARGETS)
    xpoint_model, y_xpoint, p_xpoint = fit_regressor(train, test, XPOINT_TARGETS)
    limited_model, y_limited, p_limited, prob_limited = fit_classifier(train, test)

    limiter_mask_tr = train[LIMITER_TARGETS].notna().all(axis=1)
    limiter_mask_te = test[LIMITER_TARGETS].notna().all(axis=1)
    limiter_models = fit_limiter_models(train.loc[limiter_mask_tr])
    p_r, p_z = predict_limiter(limiter_models, test.loc[limiter_mask_te, FEATURES])
    p_limiter = np.column_stack([p_r, p_z])
    y_limiter = test.loc[limiter_mask_te, LIMITER_TARGETS].to_numpy()

    train_time = time.perf_counter() - t0

    report: dict[str, Any] = {
        "shape": regression_report(y_shape, p_shape, TARGETS),
        "xpoint": regression_report(y_xpoint, p_xpoint, XPOINT_TARGETS),
        "limiter": regression_report(y_limiter, p_limiter, LIMITER_TARGETS),
        "is_limited": classification_report(y_limited, p_limited, prob_limited),
        "train_time_s": train_time,
    }

    print("\n=== shape ===")
    for row in report["shape"]:
        print(f"{row['target']:20s} MAE={row['MAE']:.6f} R2={row['R2']:.4f}")

    print("\n=== x-point / strike points (diverted rows) ===")
    for row in report["xpoint"]:
        print(f"{row['target']:20s} MAE={row['MAE']:.6f} R2={row['R2']:.4f}")

    print("\n=== limiter (limited rows, two-stage) ===")
    for row in report["limiter"]:
        print(f"{row['target']:20s} MAE={row['MAE']:.6f} R2={row['R2']:.4f}")

    cls = report["is_limited"]
    print(
        f"\n=== is_limited ===\n"
        f"accuracy={cls['accuracy']:.4f} balanced_accuracy={cls['balanced_accuracy']:.4f} "
        f"f1={cls['f1']:.4f} roc_auc={cls['roc_auc']:.4f}"
    )

    models: ModelBundle = {
        "shape": shape_model,
        "xpoint": xpoint_model,
        "limiter": limiter_models,
        "is_limited": limited_model,
    }
    x = test[FEATURES].to_numpy()

    for _ in range(20):
        shape_model.predict(x[:1])
        xpoint_model.predict(x[:1])
        limited_model.predict(x[:1])
        predict_limiter(limiter_models, test[FEATURES].iloc[:1])

    reps = 300
    t0 = time.perf_counter()
    for _ in range(reps):
        shape_model.predict(x[:1])
        xpoint_model.predict(x[:1])
        limited_model.predict(x[:1])
        predict_limiter(limiter_models, test[FEATURES].iloc[:1])
    report["latency_ms"] = (time.perf_counter() - t0) / reps * 1e3
    print(f"\nlatency (all models, 1 sample): {report['latency_ms']:.3f} ms")
    print(f"train time: {train_time:.1f} s")

    joblib.dump(models, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(report, indent=2))
    print(f"\nsaved: {MODEL_PATH}")
    print(f"saved: {METRICS_PATH}")
    print(f"saved: {SPLIT_PATH}")


if __name__ == "__main__":
    main()
