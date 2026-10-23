from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from .config import EQUIL_NOISY_PATH, EQUIL_PATH, SPLIT_PATH


def canonicalize_strike_points(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure strike point 1 always has the smaller R coordinate."""
    r1 = df["R_strike_point_1"]
    r2 = df["R_strike_point_2"]
    z1 = df["Z_strike_point_1"]
    z2 = df["Z_strike_point_2"]
    swap = (r1 > r2) & r1.notna() & r2.notna()

    out = df.copy()
    out.loc[swap, "R_strike_point_1"] = r2[swap]
    out.loc[swap, "Z_strike_point_1"] = z2[swap]
    out.loc[swap, "R_strike_point_2"] = r1[swap]
    out.loc[swap, "Z_strike_point_2"] = z1[swap]
    return out


def load_equilibrium(noisy: bool = False, canonicalize: bool = True) -> pd.DataFrame:
    path: Path = EQUIL_NOISY_PATH if noisy else EQUIL_PATH
    df = pd.read_csv(path)
    if canonicalize:
        df = canonicalize_strike_points(df)
    return df


def split_by_discharge(
    df: pd.DataFrame, test_frac: float = 0.2, seed: int = 0
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    uniq: np.ndarray = np.array(sorted(df["discharge"].unique()))
    rng = np.random.default_rng(seed)
    rng.shuffle(uniq)
    n_test = max(1, int(round(len(uniq) * test_frac)))  # noqa: RUF046

    test_discharges: list[int] = sorted(int(d) for d in uniq[:n_test])
    train_discharges: list[int] = sorted(int(d) for d in uniq[n_test:])

    train = df[df["discharge"].isin(train_discharges)].reset_index(drop=True)
    test = df[df["discharge"].isin(test_discharges)].reset_index(drop=True)

    split: dict[str, Any] = {
        "seed": seed,
        "test_frac": test_frac,
        "train_discharges": train_discharges,
        "test_discharges": test_discharges,
    }
    return train, test, split


def save_split(split: dict[str, Any], path: Path = SPLIT_PATH) -> None:
    path.write_text(json.dumps(split, indent=2))


def load_split(path: Path = SPLIT_PATH) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text()))


def check_split(train: pd.DataFrame, test: pd.DataFrame, total: int) -> None:
    overlap = set(train["discharge"]) & set(test["discharge"])
    assert not overlap, f"discharge overlap between train and test: {overlap}"
    assert len(train) + len(test) == total, "some rows were lost during the split"
    print(
        f"rozdělení OK: train={len(train)} řádků / {train.discharge.nunique()} výbojů, "
        f"test={len(test)} řádků / {test.discharge.nunique()} výbojů"
    )


def attach_mode(
    eq: pd.DataFrame, cam: pd.DataFrame, tolerance: float = 0.01
) -> pd.DataFrame:
    """Attach camera `mode` to equilibrium rows by nearest frame time per discharge."""
    common: list[int] = sorted(set(eq["discharge"]) & set(cam["discharge"]))
    parts: list[pd.DataFrame] = []
    for discharge in common:
        left = eq[eq["discharge"] == discharge].sort_values("time")
        right = cam[cam["discharge"] == discharge].sort_values("time")[["time", "mode"]]
        parts.append(
            pd.merge_asof(
                left,
                right,
                on="time",
                direction="nearest",
                tolerance=tolerance,  # pyright: ignore[reportArgumentType]
            )
        )
    return pd.concat(parts, ignore_index=True)


def add_mode_features(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    dummies = pd.get_dummies(df["mode"], prefix="mode")
    mode_cols: list[str] = [str(c) for c in dummies.columns]
    out = pd.concat([df.reset_index(drop=True), dummies.reset_index(drop=True)], axis=1)
    return out, mode_cols
