from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .config import EQUIL_PATH, SPLIT_PATH


def main() -> None:
    split: dict[str, object] = json.loads(SPLIT_PATH.read_text())
    df = pd.read_csv(EQUIL_PATH)

    train_d: set[int] = {int(d) for d in split["train_discharges"]}  # type: ignore[union-attr]
    test_d: set[int] = {int(d) for d in split["test_discharges"]}  # type: ignore[union-attr]

    print(f"split file: {SPLIT_PATH}")
    print(f"data file:  {EQUIL_PATH}")
    print(f"seed: {split['seed']}  test_frac: {split['test_frac']}")
    print()
    print(f"train discharges: {len(train_d)}")
    print(f"test discharges:  {len(test_d)}")
    print(f"test list: {sorted(test_d)}")
    print()

    overlap = train_d & test_d
    print(f"overlap (must be empty): {overlap}")
    assert not overlap, "LEAKAGE: same discharge in train and test"

    all_d: set[int] = {int(d) for d in df["discharge"].unique()}
    print(f"discharges covered: {len(train_d | test_d)} / {len(all_d)}")
    assert train_d | test_d == all_d, "some discharges are missing from the split"

    discharge_values = df["discharge"].to_numpy()
    train_rows = int(np.count_nonzero(np.isin(discharge_values, list(train_d))))
    test_rows = int(np.count_nonzero(np.isin(discharge_values, list(test_d))))
    print(f"rows train: {train_rows}")
    print(f"rows test:  {test_rows}")
    print(f"rows total: {len(df)} (train+test = {train_rows + test_rows})")
    assert train_rows + test_rows == len(df)

    example = min(test_d)
    n_example = int(np.count_nonzero(discharge_values == example))
    print()
    print(f"example discharge {example}:")
    print(f"  rows in data:  {n_example}")
    print(f"  rows in train: {n_example if example in train_d else 0}")
    print(f"  rows in test:  {n_example if example in test_d else 0}")

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
