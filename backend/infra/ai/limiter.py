from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .config import FEATURES
from .models import build_classifier, build_regressor

INNER_R_MAX: float = 0.35
INNER_R_VALUE: float = 0.347


def is_inner_limiter(r_limiter: pd.Series) -> np.ndarray:
    return (r_limiter <= INNER_R_MAX).to_numpy()


def fit_limiter_models(train: pd.DataFrame) -> dict[str, Any]:
    inner = is_inner_limiter(train["R_limiter"])
    non_inner = ~inner

    inner_classifier = build_classifier()
    inner_classifier.fit(train[FEATURES], inner.astype(int))

    r_noninner = build_regressor()
    r_noninner.fit(train.loc[non_inner, FEATURES], train.loc[non_inner, "R_limiter"])

    z_inner = build_regressor()
    z_inner.fit(train.loc[inner, FEATURES], train.loc[inner, "Z_limiter"])

    z_noninner = build_regressor()
    z_noninner.fit(train.loc[non_inner, FEATURES], train.loc[non_inner, "Z_limiter"])

    return {
        "inner_classifier": inner_classifier,
        "r_noninner": r_noninner,
        "z_inner": z_inner,
        "z_noninner": z_noninner,
    }


def predict_limiter(
    models: dict[str, Any], features: pd.DataFrame
) -> tuple[np.ndarray, np.ndarray]:
    inner = np.asarray(models["inner_classifier"].predict(features)).astype(bool)
    r = np.where(
        inner, INNER_R_VALUE, np.asarray(models["r_noninner"].predict(features))
    )
    z = np.where(
        inner,
        np.asarray(models["z_inner"].predict(features)),
        np.asarray(models["z_noninner"].predict(features)),
    )
    return np.asarray(r, dtype=float), np.asarray(z, dtype=float)
