# COMPASS 2026 — plasma shape reconstruction

Monorepo with two independent services:

```text
backend/     FastAPI + image model (ResNet18 features + Ridge per target)
frontend/    React/Vite UI (tables, charts, camera frame upload)
```

The model takes one Photron camera frame and returns all **31 target columns**
from `equil_data.csv` (17 main shape parameters, 13 supplementary parameters,
and the `is_limited` regime flag).

## Backend

Full documentation: [`backend/README.md`](backend/README.md).

```bash
cd backend
uv sync
uv run python -m src.api
```

Swagger: `http://localhost:8000/docs`

Endpoints:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/health` | readiness |
| GET | `/api/v1/model/info` | targets, units, metrics |
| POST | `/api/v1/predict` | multipart image upload |

The stable frontend contract is `values`: exactly 31 keys, where
`is_limited` is a boolean and parameters that are physically undefined in the
predicted configuration are `null`. Extra fields (`parameters`,
`raw_parameters`, `parameter_table`) are available for tables/debugging.

CORS is enabled for `http://localhost:5173` and `http://127.0.0.1:5173`.
Override with `CORS_ORIGINS` (comma-separated) or `CORS_ORIGIN_REGEX`.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

The UI has two modes:

- **Dataset** — browse measured discharges, photos, time series and real values.
- **Prediction** — upload a camera frame; the model returns the 31 values and
  displays them in the same layout as the dataset. If the photo filename exists
  in the dataset, the matching discharge time series and true values are shown
  too.

## Docker

Run the whole stack:

```bash
docker compose up --build -d
```

- frontend: `http://localhost:5173`
- backend: `http://localhost:8000`
- docs: `http://localhost:8000/docs`
- stop: `docker compose down`

The backend is stateless and needs no database for inference. Add
SQLite/Postgres later only if you need request history, users or feedback.

## Model

Test set: 21 unseen discharges, 32 444 frames, split by whole discharges.

| Target group | Result |
|---|---|
| Elongation / triangularity / `a` | R² ≈ 0.88–0.95 |
| Absolute R/Z position | MAE ≈ 3–4 mm, R² ≈ 0.56–0.69 |
| X-point / strike points | MAE ≈ 1–5 mm |
| Limiter contact | MAE ≈ 36 / 57 mm (hardest) |
| `is_limited` | accuracy 96.3 %, AUC 0.988 |
| Latency (CPU container) | ≈ 14–25 ms per frame |

Image-only is good for shape, but absolute position and limiter contact are
fundamentally harder from one frame. Magnetic-only reconstruction is much more
accurate (centre MAE ≈ 0.4 mm, R² > 0.98); details and ablations are in
`backend/README.md` and `backend/infra/ai/`.
