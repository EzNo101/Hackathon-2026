from __future__ import annotations

import argparse
import json
import time
from typing import Any

import joblib
import numpy as np
import pandas as pd
import torch
from sklearn.linear_model import Ridge
from torch import nn
from torch.utils.data import DataLoader

from .camera_shape import (
    FUSION_METRICS_PATH,
    FUSION_PRED_PATH,
    MAG_METRICS_PATH,
    MAG_MODEL_PATH,
    METRICS_PATH,
    MODEL_PATH,
    PRED_PATH,
    SmallCNNRegressor,
    build_datasets,
    discharge_split,
    load_camera_targets,
)
from .config import FEATURES, SEED, TARGETS
from .metrics import regression_report
from .models import build_regressor

MODEL_TARGETS: list[str] = TARGETS


def evaluate(
    model: nn.Module,
    loader: DataLoader[Any],
    device: torch.device,
    target_mean: np.ndarray,
    target_std: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, float]:
    model.eval()
    preds: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    total = 0.0
    with torch.no_grad():
        for x, y in loader:
            x = x.to(device)
            out = model(x).cpu().numpy()
            preds.append(out * target_std + target_mean)
            ys.append(y.numpy() * target_std + target_mean)
            total += float(((out - y.numpy()) ** 2).mean()) * len(y)
    y_true = np.concatenate(ys)
    y_pred = np.concatenate(preds)
    return y_true, y_pred, total / len(y_true)


def train_cnn(
    train_ds: Any,
    val_ds: Any,
    device: torch.device,
    args: argparse.Namespace,
    target_mean: np.ndarray,
    target_std: np.ndarray,
) -> tuple[SmallCNNRegressor, list[dict[str, Any]], float]:
    loader_kwargs: dict[str, Any] = {
        "batch_size": args.batch_size,
        "num_workers": args.workers,
        "persistent_workers": args.workers > 0,
    }
    train_loader = DataLoader(train_ds, shuffle=True, **loader_kwargs)
    val_loader = DataLoader(val_ds, shuffle=False, **loader_kwargs)

    model = SmallCNNRegressor(len(MODEL_TARGETS)).to(device)
    criterion = nn.SmoothL1Loss(beta=0.5)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=args.epochs, eta_min=1e-5
    )

    history: list[dict[str, Any]] = []
    best_mae = float("inf")
    best_epoch = -1
    t0 = time.perf_counter()

    for epoch in range(1, args.epochs + 1):
        model.train()
        running = 0.0
        seen = 0
        for x, y in train_loader:
            x = x.to(device)
            y = y.to(device)
            optimizer.zero_grad(set_to_none=True)
            out = model(x)
            loss = criterion(out, y)
            loss.backward()
            optimizer.step()
            running += float(loss.detach()) * len(y)
            seen += len(y)
        scheduler.step()

        y_val, p_val, val_loss = evaluate(
            model, val_loader, device, target_mean, target_std
        )
        val_mae = float(np.mean(np.abs(y_val - p_val), axis=0).mean())
        row = {
            "epoch": epoch,
            "train_loss": running / seen,
            "val_loss": val_loss,
            "val_MAE_mean": val_mae,
        }
        history.append(row)
        print(
            f"epoch {epoch:2d}/{args.epochs}  train {running / seen:.4f}  "
            f"val {val_loss:.4f}  val mean MAE {val_mae:.6f}",
            flush=True,
        )
        if val_mae < best_mae:
            best_mae = val_mae
            best_epoch = epoch
            torch.save(model.state_dict(), MODEL_PATH)
        elif epoch - best_epoch >= args.patience:
            print(f"early stopping (best epoch {best_epoch})")
            break

    model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
    return model, history, time.perf_counter() - t0


