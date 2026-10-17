# HospitalOps AI

> Agentic AI-powered hospital operations intelligence and resource optimization platform.

---

## ✅ Implementation Status: Chunk 3.3 — Resource Optimization Engine

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
| 3.3 | Resource Optimization Engine (MIP) | ✅ Complete |
| 3.4 | Optimization UI & Plan Review | ⬜ Planned |
| 4.1 | Agentic AI Orchestration & RAG | ⬜ Planned |


**The core system, ML forecasting foundation, evaluation engine, simulation workspace, and mathematical resource optimization engine are live.**
The platform features strict RBAC, data ingestion, a full walk-forward evaluation ML pipeline, decoupled MLflow experiment tracking, an auditable what-if simulation engine, and an exact Mixed-Integer Linear Programming (MILP) planning engine powered by HiGHS/SciPy. The engine optimizes department surge bed activations and critical movable equipment distributions against projected demand over a multi-period horizon, validating every constraint independently and reporting counterfactual baseline improvements without mutating live operational state. All 159 backend tests and frontend production builds pass cleanly.


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

## Resource Optimization Engine (Chunk 3.3)

HospitalOps AI provides a mathematically grounded Mixed-Integer Linear Programming (MILP) planning engine that optimizes hospital bed capacities and movable critical equipment distributions against projected demand over a multi-period horizon:
- **Mathematical MILP Formulation:**
  - **Decision Variables:** Department surge bed activations ($x_{d,t}^{\text{surge}} \in \mathbb{Z}_{\ge 0}$), unmet bed shortages ($s_{d,t}^{\text{bed}} \ge 0$), movable equipment allocations ($y_{r,d,t} \in \mathbb{Z}_{\ge 0}$), equipment deficits ($s_{r,d,t}^{\text{equip}} \ge 0$), and equipment transfer churn linearization ($z_{r,d,t}^{\Delta} \ge 0$).
  - **Multi-Objective Balancing:** Minimizes patient bed shortages, unfulfilled equipment requirements, surge bed operational costs, and inter-departmental transfer churn with clinical priority weights ($w^{\text{shortage}}=100, w^{\text{equip}}=50, w^{\text{surge}}=5, w^{\text{transfer}}=1$).
  - **Hard Operational Constraints:** Enforces surge bed pool conservation ($\sum_d x_{d,t}^{\text{surge}} \le B^{\text{surge}}$), equipment inventory conservation ($\sum_d y_{r,d,t} \le Q_r^{\text{avail}}$), and linearized demand balance across every horizon period.
- **High-Performance Exact Solver:**
  - Integrated with **HiGHS** via `scipy.optimize.milp` without external C-binary bloat. Solves multi-department 30-day horizons in $<50$ milliseconds with guaranteed integrality ($\le 10^{-5}$) and optimality gap tracking.
- **Independent Solution Validator:**
  - Automatically verifies solution feasibility, checks bounds, audits non-negativity and integer tolerances, detects active binding bottlenecks (e.g. exhausted surge beds or critical equipment inventory), and diagnoses infeasibilities.
- **Counterfactual Baseline Comparison:**
  - Evaluates an unoptimized status quo baseline ($x^{\text{surge}}=0$, static inventory) against identical demand to quantify exact percentage reduction in shortages and net patient-days saved.
- **Auditable REST API & RBAC:**
  - `POST /api/v1/optimization/solve`: Run MILP optimization across departments, movable equipment, and horizons.
  - `GET /api/v1/optimization/baseline`: Retrieve current operational baseline data (beds, inventory, 7-day forecast demand).
  - `GET /api/v1/optimization/runs`: Paginated historical optimization runs.
  - `GET /api/v1/optimization/runs/{run_id}`: Detailed plan inspection, objective breakdown, and recommendations.
  - Secured via `optimization.run` and `optimization.read` permissions.
- **Strict Operational Safety Boundary:**
  - Produces advisory allocation recommendations for human review. Never mutates live operational bed, patient, admission, or equipment records.

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
