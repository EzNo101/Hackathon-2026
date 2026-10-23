# COMPASS plasma shape from a camera image

Image-only model + FastAPI backend. The user uploads one Photron camera frame and
the API returns the plasma shape/position parameters, the limited/diverted
regime, and a frontend-ready table.

No notebooks are needed to train, evaluate, or serve the model.

## What the API returns

- **17 main plasma parameters** (`main_17`): magnetic axis, elongation,
  triangularities, minor radius, geometric centre, X-point, strike points,
  limiter contact.
- **13 extra target columns** from the dataset: `plasma_current`, top/bottom/
  outer/inner boundary points, four squareness values, and `is_limited` as the
  regime prediction.
- In total the API returns **all 31 Y columns** from `equil_data.csv`:
  30 regression outputs + `is_limited`.
- Per-row metadata: unit, group, `valid` flag, raw model value.
- `latency_ms`, model name, encoder, device.

Fields that are physically undefined in the predicted regime are returned as
`null` in `parameters` (e.g. X-point/strike points for a limited plasma, or
`R_limiter/Z_limiter` for a diverted plasma). The unmasked value stays available
as `raw_value` in `parameter_table` and in `raw_parameters`.

## Data

Data are not part of the repository. Put the unpacked folders here (or set
`COMPASS_DATA_DIR`):

```bash
export COMPASS_DATA_DIR=/path/to/data
# expected: $COMPASS_DATA_DIR/uloha_1-magneticka_data/equil_data.csv
#           $COMPASS_DATA_DIR/uloha_1-photron/camera_data.csv
#           $COMPASS_DATA_DIR/uloha_1-photron/jpeg/
```

## Train

```bash
cd backend
uv sync

# 1. cache camera frames + metadata (only if backend/infra/ai/artifacts/camera_cache_96.npy is missing)
uv run python -m infra.ai.prepare_camera

# 2. attach equilibrium targets to each camera frame (discharge/time nearest match)
uv run python -m infra.ai.match_camera

# 3. main image model: ResNet18 features + one ridge per target
uv run python -m infra.ai.train_camera_all
```

Outputs:

- `backend/infra/ai/artifacts/camera_all_targets.joblib` — models used by the API
- `backend/infra/ai/artifacts/camera_all_targets.json` — per-target MAE/RMSE/R², split, latency
- `backend/infra/ai/artifacts/camera_features_resnet18.npy` — cached 512-D image features

The small production bundle `backend/infra/ai/artifacts/camera_all_targets.joblib`
(≈100 KB) is committed to git. Large training caches (`*.npy`, `*.pt`) stay
git-ignored. On first run, torchvision downloads ResNet18 weights into
`~/.cache/torch/hub/checkpoints/`; copy that file manually if the target machine
is offline.

Supporting experiments (no notebooks):

```bash
uv run python -m infra.ai.train_magnetic        # magnetic-only baseline
uv run python -m infra.ai.train_camera_image    # image/magnetic/late/feature fusion
uv run python -m infra.ai.ablate_magnetic       # IPR/FL ablation + permutation importance
uv run python -m infra.ai.ablate_image          # crops, grayscale, learning curve, jitter
uv run python -m infra.ai.noise_robustness      # noisy/drifted magnetics + fusion rescue
```

## Run the backend

```bash
cd backend
uv sync
uv run python -m src.api          # robust: works from any directory
# or
uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

If you see `ModuleNotFoundError: No module named 'src'`, run `uv sync` first —
the project is installed as an editable package by `pyproject.toml`.

Swagger UI: `http://localhost:8000/docs`

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/health` | readiness |
| GET | `/api/v1/model/info` | target list, units, metrics |
| POST | `/api/v1/predict` | upload image, get all parameters |

Example:

```bash
curl -X POST \
  -F "file=@data/uloha_1-photron/jpeg/example.jpg" \
  http://localhost:8000/api/v1/predict
