from __future__ import annotations

import io
import json
from typing import Any

from PIL import Image

from infra.ai.config import CAMERA_METRICS_PATH
from infra.ai.predictor import PlasmaPredictor
from infra.ai.targets import GROUPS, MAIN_17, UNITS


class InvalidImageError(ValueError):
    pass


class PlasmaService:
    """Application service: image bytes -> plasma parameters."""

    def __init__(self) -> None:
        self.predictor = PlasmaPredictor()

    def warmup(self) -> None:
        self.predictor.warmup()

    def predict(self, image: Image.Image) -> dict[str, Any]:
        result = self.predictor.predict(image)
        # Plochá verze odpovědi: 30 regresních výstupů + is_limited = 31 hodnot.
        result["values"] = {
            **result["parameters"],
            "is_limited": result["regime"]["is_limited"],
        }
        return result

    def predict_bytes(self, content: bytes) -> tuple[dict[str, Any], Image.Image]:
        try:
            image = Image.open(io.BytesIO(content))
            image.load()
        except Exception as exc:
            raise InvalidImageError(f"cannot read image: {exc}") from exc
        return self.predict(image), image

    def model_info(self) -> dict[str, Any]:
        payload: dict[str, Any] = json.loads(CAMERA_METRICS_PATH.read_text())
        return {
            "main_17": payload.get("main_17", MAIN_17),
            "extra_targets": payload.get("extra_targets", []),
            "units": payload.get("units", UNITS),
            "groups": payload.get("groups", GROUPS),
            "regression_metrics": payload.get("regression", {}),
            "regime_metrics": payload.get("classification", {}),
            "split": payload.get("split", {}),
        }
