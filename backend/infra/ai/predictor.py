from __future__ import annotations

import os
import time
from typing import Any

import joblib
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from torchvision.models import ResNet18_Weights, resnet18

from .camera_image import IMAGENET_MEAN, IMAGENET_STD, RESIZE
from .config import CAMERA_MODEL_PATH
from .prepare_camera import CROP
from .targets import DIVERTOR_FIELDS, GROUPS, LABELS, LIMITER_FIELDS, MAIN_17, UNITS


class PlasmaPredictor:
    """Single-image inference wrapper used by the API."""

    def __init__(self) -> None:
        bundle = joblib.load(CAMERA_MODEL_PATH)
        self.models: dict[str, Any] = bundle["models"]
        self.classifier: Any = bundle["classifier"]
        self.targets: list[str] = bundle["targets"]
        self.main_17: list[str] = bundle["main_17"]
        requested = os.getenv("PLASMA_DEVICE", "").strip()
        if requested:
            self.device = torch.device(requested)
        else:
            self.device = torch.device(
                "mps" if torch.backends.mps.is_available() else "cpu"
            )
        encoder = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
        encoder.fc = torch.nn.Identity()  # pyright: ignore[reportAttributeAccessIssue]
        encoder.eval()
        self.encoder = encoder.to(self.device)
        self.mean = torch.from_numpy(IMAGENET_MEAN).to(self.device).view(1, 3, 1, 1)
        self.std = torch.from_numpy(IMAGENET_STD).to(self.device).view(1, 3, 1, 1)

    def _preprocess(self, image: Image.Image) -> torch.Tensor:
        image = image.convert("RGB")
        if image.width >= CROP[2] and image.height >= CROP[3]:
            image = image.crop(CROP)
        image = image.resize((96, 96), Image.Resampling.BILINEAR)
        array = np.asarray(image, dtype=np.float32) / 255.0
        x = torch.from_numpy(array).permute(2, 0, 1).unsqueeze(0).to(self.device)
        x = F.interpolate(x, size=(RESIZE, RESIZE), mode="bilinear", align_corners=False)
        return (x - self.mean) / self.std

    def _features(self, image: Image.Image) -> np.ndarray:
        with torch.no_grad():
            return self.encoder(self._preprocess(image)).cpu().numpy().astype(np.float32)

    def warmup(self) -> None:
        self.predict(Image.new("RGB", (640, 500), color=(0, 0, 0)))

    def predict(self, image: Image.Image) -> dict[str, Any]:
        t0 = time.perf_counter()
        features = self._features(image)

        raw: dict[str, float | None] = {}
        for target, model in self.models.items():
            value = float(np.asarray(model.predict(features))[0])
            raw[target] = value if np.isfinite(value) else None

        prob_limited = float(np.asarray(self.classifier.predict_proba(features))[0, 1])
        is_limited = prob_limited >= 0.5

        valid = {target: True for target in self.targets}
        for target in DIVERTOR_FIELDS:
            valid[target] = not is_limited
        for target in LIMITER_FIELDS:
            valid[target] = is_limited

        parameters = {
            target: (raw[target] if valid[target] else None) for target in self.targets
        }
        table = [
            {
                "key": target,
                "label": LABELS.get(target, target),
                "value": parameters.get(target),
                "raw_value": raw.get(target),
                "unit": UNITS.get(target, "-"),
                "group": GROUPS.get(target, "other"),
                "valid": valid.get(target, True),
            }
            for target in self.targets
        ]

        values: dict[str, object] = dict(parameters)
        values["is_limited"] = bool(is_limited)

        return {
            "regime": {
                "is_limited": bool(is_limited),
                "label": "limited" if is_limited else "diverted",
                "probability_limited": prob_limited,
                "probability_diverted": 1.0 - prob_limited,
            },
            "values": values,
            "parameters": parameters,
            "raw_parameters": raw,
            "main_17": self.main_17 or MAIN_17,
            "parameter_table": table,
            "latency_ms": (time.perf_counter() - t0) * 1e3,
            "model": {
                "image_encoder": "resnet18-imagenet1k_v1",
                "regressor": "ridge-per-target",
                "device": str(self.device),
            },
        }
