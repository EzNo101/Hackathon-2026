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

```bash
docker build -t compass-backend ./backend
docker run --rm -p 8000:8000 compass-backend
```

`docker-compose.yml` at the repository root:

```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - PLASMA_DEVICE=cpu
      - CORS_ORIGINS=*

  frontend:
    build: ./frontend
    ports:
      - "5173:80"
    depends_on:
      - backend
```

The backend is stateless and needs no database for inference.
