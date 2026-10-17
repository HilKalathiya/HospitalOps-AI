# HospitalOps AI

> Agentic AI-powered hospital operations intelligence and resource optimization platform.

---

## ✅ Implementation Status: Chunk 3.2 — Scenario Comparison & Simulation UI

| Chunk | Description | Status |
|---|---|---|
| 1.1 | MongoDB Data Model & Persistence Layer | ✅ Complete |
| 1.2 | Authentication + RBAC | ✅ Complete |
| 1.3 | Patient + Admission APIs | ✅ Complete |
| 1.4 | Bed + Resource Management | ✅ Complete |
| 1.5 | Historical Dataset Ingestion (Hero DMC, NHSN & MIMIC-IV) | ✅ Complete |
| 1.6 | Hospital Operations Dashboard | ✅ Complete |
| 2.1 | Data / ML Pipeline Foundation | ✅ Complete |
| 2.2 | Baseline Forecasting Models | ✅ Complete |
| 2.3 | ARIMA + Prophet Statistical Forecasting | ✅ Complete |
| 2.4 | Deep Learning Forecasting (LSTM / Temporal Networks) | ✅ Complete |
| 2.5 | Model Evaluation & Selection Engine | ✅ Complete |
| 2.6 | MLflow Experiment Tracking & Registry Integration | ✅ Complete |
| 2.7 | Forecasting API | ✅ Complete |
| 2.8 | Forecast Dashboard | ✅ Complete |
| 3.1 | What-if Simulation Engine | ✅ Complete |
| 3.2 | Scenario Comparison & Simulation UI | ✅ Complete |
| 4.1 | Resource Optimization Engine (MIP) | ⬜ Planned |
| 5.1 | Agentic AI Orchestration & RAG | ⬜ Planned |


**The core system, ML foundation, deep learning forecasting pipeline, evaluation engine, MLflow tracking, forecasting dashboard, deterministic simulation engine, and interactive scenario comparison workspace are live.**
The backend features strict RBAC, data ingestion, a full walk-forward evaluation ML pipeline, decoupled MLflow experiment tracking, and an auditable what-if simulation engine for modeling admission surges, bed capacity changes, and resource bottlenecks without mutating live hospital state. The frontend provides a production-grade multi-scenario comparison workspace with coordinate-mapped SVG trajectory charts, shortage interval tables, run history drawers, and deep links from the forecast dashboard. All 146 backend tests and frontend production builds pass cleanly.


> 💡 **For Interviewers:** A comprehensive 40-page technical guide to this repository is available at [`docs/HospitalOps_AI_Technical_Interview_Study_Manual.md`](docs/HospitalOps_AI_Technical_Interview_Study_Manual.md).

---

## What Is HospitalOps AI?

HospitalOps AI will eventually become a comprehensive platform for hospital operations teams,
combining:

- **Real-time occupancy intelligence** — live bed and ward utilization
- **ML-powered demand forecasting** — admission and ICU demand prediction
- **What-if simulation** — scenario planning for operational decisions
- **Resource optimization** — staff, bed, and equipment allocation
- **RAG over hospital documents** — policy and procedure retrieval
- **Multi-agent orchestration** — LLM agents coordinating operational workflows
- **Human-in-the-loop approval** — consequential recommendations reviewed before action
- **Auditability** — full trace of decisions and recommendations

This is an **operational decision-support system**. It is not a clinical system and must never
diagnose patients, prescribe treatment, or autonomously make clinical decisions.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Backend | Python 3.11+, FastAPI, Pydantic v2, Uvicorn |
| Database | MongoDB (local Docker / Atlas in production) |
| Cache / Events | Redis |
| Infrastructure | Docker, Docker Compose |
| Testing | pytest (backend), Vitest (frontend, future) |
| Linting | Ruff (Python), ESLint (frontend) |

---

## Repository Structure

