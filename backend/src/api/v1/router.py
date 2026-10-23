from __future__ import annotations

from fastapi import APIRouter

from src.api.v1.endpoints import health, model, predict

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(model.router, tags=["model"])
api_router.include_router(predict.router, tags=["predict"])
