from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from src.api.deps import get_plasma_service
from src.services.plasma_service import PlasmaService

router = APIRouter()


@router.get("/model/info")
def model_info(
    service: Annotated[PlasmaService, Depends(get_plasma_service)],
) -> dict[str, Any]:
    info: dict[str, Any] = service.model_info()
    return info