```
hospitalops-ai/
├── frontend/            React + TypeScript + Vite frontend
├── backend/             FastAPI Python backend
│   ├── app/
│   │   ├── api/         Route handlers
│   │   ├── core/        Config, logging, exceptions
│   │   ├── models/      Domain models
│   │   ├── schemas/     Pydantic request/response schemas
│   │   ├── services/    Business logic (future)
│   │   └── repositories/ Data access (future)
│   └── tests/
├── ml/                  ML models (future)
├── agents/              Agent orchestration (future)
├── rag/                 RAG pipeline (future)
├── simulation/          What-if simulation (future)
├── optimization/        Resource optimization (future)
├── infra/               Infrastructure / IaC (future)
├── tests/               Cross-service integration tests (future)
├── docs/
│   ├── architecture/    Architecture documentation
│   ├── decisions/       Architecture Decision Records (ADRs)
│   └── development/     Developer guides
├── .env.example         Environment variable template
├── docker-compose.yml   Local development environment
└── AGENTS.md            Engineering constitution
```

---

## Prerequisites

- **Docker Desktop** (v24+) and Docker Compose V2
- **Python 3.11+** (for local backend development without Docker)
- **Node.js 20+** and **npm 10+** (for local frontend development without Docker)
- **Git**

---

## Quick Start (Docker — Recommended)

### 1. Clone and configure

```bash
git clone <repo-url>
cd hospitalops-ai

# Copy and configure environment
cp .env.example .env
# Edit .env if needed — the defaults work for local Docker development
```

> **Windows note**: Use `copy .env.example .env` in Command Prompt, or
> `Copy-Item .env.example .env` in PowerShell.

### 2. Start all services

```bash
docker compose up --build
```

Services will be available at:

| Service | URL |
|---|---|
| Frontend (React) | http://localhost:5173 |
| Backend (FastAPI) | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
| MongoDB | localhost:27017 |
| Redis | localhost:6379 |

---

## Docker Development Commands

### Start

```bash
docker compose up -d           # Start all services in background
docker compose up --build -d   # Rebuild images first, then start
docker compose up backend      # Start backend service only
```

### Stop

```bash
docker compose down            # Stop containers, preserve volumes
docker compose down -v         # Stop containers AND remove volumes (data loss)
```

### Rebuild

```bash
docker compose build --no-cache   # Full clean rebuild of all images
docker compose build backend      # Rebuild backend image only
docker compose build frontend     # Rebuild frontend image only
```

### View logs

```bash
docker compose logs               # All services, current logs
docker compose logs -f            # All services, follow (live tail)
docker compose logs backend       # Backend service only
docker compose logs -f frontend   # Frontend service, live tail
docker compose logs --tail=50 backend  # Last 50 lines of backend
```

### Check status

```bash
docker compose ps                  # Container status and health
```

Wait for all services to show `(healthy)` before making requests.

Expected healthy state:

```
NAME                      STATUS
hospitalops-backend       Up (healthy)
hospitalops-frontend      Up (healthy)
hospitalops-mongodb       Up (healthy)
hospitalops-redis         Up (healthy)
```

### Health check

```bash
curl http://localhost:8000/api/v1/health
```

Expected response:

```json
{
  "status": "ok",
  "app_name": "HospitalOps AI",
  "version": "0.1.0",
  "timestamp": "...",
  "chunk": "0.1 — Foundation"
}
```

---

## Frontend ↔ Backend Connectivity (Docker)

Inside the Docker network:

```
Browser → http://localhost:5173
                ↓
    Vite dev server (frontend container)
    /api requests proxied to → http://backend:8000
                ↓
    FastAPI (backend container)
```

The Vite proxy uses the Docker service name `backend` (not `localhost`) when running inside
Docker Compose. This is configured automatically via the `VITE_API_TARGET` environment variable
in `docker-compose.yml`.

---

## Local Development (Without Docker)

### Backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — ensure MONGODB_URI and REDIS_URL point to running instances

# Start the development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend available at `http://localhost:8000`.
Swagger UI at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

Frontend available at `http://localhost:5173`.

The Vite proxy defaults to `http://localhost:8000` for the backend when `VITE_API_TARGET`
is not set.

