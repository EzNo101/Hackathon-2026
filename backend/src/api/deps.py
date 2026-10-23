from __future__ import annotations

from fastapi import HTTPException, Request

from src.services.plasma_service import PlasmaService


def get_plasma_service(request: Request) -> PlasmaService:
    service = getattr(request.app.state, "plasma_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="model is still loading")
    return service
