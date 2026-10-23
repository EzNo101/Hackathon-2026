from __future__ import annotations

import argparse
import json
import time
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .camera_image import (
    FEATURE_PATH,
    FUSION_METRICS_PATH,
    FUSION_PRED_PATH,
    IMAGE_METRICS_PATH,
    IMAGE_MODEL_PATH,
    IMAGE_PRED_PATH,
    extract_features,
)
from .camera_shape import discharge_split, load_camera_targets
from .config import FEATURES, SEED, TARGETS
from .metrics import regression_report
from .models import build_regressor

MODEL_TARGETS: list[str] = TARGETS
SHAPE_TARGETS: list[str] = [t for t in TARGETS if t != "plasma_current"]


def regression_view(y: np.ndarray, p: np.ndarray) -> dict[str, Any]:
    rows = regression_report(y, p, MODEL_TARGETS)
    shape_mae = float(
        np.mean([r["MAE"] for r in rows if r["target"] in SHAPE_TARGETS])
    )
    return {"per_target": rows, "mean_shape_MAE": shape_mae}


def fit_ridge(x: np.ndarray, y: np.ndarray, alpha: float) -> Any:
    model = make_pipeline(StandardScaler(), Ridge(alpha=alpha))
    model.fit(x, y)
    return model


def fit_mlp(x: np.ndarray, y: np.ndarray) -> Any:
    model = make_pipeline(
        StandardScaler(),
        MLPRegressor(
            hidden_layer_sizes=(256, 128),
            alpha=1e-3,
            batch_size=512,  # pyright: ignore[reportArgumentType]
            learning_rate_init=1e-3,
            max_iter=250,
            early_stopping=True,
            random_state=SEED,
        ),
    )
    model.fit(x, y)
    return model


