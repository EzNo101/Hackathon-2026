# COMPASS 2026 — plasma shape reconstruction

Monorepo with two independent services:

```text
backend/     FastAPI + image model (ResNet18 features + Ridge per target)
frontend/    React/Vite UI (tables, charts, camera frame upload)
```

## Backend

See [`backend/README.md`](backend/README.md).

```bash
cd backend
uv sync
uv run python -m src.api
```

Swagger: `http://localhost:8000/docs`

## Frontend

```bash
cd frontend
npm install
npm run dev
```

## Docker

Run the whole stack:

```bash
docker compose up --build -d
```

- frontend: `http://localhost:5173`
- backend: `http://localhost:8000`
- docs: `http://localhost:8000/docs`

CORS is enabled for `http://localhost:5173` and `http://127.0.0.1:5173`.
Override with `CORS_ORIGINS` (comma-separated) or `CORS_ORIGIN_REGEX`.
The backend is stateless and needs no database for inference.
