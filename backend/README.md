# COMPASS backend

FastAPI service: upload one camera frame, receive all 31 target columns from
`equil_data.csv` (17 main shape parameters, 13 supplementary targets, and the
limited/diverted regime).

## Local run

```bash
uv sync
uv run python -m src.api
```

or:

```bash
uv run uvicorn src.api.main:app --reload --port 8000
```

Swagger UI: `http://localhost:8000/docs`

## Docker

```bash
docker build -t compass-backend .
docker run --rm -p 8000:8000 compass-backend
```

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/health` | readiness |
| GET | `/api/v1/model/info` | target list, units, metrics |
| POST | `/api/v1/predict` | multipart image upload |

Environment variables:

- `PLASMA_DEVICE` — `cpu` or `mps` (default auto; Docker uses `cpu`).
- `CORS_ORIGINS` — comma-separated list, default `*`.

The production model is committed at
`infra/ai/artifacts/camera_all_targets.joblib`. Large training caches are not
part of the image.
