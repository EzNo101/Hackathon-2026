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

`POST /predict` response includes:

```json
{
  "values": {
    "is_limited": true,
    "plasma_current": -200029.5,
    "R_mag_axis": 0.589,
    "...": "all 31 target columns"
  },
  "regime": {
    "is_limited": true,
    "label": "limited",
    "probability_limited": 1.0,
    "probability_diverted": 0.0
  },
  "latency_ms": 13.9,
  "model": { "device": "cpu", "image_encoder": "resnet18-imagenet1k_v1" }
}
```

`values` is the stable frontend contract: exactly 31 keys, invalid parameters
are `null`, and `is_limited` is a boolean. Extra fields (`parameters`,
`raw_parameters`, `parameter_table`, `main_17`) are kept for debugging and
tables.

Environment variables:

- `PLASMA_DEVICE` — `cpu` or `mps` (default auto; Docker uses `cpu`).
- `CORS_ORIGINS` — comma-separated list, default `http://localhost:5173,http://127.0.0.1:5173`.
- `CORS_ORIGIN_REGEX` — optional regex fallback for other local dev ports.

The production model is committed at
`infra/ai/artifacts/camera_all_targets.joblib`. Large training caches are not
part of the image.
