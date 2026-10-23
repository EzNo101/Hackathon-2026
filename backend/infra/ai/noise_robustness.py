from __future__ import annotations

import json
import warnings
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .camera_image import FEATURE_PATH
from .camera_shape import discharge_split, load_camera_targets
from .config import ARTIFACTS_DIR, FEATURES, SEED, TARGETS, TEST_FRAC
from .data import load_equilibrium, split_by_discharge
from .metrics import regression_report
from .models import build_regressor

warnings.filterwarnings("ignore")

SHAPE_TARGETS: list[str] = [t for t in TARGETS if t != "plasma_current"]
OUT_PATH = ARTIFACTS_DIR / "noise_robustness.json"
NOISE_PRED_PATH = ARTIFACTS_DIR / "noise_fusion_test_predictions.csv"
ROBUST_MODEL_PATH = ARTIFACTS_DIR / "magnetic_mlp_noise_robust.joblib"


def mean_mae(y: np.ndarray, p: np.ndarray) -> float:
    rows = regression_report(y, p, SHAPE_TARGETS)
    return float(np.mean([r["MAE"] for r in rows]))


def corrupt(
    df: pd.DataFrame,
    features: list[str],
    noise_frac: float,
    drift_scale: float,
    rng: np.random.Generator,
) -> np.ndarray:
    x = df[features].to_numpy(dtype=np.float64)
    std = x.std(axis=0)
    noise = rng.normal(0.0, noise_frac, size=x.shape) * std
    drift = np.zeros_like(x)
    t = df["time"].to_numpy(dtype=np.float64)
    for discharge in df["discharge"].unique():
        mask = (df["discharge"] == discharge).to_numpy()
        coeff = rng.normal(0.0, drift_scale, size=len(features)) * std
        drift[mask] = np.outer(t[mask], coeff)
    return x + noise + drift


def fit_mag(train: pd.DataFrame, x_train: np.ndarray) -> Any:
    mask = train[SHAPE_TARGETS].notna().all(axis=1)
    model = build_regressor()
    if len(x_train) == int(mask.sum()):
        model.fit(x_train, train.loc[mask, SHAPE_TARGETS])
    else:
        model.fit(x_train, train[SHAPE_TARGETS])
    return model


