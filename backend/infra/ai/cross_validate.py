from __future__ import annotations

import argparse
import json
import warnings
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from .config import ARTIFACTS_DIR, CAMERA_CSV, FEATURES, TARGETS
from .data import add_mode_features, attach_mode, load_equilibrium
from .metrics import regression_report
from .models import build_regressor

warnings.filterwarnings("ignore")


def fold_mae(
    train: pd.DataFrame, test: pd.DataFrame, features: list[str]
) -> dict[str, float]:
    mask_tr = train[TARGETS].notna().all(axis=1)
    mask_te = test[TARGETS].notna().all(axis=1)
    model = build_regressor()
    model.fit(train.loc[mask_tr, features], train.loc[mask_tr, TARGETS])
    pred = model.predict(test.loc[mask_te, features])
    y = test.loc[mask_te, TARGETS].to_numpy()
    return {
        str(r["target"]): float(r["MAE"]) for r in regression_report(y, pred, TARGETS)
    }


def summarize(fold_results: list[dict[str, float]]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for target in TARGETS:
        values = np.array([fold[target] for fold in fold_results])
        out[target] = {"mean": float(values.mean()), "std": float(values.std())}
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-mode", action="store_true")
    parser.add_argument("--folds", type=int, default=5)
    args = parser.parse_args()

    df = load_equilibrium()
    mode_cols: list[str] = []
    if args.with_mode:
        df = attach_mode(df, pd.read_csv(CAMERA_CSV))
        df = df[df["mode"].notna()].reset_index(drop=True)
        df, mode_cols = add_mode_features(df)

    groups = df["discharge"].to_numpy()
    gkf = GroupKFold(n_splits=args.folds)

    base_results: list[dict[str, float]] = []
    mode_results: list[dict[str, float]] = []
    for i, (tr_idx, te_idx) in enumerate(gkf.split(df, groups=groups)):
        train = df.iloc[tr_idx].reset_index(drop=True)
        test = df.iloc[te_idx].reset_index(drop=True)
        assert not (set(train["discharge"]) & set(test["discharge"]))
        base_results.append(fold_mae(train, test, FEATURES))
        if args.with_mode:
            mode_results.append(fold_mae(train, test, FEATURES + mode_cols))
        print(f"fold {i + 1}/{args.folds} done", flush=True)

    base = summarize(base_results)
    print(
        f"\nGroupKFold({args.folds}) on {df['discharge'].nunique()} discharges, "
        f"{len(df)} rows"
    )
    payload: dict[str, Any]
    if args.with_mode:
        mode = summarize(mode_results)
        print(f"\n{'target':22s} {'MAE base':>18s} {'MAE +mode':>18s} {'delta':>8s}")
        for target in TARGETS:
            b, m = base[target], mode[target]
            delta = (m["mean"] - b["mean"]) / b["mean"] * 100
            print(
                f"{target:22s} {b['mean']:.6f}+/-{b['std']:.6f} "
                f"{m['mean']:.6f}+/-{m['std']:.6f} {delta:+7.2f}%"
            )
        deltas = [
            (mode[t]["mean"] - base[t]["mean"]) / base[t]["mean"] * 100 for t in TARGETS
        ]
        print(f"\nmean MAE change: {np.mean(deltas):+.2f}%")
        payload = {
            "base": base,
            "with_mode": mode,
            "mean_delta_pct": float(np.mean(deltas)),
        }
        path = ARTIFACTS_DIR / "cv_mode.json"
    else:
        print(f"\n{'target':22s} {'MAE mean':>12s} {'std':>10s}")
        for target in TARGETS:
            print(
                f"{target:22s} {base[target]['mean']:12.6f} {base[target]['std']:10.6f}"
            )
        payload = {"base": base}
        path = ARTIFACTS_DIR / "cv_magnetic.json"

    path.write_text(json.dumps(payload, indent=2))
    print(f"\nsaved: {path}")


if __name__ == "__main__":
    main()
