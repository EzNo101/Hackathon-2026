from __future__ import annotations

import json
import time
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import TransformedTargetRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler

from .camera_image import FEATURE_PATH
from .camera_shape import discharge_split, load_camera_targets
from .config import CAMERA_METRICS_PATH, CAMERA_MODEL_PATH, CLASSIFICATION_TARGET, SEED
from .targets import EXTRA_TARGETS, GROUPS, MAIN_17, UNITS


def fit_target(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    y_val: np.ndarray,
) -> tuple[Any, float]:
    mask_tr = np.isfinite(y_train)
    mask_val = np.isfinite(y_val)
    if mask_tr.sum() < 50:
        raise ValueError(f"not enough labelled rows ({mask_tr.sum()})")
    best_alpha = 100.0
    best_mae = float("inf")
    best_model: Any = None
    for alpha in [1.0, 10.0, 100.0, 300.0]:
        model = TransformedTargetRegressor(
            regressor=make_pipeline(StandardScaler(), Ridge(alpha=alpha)),
            transformer=StandardScaler(),
        )
        model.fit(x_train[mask_tr], y_train[mask_tr])
        if mask_val.sum() == 0:
            best_model, best_alpha = model, alpha
            break
        p = np.asarray(model.predict(x_val[mask_val]))
        mae = float(mean_absolute_error(y_val[mask_val], p))
        if mae < best_mae:
            best_mae, best_alpha, best_model = mae, alpha, model
    assert best_model is not None
    return best_model, best_alpha


def main() -> None:
    np.random.seed(SEED)
    df, _mean, _std = load_camera_targets()
    train, val, test, info = discharge_split(df)
    features = np.load(FEATURE_PATH)
    row_to_index = {int(r): i for i, r in enumerate(df["row"].to_numpy())}

    def fi(part: pd.DataFrame) -> np.ndarray:
        return features[np.asarray([row_to_index[int(r)] for r in part["row"].to_numpy()])]

    x_train, x_val, x_test = fi(train), fi(val), fi(test)
    print(
        f"frames: train={len(train):,}/{train.discharge.nunique()} "
        f"val={len(val):,}/{val.discharge.nunique()} "
        f"test={len(test):,}/{test.discharge.nunique()}"
    )

    models: dict[str, Any] = {}
    metrics: dict[str, Any] = {}
    t0 = time.perf_counter()

    for target in MAIN_17 + EXTRA_TARGETS:
        if target not in df.columns:
            print(f"  {target:26s} SKIP (not in camera target table)")
            continue
        y_train = train[target].to_numpy(dtype=np.float64)
        y_val = val[target].to_numpy(dtype=np.float64)
        y_test = test[target].to_numpy(dtype=np.float64)
        mask_test = np.isfinite(y_test)
        try:
            model, alpha = fit_target(x_train, y_train, x_val, y_val)
        except ValueError as exc:
            print(f"  {target:26s} SKIP ({exc})")
            continue
        p = np.asarray(model.predict(x_test[mask_test]))
        yt = y_test[mask_test]
        row: dict[str, Any] = {
            "n_train": int(np.isfinite(y_train).sum()),
            "n_test": int(mask_test.sum()),
            "alpha": alpha,
            "MAE": float(mean_absolute_error(yt, p)),
            "RMSE": float(np.sqrt(mean_squared_error(yt, p))),
            "R2": float(r2_score(yt, p)) if len(yt) > 1 else None,
            "unit": UNITS.get(target, "-"),
            "group": GROUPS.get(target, "other"),
        }
        models[target] = model
        metrics[target] = row
        print(
            f"  {target:26s} n={row['n_test']:6d} MAE={row['MAE']:.6f} "
            f"R2={row['R2'] if row['R2'] is None else round(row['R2'], 4)}"
        )

    # Regime classifier (needed to decide which fields are physically valid).
    y_train_cls = train[CLASSIFICATION_TARGET].astype(int).to_numpy()
    y_val_cls = val[CLASSIFICATION_TARGET].astype(int).to_numpy()
    y_test_cls = test[CLASSIFICATION_TARGET].astype(int).to_numpy()
    best_c = 1.0
    best_bal = -1.0
    classifier: Pipeline | None = None
    for c in [0.01, 0.1, 1.0, 10.0]:
        candidate = make_pipeline(
            StandardScaler(),
            LogisticRegression(C=c, max_iter=2000, class_weight="balanced"),
        )
        candidate.fit(x_train, y_train_cls)
        bal = float(balanced_accuracy_score(y_val_cls, candidate.predict(x_val)))
        if bal > best_bal:
            best_bal, best_c, classifier = bal, c, candidate
    assert classifier is not None
    prob = classifier.predict_proba(x_test)[:, 1]
    pred = (prob >= 0.5).astype(int)
    cls_metrics = {
        "n_test": len(y_test_cls),
        "accuracy": float(accuracy_score(y_test_cls, pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_test_cls, pred)),
        "f1": float(f1_score(y_test_cls, pred)),
        "roc_auc": float(roc_auc_score(y_test_cls, prob)),
        "C": best_c,
        "val_balanced_accuracy": best_bal,
        "unit": "bool",
        "group": "regime",
    }
    print(
        f"\nis_limited: acc={cls_metrics['accuracy']:.4f} "
        f"bal={cls_metrics['balanced_accuracy']:.4f} "
        f"AUC={cls_metrics['roc_auc']:.4f}"
    )

    available = MAIN_17 + [t for t in EXTRA_TARGETS if t in models]
    extra_available = [t for t in EXTRA_TARGETS if t in models]
    payload: dict[str, Any] = {
        "model": "resnet18-imagenet features + ridge per target",
        "split": info,
        "targets": available,
        "main_17": MAIN_17,
        "extra_targets": extra_available,
        "units": UNITS,
        "groups": GROUPS,
        "regression": metrics,
        "classification": {CLASSIFICATION_TARGET: cls_metrics},
        "train_time_s": time.perf_counter() - t0,
    }
    CAMERA_METRICS_PATH.write_text(json.dumps(payload, indent=2))
    joblib.dump(
        {
            "models": models,
            "classifier": classifier,
            "targets": available,
            "main_17": MAIN_17,
            "units": UNITS,
            "groups": GROUPS,
            "alphas": {k: v["alpha"] for k, v in metrics.items()},
        },
        CAMERA_MODEL_PATH,
        compress=3,
    )
    print(f"\nsaved: {CAMERA_MODEL_PATH}")
    print(f"saved: {CAMERA_METRICS_PATH}")


if __name__ == "__main__":
    main()