def eval_mag(model: Any, x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    p = np.asarray(model.predict(x))
    rows = regression_report(y, p, SHAPE_TARGETS)
    return {"mean_shape_MAE": float(np.mean([r["MAE"] for r in rows])), "per_target": rows}


def attach_noisy_features(
    frames: pd.DataFrame, noisy_eq: pd.DataFrame, tolerance: float = 0.02
) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    for discharge in sorted(frames["discharge"].unique()):
        left = frames[frames["discharge"] == discharge].sort_values("t_eq")
        right = noisy_eq[noisy_eq["discharge"] == discharge].sort_values("time")
        right = right[["time"] + FEATURES].rename(
            columns={"time": "t_noisy", **{f: f"noisy_{f}" for f in FEATURES}}
        )
        part = pd.merge_asof(
            left,
            right,
            left_on="t_eq",
            right_on="t_noisy",
            direction="nearest",
            tolerance=tolerance,  # pyright: ignore[reportArgumentType]
        )
        parts.append(part)
    return pd.concat(parts, ignore_index=True)


def camera_fusion_under_noise(
    noisy_eq: pd.DataFrame,
) -> dict[str, Any]:
    frames, _mean, _std = load_camera_targets()
    frames = attach_noisy_features(frames, noisy_eq)
    train, val, test, _info = discharge_split(frames)
    all_features = np.load(FEATURE_PATH)
    row_to_index = {int(r): i for i, r in enumerate(frames["row"].to_numpy())}

    def fi(part: pd.DataFrame) -> np.ndarray:
        return all_features[np.asarray([row_to_index[int(r)] for r in part["row"].to_numpy()])]

    x_train, x_val, x_test = fi(train), fi(val), fi(test)
    y_train = train[SHAPE_TARGETS].to_numpy(dtype=np.float64)
    y_val = val[SHAPE_TARGETS].to_numpy(dtype=np.float64)
    y_test = test[SHAPE_TARGETS].to_numpy(dtype=np.float64)

    image = make_pipeline(StandardScaler(), Ridge(alpha=100.0))
    image.fit(x_train, y_train)
    p_val_img = np.asarray(image.predict(x_val))
    p_test_img = np.asarray(image.predict(x_test))

    mag = fit_mag(train, train[FEATURES].to_numpy())
    p_val_mag_clean = np.asarray(mag.predict(val[FEATURES]))
    p_test_mag_clean = np.asarray(mag.predict(test[FEATURES]))
    noisy_cols = [f"noisy_{f}" for f in FEATURES]
    p_val_mag_noisy = np.asarray(mag.predict(val[noisy_cols]))
    p_test_mag_noisy = np.asarray(mag.predict(test[noisy_cols]))

    def stack(p_val_mag: np.ndarray, p_test_mag: np.ndarray) -> np.ndarray:
        xv = np.hstack([p_val_img, p_val_mag])
        xt = np.hstack([p_test_img, p_test_mag])
        out = np.zeros_like(y_test)
        for i in range(len(SHAPE_TARGETS)):
            reg = Ridge(alpha=1.0)
            reg.fit(xv, y_val[:, i])
            out[:, i] = reg.predict(xt)
        return out

    p_fusion_clean = stack(p_val_mag_clean, p_test_mag_clean)
    p_fusion_noisy = stack(p_val_mag_noisy, p_test_mag_noisy)

    def view(name: str, p: np.ndarray) -> dict[str, Any]:
        rows = regression_report(y_test, p, SHAPE_TARGETS)
        result = {
            "mean_shape_MAE": float(np.mean([r["MAE"] for r in rows])),
            "per_target": rows,
        }
        print(f"{name:28s} mean shape MAE={result['mean_shape_MAE']:.6f}")
        return result

    print("\n=== camera frames: clean magnetic ===")
    out: dict[str, Any] = {}
    out["image_clean"] = view("image (clean)", p_test_img)
    out["mag_clean"] = view("magnetic (clean)", p_test_mag_clean)
    out["fusion_clean"] = view("fusion (clean)", p_fusion_clean)

    print("\n=== camera frames: noisy magnetic (from file) ===")
    out["mag_noisy"] = view("magnetic (noisy)", p_test_mag_noisy)
    out["image_noisy_mag"] = view("image (noisy mag input)", p_test_img)
    out["fusion_noisy"] = view("fusion (noisy)", p_fusion_noisy)

    pred = test[["row", "discharge", "t_cam"]].copy()
    for i, target in enumerate(SHAPE_TARGETS):
        pred[f"true_{target}"] = y_test[:, i]
        pred[f"image_{target}"] = p_test_img[:, i]
        pred[f"mag_clean_{target}"] = p_test_mag_clean[:, i]
        pred[f"mag_noisy_{target}"] = p_test_mag_noisy[:, i]
        pred[f"fusion_noisy_{target}"] = p_fusion_noisy[:, i]
    pred.to_csv(NOISE_PRED_PATH, index=False)
    return out


def main() -> None:
    np.random.seed(SEED)
    df = load_equilibrium()
    noisy = load_equilibrium(noisy=True)
    assert (df["discharge"].to_numpy() == noisy["discharge"].to_numpy()).all()
    assert np.allclose(df["time"].to_numpy(), noisy["time"].to_numpy())
    for f in FEATURES:
        df[f"noisy_{f}"] = noisy[f].to_numpy()

    train, test, _ = split_by_discharge(df, TEST_FRAC, SEED)
    mask_tr = train[SHAPE_TARGETS].notna().all(axis=1)
    mask_te = test[SHAPE_TARGETS].notna().all(axis=1)
    x_train_clean = train.loc[mask_tr, FEATURES].to_numpy()
    x_test_clean = test.loc[mask_te, FEATURES].to_numpy()
    x_test_noisy = test.loc[mask_te, [f"noisy_{f}" for f in FEATURES]].to_numpy()
    y_test = test.loc[mask_te, SHAPE_TARGETS].to_numpy()

    print("=== clean-trained magnetic model ===")
    clean_model = fit_mag(train, x_train_clean)
    clean_on_clean = eval_mag(clean_model, x_test_clean, y_test)
    clean_on_noisy = eval_mag(clean_model, x_test_noisy, y_test)
    print(f"clean test: {clean_on_clean['mean_shape_MAE']:.6f}")
    print(f"noisy test: {clean_on_noisy['mean_shape_MAE']:.6f}")

    print("\n=== noise/drift-augmented training ===")
    rng = np.random.default_rng(SEED)
    augmented = [x_train_clean]
    for noise_frac, drift_scale in [(0.02, 0.05), (0.05, 0.10), (0.1, 0.25)]:
        augmented.append(
            corrupt(train.loc[mask_tr], FEATURES, noise_frac, drift_scale, rng)
        )
    x_train_aug = np.vstack(augmented)
    robust_model = fit_mag(
        pd.concat([train.loc[mask_tr]] * len(augmented), ignore_index=True), x_train_aug
    )
    robust_on_clean = eval_mag(robust_model, x_test_clean, y_test)
    robust_on_noisy = eval_mag(robust_model, x_test_noisy, y_test)
    print(f"clean test: {robust_on_clean['mean_shape_MAE']:.6f}")
    print(f"noisy test: {robust_on_noisy['mean_shape_MAE']:.6f}")

    levels: list[dict[str, Any]] = []
    print("\n=== synthetic drift sweep (clean test rows) ===")
    for drift_scale in [0.0, 0.01, 0.03, 0.1, 0.3, 1.0]:
        x_syn = corrupt(test.loc[mask_te], FEATURES, 0.02, drift_scale, rng)
        a = mean_mae(y_test, np.asarray(clean_model.predict(x_syn)))
        b = mean_mae(y_test, np.asarray(robust_model.predict(x_syn)))
        levels.append({"drift_scale": drift_scale, "clean_model": a, "robust_model": b})
        print(f"drift={drift_scale:4.2f}  clean={a:.6f}  robust={b:.6f}")

    print("\n=== image + magnetic fusion under noisy magnetic ===")
    fusion = camera_fusion_under_noise(noisy)

    payload: dict[str, Any] = {
        "clean_model": {
            "clean_test": clean_on_clean,
            "noisy_test": clean_on_noisy,
        },
        "robust_model": {
            "clean_test": robust_on_clean,
            "noisy_test": robust_on_noisy,
        },
        "drift_sweep": levels,
        "camera_fusion": fusion,
        "note": "MAE averaged over 9 shape targets; split by discharge",
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2))
    joblib.dump(
        {"model": robust_model, "targets": SHAPE_TARGETS}, ROBUST_MODEL_PATH
    )
    print(f"\nsaved: {OUT_PATH}")
    print(f"saved: {ROBUST_MODEL_PATH}")
    print(f"saved: {NOISE_PRED_PATH}")


if __name__ == "__main__":
    main()
