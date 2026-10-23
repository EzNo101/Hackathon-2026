from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from infra.ai.config import ARTIFACTS_DIR, EQUIL_PATH, LIMITER_TARGETS

OUT = Path(__file__).resolve().parent / "img"
OUT.mkdir(exist_ok=True)

plt.rcParams.update(
    {
        "figure.dpi": 160,
        "font.size": 11,
        "axes.grid": True,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)


def limiter_cv() -> None:
    cv = json.loads((ARTIFACTS_DIR / "cv_limiter.json").read_text())
    x = np.arange(len(LIMITER_TARGETS))
    width = 0.36
    base = [cv["baseline"][t]["mean"] * 1000 for t in LIMITER_TARGETS]
    base_std = [cv["baseline"][t]["std"] * 1000 for t in LIMITER_TARGETS]
    two = [cv["two_stage"][t]["mean"] * 1000 for t in LIMITER_TARGETS]
    two_std = [cv["two_stage"][t]["std"] * 1000 for t in LIMITER_TARGETS]

    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.bar(x - width / 2, base, width, yerr=base_std, capsize=4, label="baseline", color="#9aa5b1")
    ax.bar(x + width / 2, two, width, yerr=two_std, capsize=4, label="two-stage", color="#2a9d8f")
    for i, (b, t) in enumerate(zip(base, two)):
        ax.text(i - width / 2, b + 1.2, f"{b:.1f}", ha="center", fontsize=9)
        ax.text(i + width / 2, t + 1.2, f"{t:.1f}", ha="center", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(LIMITER_TARGETS)
    ax.set_ylabel("MAE [mm]")
    ax.set_title("Limiter: baseline vs two-stage (GroupKFold 5)")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "limiter_cv.png", bbox_inches="tight")
    plt.close(fig)


def parity() -> None:
    pred = pd.read_csv(ARTIFACTS_DIR / "test_predictions.csv")
    targets = ["R_mag_axis", "Z_mag_axis", "elongation"]

    fig, axes = plt.subplots(1, 3, figsize=(10, 3.4))
    for ax, target in zip(axes, targets):
        true = pred[f"{target}_true"].dropna()
        p = pred.loc[true.index, f"{target}_pred"]
        ax.scatter(true, p, s=3, alpha=0.2, color="#1f4e79")
        lo = min(float(true.min()), float(p.min()))
        hi = max(float(true.max()), float(p.max()))
        ax.plot([lo, hi], [lo, hi], "--", color="#e76f51", lw=1)
        ax.set_title(target)
        ax.set_xlabel("skutečnost")
        ax.set_ylabel("predikce")
    fig.tight_layout()
    fig.savefig(OUT / "parity.png", bbox_inches="tight")
    plt.close(fig)


def limiter_points() -> None:
    df = pd.read_csv(EQUIL_PATH)
    lim = df[df[LIMITER_TARGETS].notna().all(axis=1)]
    inner = lim["R_limiter"] <= 0.35

    fig, ax = plt.subplots(figsize=(4.8, 4.2))
    ax.scatter(
        lim.loc[inner, "R_limiter"],
        lim.loc[inner, "Z_limiter"],
        s=3,
        alpha=0.2,
        label="inner (R ≤ 0.35)",
        color="#2a9d8f",
    )
    ax.scatter(
        lim.loc[~inner, "R_limiter"],
        lim.loc[~inner, "Z_limiter"],
        s=3,
        alpha=0.2,
        label="other",
        color="#e76f51",
    )
    ax.set_xlabel("R_limiter [m]")
    ax.set_ylabel("Z_limiter [m]")
    ax.set_title("Bod kontaktu s limiterem")
    ax.legend(frameon=False, markerscale=4)
    fig.tight_layout()
    fig.savefig(OUT / "limiter_points.png", bbox_inches="tight")
    plt.close(fig)


def cv_mae() -> None:
    cv = json.loads((ARTIFACTS_DIR / "cv_magnetic.json").read_text())["base"]
    names = ["R_mag_axis", "Z_mag_axis", "a", "R_geom", "Z_geom"]
    labels = ["R mag. osa", "Z mag. osa", "a", "R geom.", "Z geom."]
    values = [cv[n]["mean"] * 1000 for n in names]
    errors = [cv[n]["std"] * 1000 for n in names]

    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    ax.barh(labels, values, xerr=errors, capsize=4, color="#1f4e79")
    ax.invert_yaxis()
    ax.set_xlabel("MAE [mm]")
    ax.set_title("GroupKFold(5): chyba polohy plazmatu")
    fig.tight_layout()
    fig.savefig(OUT / "cv_mae.png", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    limiter_cv()
    parity()
    limiter_points()
    cv_mae()
    print("saved:", sorted(p.name for p in OUT.glob("*.png")))
