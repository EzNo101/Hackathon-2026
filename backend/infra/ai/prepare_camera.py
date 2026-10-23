from __future__ import annotations

import argparse
import json
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from .config import ARTIFACTS_DIR, CAMERA_CSV, JPEG_DIR

SIZE: int = 96
CROP: tuple[int, int, int, int] = (160, 90, 480, 410)
CLASSES: list[str] = ["L-mode", "H-mode", "ELM"]
CACHE_PATH: Path = ARTIFACTS_DIR / f"camera_cache_{SIZE}.npy"
INDEX_PATH: Path = ARTIFACTS_DIR / "camera_index.csv"
META_PATH: Path = ARTIFACTS_DIR / "camera_cache_meta.json"


def _load_one(args: tuple[int, str]) -> tuple[int, np.ndarray]:
    i, filename = args
    with Image.open(JPEG_DIR / filename) as img:
        img = img.convert("RGB").crop(CROP).resize((SIZE, SIZE), Image.Resampling.BILINEAR)
        arr = np.asarray(img, dtype=np.uint8)
    return i, arr


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    args = parser.parse_args()

    if CACHE_PATH.exists() and INDEX_PATH.exists() and not args.force:
        print(f"cache already exists: {CACHE_PATH}")
        return

    cam = pd.read_csv(CAMERA_CSV).reset_index(drop=True)
    n = len(cam)
    print(f"frames: {n:,}   size: {SIZE}x{SIZE}   crop: {CROP}")

    cache = np.lib.format.open_memmap(
        CACHE_PATH, mode="w+", dtype=np.uint8, shape=(n, SIZE, SIZE, 3)
    )

    total = np.zeros(3, dtype=np.float64)
    total_sq = np.zeros(3, dtype=np.float64)
    done = 0
    tasks = list(zip(range(n), cam["filename"].tolist()))
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for i, arr in pool.map(_load_one, tasks, chunksize=256):
            cache[i] = arr
            flat = arr.reshape(-1, 3).astype(np.float64)
            total += flat.sum(axis=0)
            total_sq += (flat**2).sum(axis=0)
            done += 1
            if done % 10_000 == 0:
                print(f"  {done:,}/{n:,}", flush=True)

    cache.flush()
    del cache

    pixels = n * SIZE * SIZE
    mean = total / pixels
    std = np.sqrt(total_sq / pixels - mean**2)

    index = cam[["filename", "discharge", "time", "mode"]].copy()
    index.insert(0, "row", np.arange(n))
    index["label"] = index["mode"].map({name: i for i, name in enumerate(CLASSES)})
    index.to_csv(INDEX_PATH, index=False)

    meta = {
        "size": SIZE,
        "crop": list(CROP),
        "n_frames": n,
        "classes": CLASSES,
        "mean": mean.tolist(),
        "std": std.tolist(),
    }
    META_PATH.write_text(json.dumps(meta, indent=2))

    print(f"saved: {CACHE_PATH} ({CACHE_PATH.stat().st_size / 1e9:.2f} GB)")
    print(f"saved: {INDEX_PATH}")
    print(f"saved: {META_PATH}")
    print(f"mean RGB: {mean.round(2).tolist()}   std RGB: {std.round(2).tolist()}")


if __name__ == "__main__":
    main()
