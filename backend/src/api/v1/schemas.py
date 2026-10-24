from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class Regime(BaseModel):
    is_limited: bool
    label: str
    probability_limited: float
    probability_diverted: float


class ParameterRow(BaseModel):
    key: str
    label: str
    value: float | None
    raw_value: float | None
    unit: str
    group: str
    valid: bool


class ModelMeta(BaseModel):
    image_encoder: str
    regressor: str
    device: str


class PredictionResponse(BaseModel):
    filename: str | None = None
    image_size: list[int] | None = None
    regime: Regime
    values: dict[str, Any]
    parameters: dict[str, float | None]
    raw_parameters: dict[str, float | None]
    main_17: list[str]
    parameter_table: list[ParameterRow]
    latency_ms: float
    model: ModelMeta


class HealthResponse(BaseModel):
    status: str
    model: str
