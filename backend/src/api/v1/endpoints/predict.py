from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from src.api.deps import get_plasma_service
from src.api.v1.schemas import PredictionResponse
from src.services.plasma_service import InvalidImageError, PlasmaService

router = APIRouter()


@router.post("/predict", response_model=PredictionResponse)
async def predict(
    file: Annotated[UploadFile, File()],
    service: Annotated[PlasmaService, Depends(get_plasma_service)],
) -> PredictionResponse:
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="file must be an image")

    content = await file.read()
    try:
        result, image = service.predict_bytes(content)
    except InvalidImageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result["filename"] = file.filename
    result["image_size"] = [image.width, image.height]
    return PredictionResponse.model_validate(result)