---

## Running Tests

### Backend Tests

```bash
cd backend
.venv\Scripts\pytest tests/ -v       # Windows
# or
.venv/bin/pytest tests/ -v           # macOS/Linux
```

### Backend Lint

```bash
cd backend
.venv\Scripts\ruff check .           # Windows
```

### Frontend Build

```bash
cd frontend
npm run build
```

### Frontend Lint

```bash
cd frontend
npm run lint
```

### Machine Learning & Experiment Tracking Tests

```bash
cd backend
.venv\Scripts\pytest tests/test_ml/test_mlflow_tracking.py -v   # Windows
# or
.venv/bin/pytest tests/test_ml/test_mlflow_tracking.py -v       # macOS/Linux
```

---

## MLflow Experiment Tracking (Chunk 2.6)

HospitalOps AI integrates MLflow for experiment tracking and model registry capabilities behind a decoupled `ExperimentTracker` abstraction:
- **Local Store:** Default `sqlite:///backend/ml/mlflow.db` provides zero-config local development and fully supports the MLflow Model Registry (unlike deprecated file stores).
- **Separation of Metrics:** Strict separation between validation metrics (`val_mae`, `val_rmse`, `val_smape`, `val_mape`) and held-out test metrics (`test_mae`, etc.).
- **Privacy & Safety:** Sanitizes all logged parameters and artifacts to scrub PHI (patient IDs, MRNs, notes) and credentials (JWT keys, passwords).
- **Graceful Degradation:** If `MLFLOW_TRACKING_ENABLED=False` or the tracking server is unreachable, the system safely operates via `NullExperimentTracker` without crashing.

### Inspecting Local MLflow Runs

To view experiment runs and parameters in the MLflow UI:

```bash
cd backend
.venv\Scripts\mlflow ui --backend-store-uri sqlite:///backend/ml/mlflow.db --port 5000
```
---

## Forecasting API (Chunk 2.7)

HospitalOps AI exposes verified forecasting models, benchmark evaluation reports, and experiment runs through secure REST endpoints:
- `GET /api/v1/forecast/admissions`: Daily admissions forecasting (Hero DMC daily series), horizon 1–30 days. Resolves validation-winning model by default (`val_mae` from `model_selection_report.json`) with optional model override.
- `GET /api/v1/forecast/icu`: Weekly ICU capacity projections (NHSN HRD `icu_beds_occupied` weekly series), horizon 1–8 weeks. Strictly preserves weekly cadence and physical bed units.
- `GET /api/v1/forecast/occupancy`: Explicit guardrail returning HTTP 400 Bad Request to prevent fabricating occupancy without concurrent population-matched beds/census metrics.
- `GET /api/v1/forecast/benchmarks`: Filtered model-selection benchmarks, cleanly separating validation and held-out test splits.
- `GET /api/v1/forecast/runs`: Paginated historical experiment runs with artifact provenance and UTC timestamps.
- `GET /api/v1/forecast/runs/{run_id}`: Detailed run metadata, target info, metrics, and prediction arrays.

All forecasting endpoints require JWT authentication and `predictions.read` permission (ADMIN, OPERATIONS_MANAGER, DOCTOR).

---

## Forecast Dashboard (Chunk 2.8)

HospitalOps AI provides a production-grade forecasting dashboard (`/forecasts`) connected directly to backend forecasting APIs and the What-if simulation engine:
- **Daily Admissions:** Daily cadence (1D) forecasting on the Hero DMC benchmark with interactive 1–30d horizon selection (+7d, +14d, +30d), connecting historical observations at forecast origin ($T_0$) to model point predictions.
- **Weekly ICU Capacity:** Weekly cadence (1W) facility capacity projections on NHSN HRD with 1–8w horizon toggles (+1w, +2w, +4w, +8w) in physical bed units.
- **Strict Confidence Intervals:** Uncertainty bands are displayed only when the model genuinely generates valid prediction bounds (e.g. Monte Carlo Dropout LSTM).
- **Occupancy Rate Guardrail:** Surfaces clear operational disclaimers and guidance when derived metrics cannot be mathematically grounded without concurrent population-matched capacity.
- **Scenario Overlay:** Visualizes simulated surge projections (+15%, +30%) from the deterministic simulation engine alongside baseline models without mutating operational data.
- **Model Provenance & Inspection:** Validation-based winner leaderboard (`val_mae`) with held-out test MAE isolation and clickable JSON run inspection modal.

