from __future__ import annotations

import json
import time
from typing import Any

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from torchvision.models import ResNet18_Weights, resnet18

from .camera_image import IMAGENET_MEAN, IMAGENET_STD, RESIZE
from .camera_shape import discharge_split, load_camera_targets
from .config import ARTIFACTS_DIR, SEED, TARGETS
from .prepare_camera import CACHE_PATH

OUT_PATH = ARTIFACTS_DIR / "image_ablation.json"
SHAPE_TARGETS: list[str] = [t for t in TARGETS if t != "plasma_current"]

Device = torch.device


def _encoder(device: Device) -> torch.nn.Module:
    model = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
    model.fc = torch.nn.Identity()  # pyright: ignore[reportAttributeAccessIssue]
    model.eval()
    return model.to(device)


def _load_batch(cache: np.ndarray, rows: np.ndarray) -> torch.Tensor:
    batch = np.asarray(cache[rows.astype(int)])
    return torch.from_numpy(batch.astype(np.float32) / 255.0).permute(0, 3, 1, 2)


def _apply_variant(x: torch.Tensor, name: str) -> torch.Tensor:
    if name == "grayscale":
        return x.mean(dim=1, keepdim=True).repeat(1, 3, 1, 1)
    if name.startswith("crop_"):
        box = {
            "crop_left": (0, 0, 48, 96),
            "crop_right": (48, 0, 96, 96),
            "crop_top": (0, 0, 96, 48),
            "crop_bottom": (0, 48, 96, 96),
            "crop_center": (24, 24, 72, 72),
        }[name]
        x0, y0, x1, y1 = box
        return F.interpolate(x[:, :, y0:y1, x0:x1], size=(96, 96), mode="bilinear")
    if name.startswith("occlude_"):
        box = {
            "occlude_left": (0, 0, 48, 96),
            "occlude_right": (48, 0, 96, 96),
            "occlude_top": (0, 0, 96, 48),
            "occlude_bottom": (0, 48, 96, 96),
            "occlude_center": (24, 24, 72, 72),
        }[name]
        x0, y0, x1, y1 = box
        out = x.clone()
        out[:, :, y0:y1, x0:x1] = 0.0
        return out
    if name.startswith("shift_"):
        _, dx, dy = name.split("_")
        theta = torch.tensor(
            [[1.0, 0.0, 2.0 * int(dx) / 96.0], [0.0, 1.0, 2.0 * int(dy) / 96.0]],
            device=x.device,
        ).unsqueeze(0).repeat(x.shape[0], 1, 1)
        grid = F.affine_grid(theta, list(x.shape), align_corners=False)
        return F.grid_sample(x, grid, align_corners=False, padding_mode="zeros")
    if name.startswith("rotate_"):
        angle = float(name.split("_")[1])
        rad = np.deg2rad(angle)
        cos, sin = float(np.cos(rad)), float(np.sin(rad))
        theta = torch.tensor(
            [[cos, -sin, 0.0], [sin, cos, 0.0]], device=x.device
        ).unsqueeze(0).repeat(x.shape[0], 1, 1)
        grid = F.affine_grid(theta, list(x.shape), align_corners=False)
        return F.grid_sample(x, grid, align_corners=False, padding_mode="zeros")
    if name == "full":
        return x
    raise ValueError(name)


def embed(
    rows: np.ndarray,
    variant: str,
    device: Device,
    batch_size: int = 128,
) -> np.ndarray:
    encoder = _encoder(device)
    cache = np.load(CACHE_PATH, mmap_mode="r")
    mean = torch.from_numpy(IMAGENET_MEAN).to(device).view(1, 3, 1, 1)
    std = torch.from_numpy(IMAGENET_STD).to(device).view(1, 3, 1, 1)
    out: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(rows), batch_size):
            x = _load_batch(cache, rows[start : start + batch_size]).to(device)
            x = _apply_variant(x, variant)
            x = F.interpolate(x, size=(RESIZE, RESIZE), mode="bilinear", align_corners=False)
            out.append(encoder((x - mean) / std).cpu().numpy())
    return np.concatenate(out).astype(np.float32)


def fit_eval(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_test: np.ndarray,
    y_test: np.ndarray,
) -> dict[str, Any]:
    model = make_pipeline(StandardScaler(), Ridge(alpha=100.0))
    model.fit(x_train, y_train)
    p = np.asarray(model.predict(x_test))
    per_target = {
        target: float(mean_absolute_error(y_test[:, i], p[:, i]))
        for i, target in enumerate(SHAPE_TARGETS)
    }
    return {"mean_shape_MAE": float(np.mean(list(per_target.values()))), "per_target": per_target}


