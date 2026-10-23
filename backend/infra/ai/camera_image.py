from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
from torchvision.models import ResNet18_Weights, resnet18

from .camera_shape import load_camera_targets
from .config import ARTIFACTS_DIR
from .prepare_camera import CACHE_PATH

FEATURE_PATH: Path = ARTIFACTS_DIR / "camera_features_resnet18.npy"
FEATURE_META_PATH: Path = ARTIFACTS_DIR / "camera_features_resnet18.json"

IMAGE_MODEL_PATH: Path = ARTIFACTS_DIR / "camera_image_ridge.joblib"
IMAGE_METRICS_PATH: Path = ARTIFACTS_DIR / "camera_image_metrics.json"
IMAGE_PRED_PATH: Path = ARTIFACTS_DIR / "camera_image_test_predictions.csv"

FUSION_MODEL_PATH: Path = ARTIFACTS_DIR / "camera_fusion_ridge.joblib"
FUSION_METRICS_PATH: Path = ARTIFACTS_DIR / "camera_multimodal_metrics.json"
FUSION_PRED_PATH: Path = ARTIFACTS_DIR / "camera_multimodal_test_predictions.csv"

RESIZE: int = 128
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def _build_encoder(device: torch.device) -> torch.nn.Module:
    model = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
    model.fc = torch.nn.Identity()  # pyright: ignore[reportAttributeAccessIssue]
    model.eval()
    return model.to(device)


def extract_features(
    rows: np.ndarray,
    batch_size: int = 128,
    device: torch.device | None = None,
    force: bool = False,
    cache_path: Path = FEATURE_PATH,
) -> np.ndarray:
    if cache_path.exists() and not force:
        return np.load(cache_path)

    if device is None:
        device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    encoder = _build_encoder(device)
    cache = np.load(CACHE_PATH, mmap_mode="r")
    mean = torch.from_numpy(IMAGENET_MEAN).to(device).view(1, 3, 1, 1)
    std = torch.from_numpy(IMAGENET_STD).to(device).view(1, 3, 1, 1)

    out: list[np.ndarray] = []
    t0 = time.perf_counter()
    with torch.no_grad():
        for start in range(0, len(rows), batch_size):
            batch = np.asarray(cache[rows[start : start + batch_size].astype(int)])
            x = torch.from_numpy(batch.astype(np.float32) / 255.0).permute(0, 3, 1, 2)
            x = F.interpolate(
                x.to(device), size=(RESIZE, RESIZE), mode="bilinear", align_corners=False
            )
            out.append(encoder((x - mean) / std).cpu().numpy())
            if start % (batch_size * 40) == 0:
                done = min(start + batch_size, len(rows))
                print(f"  features {done:,}/{len(rows):,}", flush=True)
    features = np.concatenate(out).astype(np.float32)
    np.save(cache_path, features)
    meta: dict[str, Any] = {
        "encoder": "resnet18-imagenet1k_v1",
        "resize": RESIZE,
        "n_frames": len(rows),
        "dim": int(features.shape[1]),
        "seconds": float(time.perf_counter() - t0),
    }
    cache_path.with_suffix(".json").write_text(json.dumps(meta, indent=2))
    print(f"saved: {cache_path} ({features.nbytes / 1e6:.0f} MB)")
    return features


def features_for_df(
    df: Any, batch_size: int = 128, force: bool = False
) -> np.ndarray:
    if FEATURE_PATH.exists() and not force:
        full = np.load(FEATURE_PATH)
        if len(full) == len(load_camera_targets()[0]):
            return full[df["row"].to_numpy()]
    return extract_features(df["row"].to_numpy(), batch_size, force=force)