---

## Scenario Comparison & Simulation UI (Chunk 3.2)

HospitalOps AI provides an interactive what-if scenario comparison workspace (`/simulations`) that allows operational managers to model operational stress scenarios, compare them against a baseline, and inspect capacity shortages:
- **Interactive Scenario Builder:** Supports three deterministic scenario archetypes:
  - `ADMISSION_SURGE`: Scale prospective admission volume by $\pm X\%$ (with quick presets like +15%, +30%) over a 1–30 day horizon.
  - `BED_CAPACITY_CHANGE`: Model hypothetical additions or subtractions of operational physical beds ($\pm 50$ beds, e.g. +10, +25, -10 beds) while strictly isolating hypothetical capacity adjustments from live bed inventory.
  - `RESOURCE_BOTTLENECK`: Stress-test resource demand ratios (ventilators, infusion pumps, dialysis machines) per occupied bed against verified current inventory counts.
- **Multi-Scenario Comparison Matrix:** Orchestrates multiple scenarios against a common baseline, displaying side-by-side peak occupancy %, peak bed deficits, shortage duration, cumulative unmet admissions, and bottleneck resources.
- **Coordinate-Mapped SVG Trajectory Chart:** Visualizes baseline curves, up to 4 scenario trajectories, effective bed capacity thresholds ($C$), and shaded deficit zones with interactive hover tooltips and series toggles.
- **Shortage Interval Breakdown:** Provides contiguous period breakdowns (start day, end day, duration, peak deficit, and affected resource) and deterministic operational takeaways.
- **Run History & JSON Inspection:** Slide-over run history drawer with timestamped runs and raw JSON inspection modals directly from backend response contracts.
- **Forecast Dashboard Integration:** Seamless navigation between forecasting (`/forecasts`) and scenario modeling (`/simulations`) with verified parameter reuse.

---

## Environment Configuration

Copy `.env.example` to `.env` and configure:

| Variable | Description | Required |
|---|---|---|
| `APP_ENV` | Runtime environment (`development` / `staging` / `production`) | Yes |
| `APP_NAME` | Application name | Yes |
| `MONGODB_URI` | MongoDB connection URI | Yes |
| `MONGODB_DATABASE` | Database name | Yes |
| `REDIS_URL` | Redis connection URL | Yes |
| `CORS_ORIGINS` | Allowed CORS origins (comma-separated) | No |
| `LOG_LEVEL` | Logging level | No |
| `BACKEND_PORT` | Backend port override (default: 8000) | No |
| `FRONTEND_PORT` | Frontend port override (default: 5173) | No |
| `MLFLOW_TRACKING_ENABLED` | Enable MLflow tracking in pipeline runs (default: `False`) | No |
| `MLFLOW_TRACKING_URI` | MLflow tracking store URI (default: `sqlite:///backend/ml/mlflow.db`) | No |
| `MLFLOW_EXPERIMENT_NAME` | MLflow experiment group name (default: `hospitalops-forecasting`) | No |

See `.env.example` for the full list including future-chunk placeholders.

**Never commit `.env` files or real credentials.**

---

## Architecture

See [`docs/architecture/overview.md`](docs/architecture/overview.md) for the full architecture documentation.

See [`docs/decisions/`](docs/decisions/) for Architecture Decision Records (ADRs 001–005).

---

## Contributing

1. Read [`AGENTS.md`](AGENTS.md) — the engineering constitution.
2. Follow the engineering rules therein.
3. Write tests for new backend features.
4. Document architectural decisions as ADRs.
5. Use focused commits per chunk.