def evaluate_model(name: str, model: Any, x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    t0 = time.perf_counter()
    p = np.asarray(model.predict(x))
    latency = (time.perf_counter() - t0) / len(x) * 1e3
    out = regression_view(y, p)
    out["inference_ms_per_sample"] = latency
    print(
        f"{name:18s} mean shape MAE={out['mean_shape_MAE']:.6f} "
        f"({latency:.4f} ms/sample)"
    )
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--alpha", type=float, default=100.0)
    parser.add_argument("--force-features", action="store_true")
    parser.add_argument("--max-train", type=int, default=0)
    args = parser.parse_args()

    np.random.seed(SEED)
    df, _mean, _std = load_camera_targets()
    train, val, test, info = discharge_split(df)
    if args.max_train:
        train = train.iloc[: args.max_train].reset_index(drop=True)

    print(
        f"frames: train={len(train):,}/{train.discharge.nunique()} "
        f"val={len(val):,}/{val.discharge.nunique()} "
        f"test={len(test):,}/{test.discharge.nunique()}"
    )
    print("extracting / loading ResNet18 features")
    t0 = time.perf_counter()
    all_features = extract_features(df["row"].to_numpy(), force=args.force_features)
    print(f"features ready in {time.perf_counter() - t0:.1f} s")

    row_to_index = {int(r): i for i, r in enumerate(df["row"].to_numpy())}
    def index_rows(part: pd.DataFrame) -> np.ndarray:
        return np.asarray([row_to_index[int(r)] for r in part["row"].to_numpy()])

    x_train = all_features[index_rows(train)]
    x_val = all_features[index_rows(val)]
    x_test = all_features[index_rows(test)]
    y_train = train[MODEL_TARGETS].to_numpy(dtype=np.float64)
    y_val = val[MODEL_TARGETS].to_numpy(dtype=np.float64)
    y_test = test[MODEL_TARGETS].to_numpy(dtype=np.float64)

    print("\n=== image-only: ResNet18 features + ridge ===")
    image_model = fit_ridge(x_train, y_train, args.alpha)
    img_val = evaluate_model("image/val", image_model, x_val, y_val)
    img_test = evaluate_model("image/test", image_model, x_test, y_test)
    for r in img_test["per_target"]:
        print(f"  {r['target']:22s} MAE={r['MAE']:.6f} R2={r['R2']:+.4f}")

    print("\n=== image-only: ResNet18 features + MLP ===")
    image_mlp = fit_mlp(x_train, y_train)
    img_mlp_test = evaluate_model("image-mlp/test", image_mlp, x_test, y_test)

    print("\n=== magnetic-only (same frames) ===")
    mag_model = build_regressor()
    mag_model.fit(train[FEATURES], y_train)
    p_val_mag = np.asarray(mag_model.predict(val[FEATURES]))
    mag_test = evaluate_model("magnetic/test", mag_model, test[FEATURES].to_numpy(), y_test)
    for r in mag_test["per_target"]:
        print(f"  {r['target']:22s} MAE={r['MAE']:.6f} R2={r['R2']:+.4f}")

    print("\n=== late fusion: stack image + magnetic predictions (fit on val) ===")
    p_val_img = np.asarray(image_model.predict(x_val))
    x_val_stack = np.hstack([p_val_img, p_val_mag])
    x_test_stack = np.hstack([np.asarray(image_model.predict(x_test)), np.asarray(mag_model.predict(test[FEATURES]))])
    fusion_pred = np.zeros_like(y_test)
    stack_models: list[Ridge] = []
    for i in range(len(MODEL_TARGETS)):
        reg = Ridge(alpha=1.0)
        reg.fit(x_val_stack, y_val[:, i])
        fusion_pred[:, i] = reg.predict(x_test_stack)
        stack_models.append(reg)
    late_report = regression_view(y_test, fusion_pred)
    print(f"{'late-fusion':18s} mean shape MAE={late_report['mean_shape_MAE']:.6f}")
    for r in late_report["per_target"]:
        print(f"  {r['target']:22s} MAE={r['MAE']:.6f} R2={r['R2']:+.4f}")

    print("\n=== feature fusion: ResNet18 + magnetic features + ridge ===")
    x_train_fuse = np.hstack([x_train, train[FEATURES].to_numpy()])
    x_val_fuse = np.hstack([x_val, val[FEATURES].to_numpy()])
    x_test_fuse = np.hstack([x_test, test[FEATURES].to_numpy()])
    fusion_feat_model = fit_ridge(x_train_fuse, y_train, args.alpha)
    feat_val = evaluate_model("feat-fusion/val", fusion_feat_model, x_val_fuse, y_val)
    feat_test = evaluate_model("feat-fusion/test", fusion_feat_model, x_test_fuse, y_test)
    for r in feat_test["per_target"]:
        print(f"  {r['target']:22s} MAE={r['MAE']:.6f} R2={r['R2']:+.4f}")
    p_test_feat = np.asarray(fusion_feat_model.predict(x_test_fuse))

    payload: dict[str, Any] = {
        "split": info,
        "features": "resnet18-imagenet 512d",
        "alpha": args.alpha,
        "image_ridge": {"val": img_val, "test": img_test},
        "image_mlp": {"test": img_mlp_test},
        "magnetic": {"test": mag_test},
        "late_fusion": {"test": late_report},
        "feature_fusion": {"val": feat_val, "test": feat_test},
        "stack_models": [m.coef_.tolist() for m in stack_models],
    }
    IMAGE_METRICS_PATH.write_text(json.dumps(payload, indent=2))
    FUSION_METRICS_PATH.write_text(json.dumps(payload, indent=2))

    pred = test[["row", "discharge", "t_cam"]].copy()
    for i, target in enumerate(MODEL_TARGETS):
        pred[f"true_{target}"] = y_test[:, i]
        pred[f"image_{target}"] = np.asarray(image_model.predict(x_test))[:, i]
        pred[f"mag_{target}"] = np.asarray(mag_model.predict(test[FEATURES]))[:, i]
        pred[f"late_{target}"] = fusion_pred[:, i]
        pred[f"feat_{target}"] = p_test_feat[:, i]
    pred.to_csv(IMAGE_PRED_PATH, index=False)

    fusion_pred_df = test[["row", "discharge", "t_cam"]].copy()
    for i, target in enumerate(MODEL_TARGETS):
        fusion_pred_df[f"true_{target}"] = y_test[:, i]
        fusion_pred_df[f"pred_{target}"] = p_test_feat[:, i]
        fusion_pred_df[f"late_{target}"] = fusion_pred[:, i]
    fusion_pred_df.to_csv(FUSION_PRED_PATH, index=False)

    joblib.dump(
        {"model": image_model, "targets": MODEL_TARGETS, "encoder": "resnet18"},
        IMAGE_MODEL_PATH,
    )
    joblib.dump(
        {
            "model": fusion_feat_model,
            "targets": MODEL_TARGETS,
            "encoder": "resnet18",
            "features": FEATURES,
        },
        FUSION_METRICS_PATH.with_name("camera_fusion_feature_ridge.joblib"),
    )
    print(f"\nsaved: {IMAGE_MODEL_PATH}")
    print(f"saved: {IMAGE_METRICS_PATH}")
    print(f"saved: {IMAGE_PRED_PATH}")
    print(f"saved: {FUSION_PRED_PATH}")
    print(f"feature file: {FEATURE_PATH}")


if __name__ == "__main__":
    main()
