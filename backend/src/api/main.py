from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.core.config import API_V1_PREFIX, APP_TITLE, APP_VERSION, CORS_ORIGINS
from src.api.v1.router import api_router
from src.services.plasma_service import PlasmaService


@asynccontextmanager
async def lifespan(app: FastAPI):
    service = PlasmaService()
    service.warmup()
    app.state.plasma_service = service
    yield
    app.state.plasma_service = None


app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description="Upload a Photron camera frame and receive plasma shape/position parameters.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=API_V1_PREFIX)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": APP_TITLE,
        "version": APP_VERSION,
        "docs": "/docs",
        "api": API_V1_PREFIX,
    }
