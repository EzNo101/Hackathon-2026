from __future__ import annotations

import json
import warnings
from typing import Any

import numpy as np
import pandas as pd

from .config import ARTIFACTS_DIR, CAMERA_CSV, FEATURES, TARGETS
from .data import add_mode_features, attach_mode, load_equilibrium
from .metrics import regression_report
from .models import build_regressor

warnings.filterwarnings("ignore")


def evaluate(
    train: pd.DataFrame, test: pd.DataFrame, features: list[str]
) -> dict[str, dict[str, Any]]:
    mask_tr = train[TARGETS].notna().all(axis=1)
    mask_te = test[TARGETS].notna().all(axis=1)
    model = build_regressor()
    model.fit(train.loc[mask_tr, features], train.loc[mask_tr, TARGETS])
    pred = model.predict(test.loc[mask_te, features])
    y = test.loc[mask_te, TARGETS].to_numpy()
    return {str(r["target"]): r for r in regression_report(y, pred, TARGETS)}


def main() -> None:
    split: dict[str, Any] = json.loads((ARTIFACTS_DIR / "split.json").read_text())
    eq = load_equilibrium()
    cam = pd.read_csv(CAMERA_CSV)

    df = attach_mode(eq, cam)
    df = df[df["mode"].notna()].reset_index(drop=True)
    df, mode_cols = add_mode_features(df)
    print(f"rows with mode: {len(df)}")
    print(f"discharges with mode: {df['discharge'].nunique()}")
    print(f"mode counts:\n{df['mode'].value_counts().to_string()}\n")

    train = df[df["discharge"].isin(split["train_discharges"])].reset_index(drop=True)
    test = df[df["discharge"].isin(split["test_discharges"])].reset_index(drop=True)
    print(f"train: {len(train)} rows / {train['discharge'].nunique()} discharges")
    print(f"test:  {len(test)} rows / {test['discharge'].nunique()} discharges\n")

    assert not (set(train["discharge"]) & set(test["discharge"]))
    assert len(train) > 0 and len(test) > 0

    base = evaluate(train, test, FEATURES)
    with_mode = evaluate(train, test, FEATURES + mode_cols)

    print(
        f"{'target':22s} {'MAE base':>10s} {'MAE +mode':>11s} "
        f"{'change':>9s} {'R2 base':>9s} {'R2 +mode':>9s}"
    )
    for target in TARGETS:
        b, m = base[target], with_mode[target]
        change = (float(m["MAE"]) - float(b["MAE"])) / float(b["MAE"]) * 100
        print(
            f"{target:22s} {float(b['MAE']):10.6f} {float(m['MAE']):11.6f} "
            f"{change:+8.2f}% {float(b['R2']):9.4f} {float(m['R2']):9.4f}"
        )

    mean_change = float(
        np.mean(
            [
                (float(with_mode[t]["MAE"]) - float(base[t]["MAE"]))
                / float(base[t]["MAE"])
                * 100
                for t in TARGETS
            ]
        )
    )
    print(f"\nmean MAE change across targets: {mean_change:+.2f}%")

    out: dict[str, Any] = {
        "n_rows": len(df),
        "n_train": len(train),
        "n_test": len(test),
        "base": base,
        "with_mode": with_mode,
        "mean_mae_change_pct": mean_change,
    }
    path = ARTIFACTS_DIR / "mode_comparison.json"
    path.write_text(json.dumps(out, indent=2))
    print(f"saved: {path}")


if __name__ == "__main__":
    main()
