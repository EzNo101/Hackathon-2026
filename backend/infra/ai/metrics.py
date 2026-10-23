from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    roc_auc_score,
)


def regression_report(
    y_true: np.ndarray, y_pred: np.ndarray, names: list[str]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, name in enumerate(names):
        yt, yp = y_true[:, i], y_pred[:, i]
        rows.append(
            {
                "target": name,
                "n": len(yt),
                "MAE": float(mean_absolute_error(yt, yp)),
                "RMSE": float(np.sqrt(mean_squared_error(yt, yp))),
                "R2": float(r2_score(yt, yp)),
            }
        )
    return rows


def classification_report(
    y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray
) -> dict[str, Any]:
    return {
        "n": len(y_true),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "f1": float(f1_score(y_true, y_pred)),
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
    }