def main() -> None:
    np.random.seed(SEED)
    df, _mean, _std = load_camera_targets()
    train, _val, test, _info = discharge_split(df)
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

    # Balanced-ish subset across discharges for the extraction-heavy experiments.
    def subsample(part: pd.DataFrame, n: int) -> pd.DataFrame:
        rng = np.random.default_rng(SEED)
        idx = rng.choice(len(part), min(n, len(part)), replace=False)
        return part.iloc[np.sort(idx)].reset_index(drop=True)

    train_s = subsample(train, 20_000)
    test_s = subsample(test, 8_000)
    y_train = train_s[SHAPE_TARGETS].to_numpy(dtype=np.float64)
    y_test = test_s[SHAPE_TARGETS].to_numpy(dtype=np.float64)
    print(f"subset: train={len(train_s)} test={len(test_s)}")

    variants = [
        "full",
        "grayscale",
        "crop_left",
        "crop_right",
        "crop_top",
        "crop_bottom",
        "crop_center",
        "occlude_left",
        "occlude_right",
        "occlude_top",
        "occlude_bottom",
        "occlude_center",
    ]
    results: dict[str, Any] = {}
    print("\n=== image region / grayscale ablation ===")
    for name in variants:
        t0 = time.perf_counter()
        x_tr = embed(train_s["row"].to_numpy(), name, device)
        x_te = embed(test_s["row"].to_numpy(), name, device)
        row = fit_eval(x_tr, y_train, x_te, y_test)
        row["seconds"] = time.perf_counter() - t0
        results[name] = row
        print(f"{name:16s} mean shape MAE={row['mean_shape_MAE']:.6f}")

    # Learning curve with the cached full-image features.
    print("\n=== learning curve (image-only) ===")
    all_features = np.load(ARTIFACTS_DIR / "camera_features_resnet18.npy")
    row_to_index = {int(r): i for i, r in enumerate(df["row"].to_numpy())}
    full_train = train[["row"]].copy()
    full_train["features_idx"] = [row_to_index[int(r)] for r in full_train["row"]]
    x_train_all = all_features[full_train["features_idx"].to_numpy()]
    y_train_all = train[SHAPE_TARGETS].to_numpy(dtype=np.float64)
    x_test_all = all_features[np.asarray([row_to_index[int(r)] for r in test["row"].to_numpy()])]
    y_test_all = test[SHAPE_TARGETS].to_numpy(dtype=np.float64)
    rng = np.random.default_rng(SEED)
    learning: dict[str, Any] = {}
    for n in [1000, 2500, 5000, 10_000, 20_000, 40_000, len(x_train_all)]:
        n = min(n, len(x_train_all))
        idx = rng.choice(len(x_train_all), n, replace=False)
        row = fit_eval(x_train_all[idx], y_train_all[idx], x_test_all, y_test_all)
        learning[str(n)] = row
        print(f"n={n:6d}  mean shape MAE={row['mean_shape_MAE']:.6f}")

    # Camera jitter sensitivity: train on full train, test on transformed test.
    print("\n=== camera jitter / rotation sensitivity (image-only) ===")
    model = make_pipeline(StandardScaler(), Ridge(alpha=100.0))
    model.fit(x_train_all, y_train_all)
    base_pred = np.asarray(model.predict(x_test_all))
    base_mae = float(
        np.mean(
            [
                mean_absolute_error(y_test_all[:, i], base_pred[:, i])
                for i in range(len(SHAPE_TARGETS))
            ]
        )
    )
    jitter: dict[str, Any] = {"none": base_mae}
    for name in [
        "shift_5_0",
        "shift_-5_0",
        "shift_0_5",
        "shift_0_-5",
        "shift_5_5",
        "shift_-5_-5",
        "rotate_3",
        "rotate_-3",
    ]:
        x_var = embed(test_s["row"].to_numpy(), name, device)
        p = np.asarray(model.predict(x_var))
        jitter[name] = float(
            np.mean(
                [
                    mean_absolute_error(y_test[:, i], p[:, i])
                    for i in range(len(SHAPE_TARGETS))
                ]
            )
        )
        print(f"{name:14s} mean shape MAE={jitter[name]:.6f} (baseline {base_mae:.6f})")

    payload: dict[str, Any] = {
        "n_train_subset": len(train_s),
        "n_test_subset": len(test_s),
        "variants": results,
        "learning_curve": learning,
        "jitter": jitter,
        "note": "Ridge on frozen ResNet18 features; MAE over 9 shape targets",
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2))
    print(f"\nsaved: {OUT_PATH}")


if __name__ == "__main__":
    main()
