from __future__ import annotations

import os

API_V1_PREFIX: str = os.getenv("API_V1_PREFIX", "/api/v1")
CORS_ORIGINS: list[str] = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "*").split(",")
    if origin.strip()
]
APP_TITLE: str = "COMPASS plasma shape API"
APP_VERSION: str = "1.0.0"
