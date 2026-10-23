from __future__ import annotations

from fastapi import APIRouter

from src.api.v1.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", model="ready")