```

## Docker

```bash
docker build -t compass-backend ./backend
docker run --rm -p 8000:8000 compass-backend
```

A `docker-compose.yml` at the repository root can use:

```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
```

Response shape:

```json
{
  "regime": {
    "is_limited": true,
    "label": "limited",
    "probability_limited": 0.99,
    "probability_diverted": 0.01
  },
  "parameters": {
    "R_mag_axis": 0.55,
    "Z_mag_axis": 0.01,
    "elongation": 1.7,
    "R_x_point": null,
    "R_limiter": 0.347
  },
  "main_17": ["R_mag_axis", "Z_mag_axis", "..."],
  "parameter_table": [
    {
      "key": "R_mag_axis",
      "label": "R magnetic axis",
      "value": 0.55,
      "raw_value": 0.55,
      "unit": "m",
      "group": "position_shape",
      "valid": true
    }
  ],
  "latency_ms": 9.5,
  "model": {
    "image_encoder": "resnet18-imagenet1k_v1",
    "regressor": "ridge-per-target",
    "device": "mps"
  }
}
```

CORS is open (`*`) for local frontend development.

## Image-only results

Test set: 21 discharges, 32 444 frames, split by whole discharges. No camera
frame from a test discharge is used in training.

| Target | MAE | R² |
|---|---:|---:|
| R_mag_axis | 2.90 mm | 0.563 |
| Z_mag_axis | 3.38 mm | 0.694 |
| elongation | 0.0374 | 0.950 |
| triangularity | 0.0204 | 0.931 |
| triangularity_lower | 0.0287 | 0.935 |
| triangularity_upper | 0.0154 | 0.879 |
| a | 2.55 mm | 0.910 |
| R_geom | 2.82 mm | 0.712 |
| Z_geom | 4.24 mm | 0.817 |
| R_x_point | 3.73 mm | 0.606 |
| Z_x_point | 4.11 mm | 0.459 |
| R_strike_point_1 | 4.27 mm | 0.666 |
| Z_strike_point_1 | 1.72 mm | 0.619 |
| R_strike_point_2 | 4.85 mm | 0.370 |
| Z_strike_point_2 | 0.94 mm | 0.405 |
| R_limiter | 36.0 mm | 0.538 |
| Z_limiter | 57.4 mm | 0.725 |
| plasma_current | 30.0 kA | 0.738 |
| is_limited | acc 0.963 | AUC 0.988 |

Extra targets (also returned by the API):

| Target | MAE | R² |
|---|---:|---:|
| R_top | 4.24 mm | 0.784 |
| Z_top | 6.82 mm | 0.831 |
| R_bottom | 5.80 mm | 0.881 |
| Z_bottom | 9.02 mm | 0.910 |
| R_outer | 4.33 mm | 0.746 |
| Z_outer | 3.06 mm | 0.833 |
| R_inner | 3.26 mm | 0.906 |
| Z_inner | 32.5 mm | 0.642 |
| squareness_upper_outer | 0.0024 | 0.777 |
| squareness_upper_inner | 0.0410 | 0.709 |
| squareness_lower_outer | 0.0153 | 0.934 |
| squareness_lower_inner | 0.0501 | 0.325 |

Interpretation:

- Image-only is good for **shape** (elongation/triangularity/a R² ≈ 0.88–0.95).
- Absolute **R/Z position** is fundamentally difficult from one camera frame:
  a few mm error, R² ≈ 0.56–0.69.
- Divertor and limiter targets are the hardest; images contain only indirect
  evidence of the X-point and wall contact.
- Measured latency: **≈9–16 ms per frame on Apple MPS** after warm-up, so the
  service is fast enough for offline analysis and close to real-time control.
  CPU-only inference is slower.

If magnetic coils are available, the magnetic model is much more accurate
(centre MAE ≈0.4 mm, R² >0.98). Under noise/drift, noise-augmented magnetic
training reduces MAE from 17.2 mm to 7.4 mm, and image+magnetic fusion is better
than either modality under corrupted magnetic measurements.

## Source layout

```
backend/infra/ai/            AI / ML layer
  config.py                  paths and feature/target constants
  targets.py                 main 17 targets, units, groups, labels
  predictor.py               single-image inference wrapper
  artifacts/                 models, caches, metrics (git-ignored binaries)
  prepare_camera.py          JPEG crop/resize cache
  match_camera.py            camera frame <-> equilibrium target matching
  camera_image.py            ResNet18 feature extraction
  camera_shape.py            frame-target matching, discharge split
  train_camera_all.py        image-only model used by the API
  train_camera_image.py      image/magnetic/fusion comparison
  train_magnetic.py          magnetic-only baseline and limiter model
  ablate_magnetic.py         magnetic input ablation/importance
  ablate_image.py            crop/grayscale/learning-curve/jitter analysis
  noise_robustness.py        noisy/drifted magnetics + multimodal rescue

backend/src/api/             HTTP layer
  main.py                    FastAPI app factory + lifespan
  core/config.py             API prefix, CORS, app metadata
  deps.py                    dependency providers
  v1/router.py               /api/v1 router
  v1/endpoints/              health.py, model.py, predict.py
  v1/schemas.py              Pydantic response models

backend/src/services/        application layer
  plasma_service.py          image bytes -> model -> response payload

```

No database is required for inference: the service is stateless and loads the
model bundle once at startup. Add SQLite/Postgres later only if you need request
history, users, or feedback storage.

Legacy notebooks are left in `notebooks/` for history only; they are not part of
the training or serving path.