def fit_magnetic_baseline(
    train: pd.DataFrame, val: pd.DataFrame, test: pd.DataFrame
) -> tuple[Any, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    model = build_regressor()
    model.fit(train[FEATURES], train[MODEL_TARGETS])
    p_val = np.asarray(model.predict(val[FEATURES]))
    p_test = np.asarray(model.predict(test[FEATURES]))
    return model, p_val, p_test, val[MODEL_TARGETS].to_numpy(), test[MODEL_TARGETS].to_numpy()


def fit_fusion(
    val_mag: np.ndarray,
    val_img: np.ndarray,
    val_y: np.ndarray,
    test_mag: np.ndarray,
    test_img: np.ndarray,
) -> tuple[np.ndarray, list[Ridge]]:
    x_val = np.hstack([val_mag, val_img])
    x_test = np.hstack([test_mag, test_img])
    preds = np.zeros_like(test_mag)
    models: list[Ridge] = []
    for i in range(test_mag.shape[1]):
        reg = Ridge(alpha=1.0)
        reg.fit(x_val, val_y[:, i])
        preds[:, i] = reg.predict(x_test)
        models.append(reg)
    return preds, models


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--patience", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--max-train", type=int, default=0)
    args = parser.parse_args()

    torch.manual_seed(SEED)
    np.random.seed(SEED)
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"device: {device}")

    df, mean, std = load_camera_targets()
    train, val, test, info = discharge_split(df)
    if args.max_train:
        train = train.iloc[: args.max_train].reset_index(drop=True)
    print(
        f"frames: train={len(train):,}/{train.discharge.nunique()} "
        f"val={len(val):,}/{val.discharge.nunique()} "
        f"test={len(test):,}/{test.discharge.nunique()}"
    )

    train_ds, val_ds, test_ds, target_mean, target_std = build_datasets(
        train, val, test, MODEL_TARGETS, mean, std
    )
    n_params = sum(p.numel() for p in SmallCNNRegressor(len(MODEL_TARGETS)).parameters())
    print(f"model parameters: {n_params:,}")

    model, history, train_time = train_cnn(
        train_ds, val_ds, device, args, target_mean, target_std
    )
    loader_kwargs: dict[str, Any] = {
        "batch_size": args.batch_size,
        "num_workers": args.workers,
        "persistent_workers": args.workers > 0,
    }
    test_loader = DataLoader(test_ds, shuffle=False, **loader_kwargs)
    y_test_img, p_test_img, _ = evaluate(
        model, test_loader, device, target_mean, target_std
    )
    img_report = regression_report(y_test_img, p_test_img, MODEL_TARGETS)
    print("\n=== image-only ===")
    for row in img_report:
        print(f"{row['target']:22s} MAE={row['MAE']:.6f} R2={row['R2']:+.4f}")

    print("\n=== magnetic-only (same frames) ===")
    mag_model, p_val_mag, p_test_mag, y_val_mag, y_test_mag = fit_magnetic_baseline(
        train, val, test
    )
    mag_report = regression_report(y_test_mag, p_test_mag, MODEL_TARGETS)
    for row in mag_report:
        print(f"{row['target']:22s} MAE={row['MAE']:.6f} R2={row['R2']:+.4f}")

    fisher_img = np.abs(y_test_img - p_test_img)
    fisher_mag = np.abs(y_test_mag - p_test_mag)
    print("\n=== fusion (stacked on validation discharges) ===")
    val_loader = DataLoader(val_ds, shuffle=False, **loader_kwargs)
    _, p_val_img, _ = evaluate(model, val_loader, device, target_mean, target_std)
    p_test_fusion, fusion_models = fit_fusion(
        p_val_mag,
        p_val_img,
        y_val_mag,
        p_test_mag,
        p_test_img,
    )
    fusion_report = regression_report(y_test_mag, p_test_fusion, MODEL_TARGETS)
    for row in fusion_report:
        print(f"{row['target']:22s} MAE={row['MAE']:.6f} R2={row['R2']:+.4f}")

    summary = []
    for name, rep in [
        ("image", img_report),
        ("magnetic", mag_report),
        ("fusion", fusion_report),
    ]:
        summary.append({"modality": name, "targets": rep})
    print(
        f"\nmean MAE: image={np.mean([r['MAE'] for r in img_report]):.6f} "
        f"magnetic={np.mean([r['MAE'] for r in mag_report]):.6f} "
        f"fusion={np.mean([r['MAE'] for r in fusion_report]):.6f}"
    )

    model.eval()
    x1 = test_ds[0][0].unsqueeze(0).to(device)
    for _ in range(10):
        model(x1)
    reps = 100
    t0 = time.perf_counter()
    with torch.no_grad():
        for _ in range(reps):
            model(x1)
    latency_ms = (time.perf_counter() - t0) / reps * 1e3
    print(f"\nimage CNN latency (1 frame): {latency_ms:.3f} ms")

    pred_df = test[["row", "discharge", "t_cam"]].copy()
    for i, name in enumerate(MODEL_TARGETS):
        pred_df[f"true_{name}"] = y_test_img[:, i]
        pred_df[f"img_{name}"] = p_test_img[:, i]
        pred_df[f"mag_{name}"] = p_test_mag[:, i]
        pred_df[f"fus_{name}"] = p_test_fusion[:, i]
    pred_df.to_csv(PRED_PATH, index=False)

    fusion_pred_df = test[["row", "discharge", "t_cam"]].copy()
    for i, name in enumerate(MODEL_TARGETS):
        fusion_pred_df[f"true_{name}"] = y_test_img[:, i]
        fusion_pred_df[f"pred_{name}"] = p_test_fusion[:, i]
    fusion_pred_df.to_csv(FUSION_PRED_PATH, index=False)

    payload: dict[str, Any] = {
        "device": str(device),
        "n_params": n_params,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "lr": args.lr,
        "train_time_s": train_time,
        "latency_ms": latency_ms,
        "targets": MODEL_TARGETS,
        "split": info,
        "history": history,
        "image": img_report,
        "magnetic": mag_report,
        "fusion": fusion_report,
        "mean_MAE": {
            "image": float(np.mean([r["MAE"] for r in img_report])),
            "magnetic": float(np.mean([r["MAE"] for r in mag_report])),
            "fusion": float(np.mean([r["MAE"] for r in fusion_report])),
        },
        "image_wins": {
            target: bool(fisher_img[:, i].mean() < fisher_mag[:, i].mean())
            for i, target in enumerate(MODEL_TARGETS)
        },
    }
    METRICS_PATH.write_text(json.dumps(payload, indent=2))

    MAG_METRICS_PATH.write_text(json.dumps({"magnetic": mag_report}, indent=2))
    FUSION_METRICS_PATH.write_text(
        json.dumps({"fusion": fusion_report, "stack_models": [m.coef_.tolist() for m in fusion_models]}, indent=2)
    )
    joblib.dump({"model": mag_model, "targets": MODEL_TARGETS}, MAG_MODEL_PATH)
    print(f"\nsaved: {MODEL_PATH}")
    print(f"saved: {METRICS_PATH}")
    print(f"saved: {MAG_MODEL_PATH}")
    print(f"saved: {PRED_PATH}")


if __name__ == "__main__":
    main()
