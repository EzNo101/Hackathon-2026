from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import Dataset

from .config import SPLIT_PATH
from .prepare_camera import CACHE_PATH, CLASSES, INDEX_PATH, META_PATH

LABEL_TO_INDEX: dict[str, int] = {name: i for i, name in enumerate(CLASSES)}


class CameraFrames(Dataset[tuple[torch.Tensor, int]]):
    def __init__(
        self,
        rows: np.ndarray,
        labels: np.ndarray,
        mean: np.ndarray,
        std: np.ndarray,
    ) -> None:
        self.rows = rows.astype(np.int64)
        self.labels = labels.astype(np.int64)
        self.mean = mean.astype(np.float32)
        self.std = std.astype(np.float32)
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

    def __getitem__(self, i: int) -> tuple[torch.Tensor, int]:
        row = int(self.rows[i])
        img = np.asarray(self.cache[row], dtype=np.float32) / 255.0
        img = (img - self.mean) / self.std
        x = torch.from_numpy(np.ascontiguousarray(img.transpose(2, 0, 1)))
        return x, int(self.labels[i])


class SmallCNN(nn.Module):
    def __init__(self, n_classes: int = len(CLASSES)) -> None:
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
            nn.Conv2d(128, 128, 3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d(1),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(0.3),
            nn.Linear(128, n_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.features(x))


def load_camera_index() -> tuple[pd.DataFrame, np.ndarray, np.ndarray, dict[str, Any]]:
    index = pd.read_csv(INDEX_PATH)
    meta: dict[str, Any] = json.loads(META_PATH.read_text())
    mean = np.asarray(meta["mean"], dtype=np.float32)
    std = np.asarray(meta["std"], dtype=np.float32)
    return index, mean, std, meta


def split_camera_index(
    index: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    split: dict[str, Any] = json.loads(SPLIT_PATH.read_text())
    train_d: set[int] = {int(d) for d in split["train_discharges"]}
    test_d: set[int] = {int(d) for d in split["test_discharges"]}

    train = index[index["discharge"].isin(train_d)].reset_index(drop=True)
    test = index[index["discharge"].isin(test_d)].reset_index(drop=True)
    assert not (set(train["discharge"]) & set(test["discharge"]))
    return train, test, split
