# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:0.10.12 AS uv

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_CACHE_DIR=/tmp/uv-cache \
    TORCH_HOME=/app/.cache/torch \
    PLASMA_DEVICE=cpu \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /uvx /bin/

RUN useradd --create-home --uid 10001 appuser \
    && chown appuser:appuser /app
USER appuser

COPY --chown=appuser:appuser pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/tmp/uv-cache,uid=10001,gid=10001 \
    uv sync --frozen --no-dev --no-install-project

COPY --chown=appuser:appuser src ./src
COPY --chown=appuser:appuser infra ./infra
RUN --mount=type=cache,target=/tmp/uv-cache,uid=10001,gid=10001 \
    uv sync --frozen --no-dev

# Bake ResNet18 weights into the image so the container does not download
# anything on first request.
RUN python -c "from torchvision.models import resnet18, ResNet18_Weights; resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health')" || exit 1

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
