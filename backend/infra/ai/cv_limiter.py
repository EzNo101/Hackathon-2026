from __future__ import annotations

import json
import warnings
from typing import Any

import numpy as np
from sklearn.model_selection import GroupKFold

from .config import ARTIFACTS_DIR, FEATURES, LIMITER_TARGETS
from .data import load_equilibrium
from .limiter import fit_limiter_models, predict_limiter
from .models import build_regressor

warnings.filterwarnings("ignore")


def main() -> None:
    df = load_equilibrium()
    limiter = df[df[LIMITER_TARGETS].notna().all(axis=1)].reset_index(drop=True)
    groups = limiter["discharge"].to_numpy()

    gkf = GroupKFold(n_splits=5)
    baseline: list[dict[str, float]] = []
    two_stage: list[dict[str, float]] = []

    for i, (tr_idx, te_idx) in enumerate(gkf.split(limiter, groups=groups)):
        train = limiter.iloc[tr_idx].reset_index(drop=True)
        test = limiter.iloc[te_idx].reset_index(drop=True)
        assert not (set(train["discharge"]) & set(test["discharge"]))

        y = test[LIMITER_TARGETS].to_numpy()

        base_model = build_regressor()
        base_model.fit(train[FEATURES], train[LIMITER_TARGETS])
        p_base = np.asarray(base_model.predict(test[FEATURES]))
        base_mae = np.abs(p_base - y).mean(axis=0)

        limiter_models = fit_limiter_models(train)
        p_r, p_z = predict_limiter(limiter_models, test[FEATURES])
        two_mae = np.abs(np.column_stack([p_r, p_z]) - y).mean(axis=0)

        baseline.append(
            {"R_limiter": float(base_mae[0]), "Z_limiter": float(base_mae[1])}
        )
        two_stage.append(
            {"R_limiter": float(two_mae[0]), "Z_limiter": float(two_mae[1])}
        )
        print(
            f"fold {i + 1}: baseline R={base_mae[0]:.5f} Z={base_mae[1]:.5f} | "
            f"two-stage R={two_mae[0]:.5f} Z={two_mae[1]:.5f}"
        )

    def summary(results: list[dict[str, float]]) -> dict[str, dict[str, float]]:
        out: dict[str, dict[str, float]] = {}
        for target in LIMITER_TARGETS:
            values = np.array([r[target] for r in results])
            out[target] = {"mean": float(values.mean()), "std": float(values.std())}
        return out

    base_sum = summary(baseline)
    two_sum = summary(two_stage)

    print("\n=== summary ===")
    for target in LIMITER_TARGETS:
        b, t = base_sum[target], two_sum[target]
        delta = (t["mean"] - b["mean"]) / b["mean"] * 100
        print(
            f"{target:12s} baseline {b['mean']:.5f}+/-{b['std']:.5f}  "
            f"two-stage {t['mean']:.5f}+/-{t['std']:.5f}  {delta:+.1f}%"
        )

    payload: dict[str, Any] = {"baseline": base_sum, "two_stage": two_sum}
    path = ARTIFACTS_DIR / "cv_limiter.json"
    path.write_text(json.dumps(payload, indent=2))
    print(f"\nsaved: {path}")


if __name__ == "__main__":
    main()
