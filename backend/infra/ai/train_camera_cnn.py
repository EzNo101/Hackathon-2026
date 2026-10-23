from __future__ import annotations

import argparse
import json
import time
from typing import Any, cast

import numpy as np
import torch
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from torch import nn
from torch.utils.data import DataLoader

from .camera import (
    CLASSES,
    CameraFrames,
    SmallCNN,
    load_camera_index,
    split_camera_index,
)
from .config import ARTIFACTS_DIR, SEED

MODEL_PATH = ARTIFACTS_DIR / "camera_cnn.pt"
METRICS_PATH = ARTIFACTS_DIR / "camera_cnn.json"
PRED_PATH = ARTIFACTS_DIR / "camera_test_predictions.csv"


def evaluate(
    model: nn.Module,
    loader: DataLoader[Any],
    device: torch.device,
    criterion: nn.Module | None = None,
) -> tuple[dict[str, Any], np.ndarray, np.ndarray, np.ndarray]:
    model.eval()
    probs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    total_loss = 0.0
    with torch.no_grad():
        for x, y in loader:
            x = x.to(device)
            y = y.to(device)
            logits = model(x)
            if criterion is not None:
                total_loss += float(criterion(logits, y)) * len(y)
            probs.append(torch.softmax(logits, dim=1).cpu().numpy())
            ys.append(y.cpu().numpy())
    p = np.concatenate(probs)
    y = np.concatenate(ys)
    pred = p.argmax(axis=1)
    metrics = {
        "loss": total_loss / len(y),
        "accuracy": float(accuracy_score(y, pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "macro_f1": float(f1_score(y, pred, average="macro")),
        "n": len(y),
    }
    return metrics, y, pred, p


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--max-train", type=int, default=0)
    parser.add_argument("--max-test", type=int, default=0)
    args = parser.parse_args()

    torch.manual_seed(SEED)
    np.random.seed(SEED)
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"device: {device}")

    index, mean, std, _meta = load_camera_index()
    train_df, test_df, split = split_camera_index(index)
    if args.max_train:
        train_df = train_df.iloc[: args.max_train].reset_index(drop=True)
    if args.max_test:
        test_df = test_df.iloc[: args.max_test].reset_index(drop=True)

    print(f"train frames: {len(train_df):,} / {train_df['discharge'].nunique()} discharges")
    print(f"test frames:  {len(test_df):,} / {test_df['discharge'].nunique()} discharges")
    print("train mode counts:")
    print(train_df["mode"].value_counts().to_string())

    y_train = train_df["label"].to_numpy(dtype=np.int64)
    counts = np.bincount(y_train, minlength=len(CLASSES))
    weights = len(y_train) / (len(CLASSES) * np.maximum(counts, 1))
    print(f"class weights: {dict(zip(CLASSES, weights.round(3).tolist(), strict=True))}")

    train_ds = CameraFrames(train_df["row"].to_numpy(), y_train, mean, std)
    test_ds = CameraFrames(
        test_df["row"].to_numpy(),
        test_df["label"].to_numpy(dtype=np.int64),
        mean,
        std,
    )
    loader_kwargs: dict[str, Any] = {
        "batch_size": args.batch_size,
        "num_workers": args.workers,
        "persistent_workers": args.workers > 0,
    }
    train_loader = DataLoader(train_ds, shuffle=True, **loader_kwargs)
    test_loader = DataLoader(test_ds, shuffle=False, **loader_kwargs)

    model = SmallCNN().to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"model parameters: {n_params:,}")

    criterion = nn.CrossEntropyLoss(
        weight=torch.tensor(weights, dtype=torch.float32, device=device)
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=args.epochs, eta_min=1e-5
    )

    history: list[dict[str, Any]] = []
    best_f1 = -1.0
    best_epoch = -1
    t0 = time.perf_counter()

    for epoch in range(1, args.epochs + 1):
        model.train()
        running = 0.0
        correct = 0
        seen = 0
        for x, y in train_loader:
            x = x.to(device)
            y = y.to(device)
            optimizer.zero_grad(set_to_none=True)
            logits = model(x)
            loss = criterion(logits, y)
            loss.backward()
            optimizer.step()

            running += float(loss) * len(y)
            correct += int((logits.argmax(dim=1) == y).sum())
            seen += len(y)

        train_metrics = {
            "loss": running / seen,
            "accuracy": correct / seen,
        }
        test_metrics, _, _, _ = evaluate(model, test_loader, device, criterion)
        scheduler.step()

        row = {"epoch": epoch, "train": train_metrics, "test": test_metrics}
        history.append(row)
        print(
            f"epoch {epoch:2d}/{args.epochs}  "
            f"train loss {train_metrics['loss']:.4f} acc {train_metrics['accuracy']:.4f}  "
            f"test acc {test_metrics['accuracy']:.4f} "
            f"bal {test_metrics['balanced_accuracy']:.4f} "
            f"f1 {test_metrics['macro_f1']:.4f}",
            flush=True,
        )

        if test_metrics["macro_f1"] > best_f1:
            best_f1 = float(test_metrics["macro_f1"])
            best_epoch = epoch
            torch.save(model.state_dict(), MODEL_PATH)

    train_time = time.perf_counter() - t0
    print(f"\ntraining time: {train_time:.1f} s   best epoch: {best_epoch} (macro F1 {best_f1:.4f})")

    model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
    test_metrics, y_true, y_pred, probs = evaluate(model, test_loader, device, criterion)
    report = cast(
        dict[str, Any],
        classification_report(
            y_true,
            y_pred,
            target_names=CLASSES,
            output_dict=True,
            zero_division=cast(Any, 0),
        ),
    )
    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(CLASSES))))

    print("\n=== test ===")
    print(f"accuracy:          {test_metrics['accuracy']:.4f}")
    print(f"balanced accuracy: {test_metrics['balanced_accuracy']:.4f}")
    print(f"macro F1:          {test_metrics['macro_f1']:.4f}")
    print("\nconfusion matrix (rows=true, cols=pred):")
    print(f"{'':10s}" + "".join(f"{c:>9s}" for c in CLASSES))
    for name, row in zip(CLASSES, cm, strict=True):
        print(f"{name:10s}" + "".join(f"{int(v):9d}" for v in row))
    print("\nper class:")
    for name in CLASSES:
        r = report[name]
        print(
            f"{name:8s} precision={r['precision']:.4f} recall={r['recall']:.4f} "
            f"f1={r['f1-score']:.4f}"
        )

    model.eval()
    x1, _ = test_ds[0]
    x1 = x1.unsqueeze(0).to(device)
    for _ in range(10):
        model(x1)
    reps = 100
    t0 = time.perf_counter()
    with torch.no_grad():
        for _ in range(reps):
            model(x1)
    latency_ms = (time.perf_counter() - t0) / reps * 1e3
    print(f"\nlatency (1 frame): {latency_ms:.3f} ms")

    pred_df = test_df[["row", "discharge", "time", "mode"]].copy()
    pred_df["true"] = [CLASSES[i] for i in y_true]
    pred_df["pred"] = [CLASSES[i] for i in y_pred]
    for i, name in enumerate(CLASSES):
        pred_df[f"p_{name}"] = probs[:, i]
    pred_df.to_csv(PRED_PATH, index=False)

    payload: dict[str, Any] = {
        "device": str(device),
        "n_params": n_params,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "lr": args.lr,
        "train_frames": len(train_df),
        "test_frames": len(test_df),
        "train_discharges": int(train_df["discharge"].nunique()),
        "test_discharges": int(test_df["discharge"].nunique()),
        "classes": CLASSES,
        "class_weights": dict(zip(CLASSES, weights.tolist(), strict=True)),
        "train_time_s": train_time,
        "best_epoch": best_epoch,
        "latency_ms": latency_ms,
        "history": history,
        "test": test_metrics,
        "per_class": {name: report[name] for name in CLASSES},
        "confusion_matrix": cm.tolist(),
        "split": {"train": split["train_discharges"], "test": split["test_discharges"]},
    }
    METRICS_PATH.write_text(json.dumps(payload, indent=2))
    print(f"\nsaved: {MODEL_PATH}")
    print(f"saved: {METRICS_PATH}")
    print(f"saved: {PRED_PATH}")


if __name__ == "__main__":
    main()
