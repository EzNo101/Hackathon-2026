from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import Dataset

from .config import ARTIFACTS_DIR, SEED, SPLIT_PATH
from .prepare_camera import CACHE_PATH, META_PATH

MATCH_PATH: Path = ARTIFACTS_DIR / "camera_targets.csv"
MODEL_PATH: Path = ARTIFACTS_DIR / "camera_shape_cnn.pt"
METRICS_PATH: Path = ARTIFACTS_DIR / "camera_shape_cnn.json"
PRED_PATH: Path = ARTIFACTS_DIR / "camera_shape_test_predictions.csv"

MAG_MODEL_PATH: Path = ARTIFACTS_DIR / "camera_mag_mlp.joblib"
MAG_METRICS_PATH: Path = ARTIFACTS_DIR / "camera_mag_mlp.json"
FUSION_METRICS_PATH: Path = ARTIFACTS_DIR / "camera_fusion.json"
FUSION_PRED_PATH: Path = ARTIFACTS_DIR / "camera_fusion_test_predictions.csv"


class CameraTargets(Dataset[tuple[torch.Tensor, torch.Tensor]]):
    def __init__(
        self,
        rows: np.ndarray,
        targets: np.ndarray,
        mean: np.ndarray,
        std: np.ndarray,
        target_mean: np.ndarray,
        target_std: np.ndarray,
    ) -> None:
        self.rows = rows.astype(np.int64)
        self.targets = targets.astype(np.float32)
        self.mean = mean.astype(np.float32)
        self.std = std.astype(np.float32)
        self.target_mean = target_mean.astype(np.float32)
        self.target_std = target_std.astype(np.float32)
        self._cache: np.ndarray | None = None

    @property
    def cache(self) -> np.ndarray:
        cache = self._cache
        if cache is None:
            cache = np.load(CACHE_PATH, mmap_mode="r")
            self._cache = cache
        return cache

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, i: int) -> tuple[torch.Tensor, torch.Tensor]:
        row = int(self.rows[i])
        img = np.asarray(self.cache[row], dtype=np.float32) / 255.0
        img = (img - self.mean) / self.std
        x = torch.from_numpy(np.ascontiguousarray(img.transpose(2, 0, 1)))
        y = (self.targets[i] - self.target_mean) / self.target_std
        return x, torch.from_numpy(np.ascontiguousarray(y))


class SmallCNNRegressor(nn.Module):
    def __init__(self, n_outputs: int, width: int = 128) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(128, width, 3, padding=1),
            nn.BatchNorm2d(width),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d(1),
        )
        self.head = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(0.1),
            nn.Linear(width, width),
            nn.GELU(),
            nn.Linear(width, n_outputs),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.head(self.features(x))


def load_camera_targets() -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    meta: dict[str, Any] = json.loads(META_PATH.read_text())
    df = pd.read_csv(MATCH_PATH)
    mean = np.asarray(meta["mean"], dtype=np.float32)
    std = np.asarray(meta["std"], dtype=np.float32)
    return df, mean, std


def discharge_split(
    df: pd.DataFrame, val_frac: float = 0.15
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Return train/val/test frames, split by whole discharges."""
    split: dict[str, Any] = json.loads(SPLIT_PATH.read_text())
    test_d: set[int] = {int(d) for d in split["test_discharges"]}
    train_pool_d: list[int] = sorted(
        int(d) for d in set(df["discharge"]) - test_d
    )

    rng = np.random.default_rng(SEED)
    rng.shuffle(train_pool_d)
    n_val = max(1, round(len(train_pool_d) * val_frac))
    val_d = set(train_pool_d[:n_val])
    train_d = set(train_pool_d[n_val:])

    train = df[df["discharge"].isin(train_d)].reset_index(drop=True)
    val = df[df["discharge"].isin(val_d)].reset_index(drop=True)
    test = df[df["discharge"].isin(test_d)].reset_index(drop=True)

    info = {
        "train_discharges": sorted(train_d),
        "val_discharges": sorted(val_d),
        "test_discharges": sorted(test_d),
        "n_train": len(train),
        "n_val": len(val),
        "n_test": len(test),
    }
    assert not (train_d & val_d)
    assert not (train_d & test_d)
    assert not (val_d & test_d)
    return train, val, test, info


def build_datasets(
    train: pd.DataFrame,
    val: pd.DataFrame,
    test: pd.DataFrame,
    targets: list[str],
    mean: np.ndarray,
    std: np.ndarray,
) -> tuple[
    CameraTargets, CameraTargets, CameraTargets, np.ndarray, np.ndarray
]:
    target_mean = train[targets].to_numpy(dtype=np.float32).mean(axis=0)
    target_std = train[targets].to_numpy(dtype=np.float32).std(axis=0)
    target_std = np.where(target_std < 1e-9, 1.0, target_std)

    def make(part: pd.DataFrame) -> CameraTargets:
        return CameraTargets(
            part["row"].to_numpy(),
            part[targets].to_numpy(dtype=np.float32),
            mean,
            std,
            target_mean,
            target_std,
        )

    return make(train), make(val), make(test), target_mean, target_std


def load_split_info() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(SPLIT_PATH.read_text()))
