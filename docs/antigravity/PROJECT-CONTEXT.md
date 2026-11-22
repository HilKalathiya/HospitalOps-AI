# HospitalOps AI — Persistent Project Context & Engineering Rules

> **Authoritative Context Document:** This document defines the persistent operational rules, architectural guidelines, data boundaries, and active roadmap tracking for HospitalOps AI across all Antigravity agent sessions.

---

## 1. Persistent Operational Rules

### Rule 1: Keep Project Instructions and Roadmap Synchronized
After every user-assigned implementation task or completed chunk:
1. Update this persistent task-context document when scope, architectural decisions, or next steps change.
2. Update the authoritative roadmap table in `README.md` and `AGENTS.md` with verified actual status.
3. Update relevant technical documentation in `docs/architecture/`, `docs/decisions/`, and `docs/HospitalOps_AI_Technical_Interview_Study_Manual.md`.
4. Record completed work, incomplete work, blockers, test results, and next dependencies.
5. Ensure instructions never contradict the active repository state.

### Rule 2: Every Completed Task Must Be GitHub Push-Ready
The repository owner personally reviews and pushes commits to GitHub.
* **NEVER execute `git push` unless the user explicitly authorizes it.**
* For every independently completed task or coherent, verified milestone:
  1. Inspect `git status` before editing to preserve unrelated user work.
  2. Implement scope incrementally without unnecessarily rewriting working functionality.
  3. Run all applicable tests, linters, type checks, and builds (`pytest`, `ruff check`, `npm run lint`, `npm run build`).
  4. Inspect the final diff (`git diff --check`).
  5. Verify no sensitive files are staged (`.env`, credentials, private data, local datasets in `HospitalOps-Private-Data/`, generated databases).
  6. Synchronize documentation before the commit.
  7. Create a focused, local Git commit using conventional commit format (e.g. `feat(simulation): implement deterministic what-if scenario engine`).
  8. Report the exact commit hash, message, executed tests, results, and remaining blockers.

### Rule 3: Use Antigravity's Capabilities Appropriately
* Use focused subagents and parallel investigation for heavy read-only exploration, math audits, and test reviews.
* Maintain one primary orchestrator agent responsible for decisions, integration, and final verification.
* Never run multiple concurrent agents modifying the same files without an explicit partitioned ownership strategy.

---

## 2. Hard Healthcare & Data Governance Boundaries

HospitalOps AI is an **operational decision-support system**, NOT a clinical diagnostic or prescribing tool.
1. **The System May:** Analyze operational occupancy, forecast bed/ICU demand, simulate what-if operational scenarios, recommend non-clinical resource allocations, and retrieve administrative policies via RAG.
2. **The System Must Never:** Diagnose patients, prescribe treatments, discharge patients autonomously, or present operational projections as clinical authority.
3. **Data Integrity & Provenance:**
   * **NHSN HRD:** Primary source for facility-level and ICU weekly capacity forecasting.
   * **Hero DMC:** Legacy benchmark for daily admission forecasting.
   * **MIMIC-IV v3.1:** Clinical database for stay-level and patient-level predictions (e.g., ICU length of stay). **Never aggregate MIMIC-IV dates across patients into hospital-wide daily series** because dates are shifted independently per patient.
   * **Protected Data:** All raw MIMIC-IV files stay strictly local in `HospitalOps-Private-Data/` outside git.
4. **Simulation Safety:** What-if simulations are strictly read-only projections. They must never mutate live operational collections (`beds`, `admissions`, `resources`, `patients`).

---

## 3. Project Roadmap & Implementation Status

| Milestone | Chunk | Description | Status | Verification Summary |
|:---|:---|:---|:---|:---|
| **M1: Operational Core** | 1.1 | MongoDB Persistence Layer | ✅ Complete | Schemas, typed repositories, indexes |
| | 1.2 | Authentication & RBAC | ✅ Complete | JWT + Argon2, Admin/Manager/Doctor/Viewer |
| | 1.3 | Patient & Admission APIs | ✅ Complete | REST CRUD, department scoping |
| | 1.4 | Bed & Resource Management | ✅ Complete | State machine, atomic updates, audits |
| | 1.5 | Historical Dataset Ingestion | ✅ Complete | Hero DMC, NHSN HRD, MIMIC-IV pipelines |
| | 1.6 | Operations Dashboard | ✅ Complete | Real-time React telemetry, craft v3 UI |
| **M2: Forecasting Engine** | 2.1 | ML Pipeline Foundation | ✅ Complete | Chronological split, feature engineering |
| | 2.2 | Baseline Forecasting Models | ✅ Complete | Naive, Seasonal Naive, Moving Average |
| | 2.3 | ARIMA & Prophet Comparison | ✅ Complete | SARIMAX, Prophet, walk-forward CV |
| | 2.4 | Deep Learning Forecasting | ✅ Complete | PyTorch LSTM, Monte Carlo Dropout (95% CI) |
| | **2.5** | **Model Evaluation & Selection** | ✅ Complete | Leakage-free validation-only selection, MAE/RMSE/sMAPE/MAPE, benchmark report, 120 tests passed |
| | **2.6** | **MLflow Integration** | ✅ Complete | Decoupled tracker abstraction, SQLite registry backend, split metrics, sanitized artifacts, 10/10 tests passed |
| | **2.7** | **Forecasting API** | ✅ Complete | REST endpoints for admissions, ICU, benchmarks, runs, validation-selected model resolution, 15/15 tests passed |
| | **2.8** | **Forecast Dashboard** | ✅ Complete | Production dashboard, real historical + prediction series, strict CI bounds, 400 guardrail, run inspection, 146 tests passed |
| **M3: Decision Intelligence**| **3.1** | **What-if Simulation Engine** | ✅ Complete | Deterministic engine, 7/7 tests passed, 120 total passed |
| | **3.2** | **Simulation UI & Scenario Comparison** | ✅ Complete | Multi-scenario comparison matrix, SVG trajectory chart, shortage analysis, session persistence & JSON inspect |
| | **3.3** | **Resource Optimization Engine (MIP)** | ✅ Complete | SciPy HiGHS MILP, multi-department surge beds & equipment allocation, counterfactual baseline, 159 tests passed (reconciles former M4 C4.1) |
| | **3.4** | **Recommendation Explanation & Plan Review** | ✅ Complete | Deterministic explanation layer, objective deconstruction, constraint diagnostics, counterfactual baseline comparison, plan review workspace, 166 tests passed |
| | **3.5** | **Unified Decision Workspace** | ✅ Complete | Unified simulation & optimization cockpit, parameter derivation adapter, 3-way decision matrix, provenance tracking, 174 tests passed |
| **M4: Hospital Knowledge & RAG** | **4.1** | **Document Ingestion Pipeline — RAG Knowledge Foundation** | ✅ Complete | Multi-format parsers (PDF, DOCX, MD, TXT, HTML), 10-stage pipeline, PHI/MIMIC quarantine boundary, structure-aware chunking, persistent ChromaDB, 15/15 tests passed |
| | **4.2** | **Semantic Vector Search & Knowledge Retrieval Engine** | ✅ Complete | Vector search over ChromaDB, space compatibility validation, server-side RBAC scoping, repository post-validation, provenance ranking, MRR=1.0, 28/28 tests passed (202 total) |
| | **4.3** | **Retrieval API — RAG Context Retrieval & Assembly Layer** | ✅ Complete | Token-budget-aware context assembly, offline tiktoken cl100k_base counting, prompt boundary guard (<reference_content>), stable citations ([S1], [S2]), ordering strategies, 12/12 tests passed (214 total) |
| | **4.4** | **RAG Answer Generation — Grounded Operational QA** | ✅ Complete | Grounded QA, citation validation, 1-shot retry, clinical safety guard, mock/live LLM provider, 15/15 tests passed (229 total) |
| | **4.5** | **RAG UI — Dedicated Hospital Knowledge Assistant Workspace** | ✅ Complete | Dedicated full-screen cockpit (/knowledge/assistant), XSS-free safe markdown, bidirectional citation pills, dual-tier evidence inspector, token diagnostics, in-memory tab-local session history, 0 lint warnings |
| **M5: Agentic AI** | **5.1** | **First Agent: Hospital Operations Analyst Agent** | ✅ Complete | Autonomous decision intelligence agent (hospital_operations_analyst), 5 read-only domain tools, clinical scope guard, bounded lifecycle, execution trace, 16/16 tests passed (245 total) |
| | **5.2** | **Tool Schemas & Standardized Tool Contracts** | ✅ Complete | Standardized Pydantic v2 schemas, Draft 2020-12 JSON Schema generation, OpenAI function calling export, semver tracking, permission-filtered tool discovery, interactive UI schema inspector, 15/15 tests passed (260 total) |
| | **5.3** | **Agent Orchestration Engine** | ✅ Complete | Controlled lifecycle state machine (14 states), structured task planning, safe tool coordinator with loop prevention, evidence collector with domain classification, citation verification, execution trace API, 17/17 tests passed (277 total) |
| | **5.4** | **Agent State Management & Conversation Continuity** | ✅ Complete | Persistent session scoping (agent_sessions), chronological message turns (agent_messages), bounded context reconstruction with token budgeting, multi-turn conversational continuity, 10/10 tests passed (287 total) |
| | **5.5** | **Agent Memory & Cross-Session Intelligence** | ✅ Complete | User-approved persistent operational memory (agent_memories), deterministic healthcare safety & anti-injection validation, candidate extraction, approval/supersession lifecycle, dedicated preferences workspace, 24/24 tests passed (311 total) |
| | **5.6.1** | **Multi-Agent Architecture & Contracts** | ✅ Complete | Supervisor-and-specialist architecture, Pydantic contracts for delegation/results/traces, strict depth=1 and 4-specialist bounds, extra="forbid", 26/26 tests passed (337 total) |
| | **5.6.2** | **Specialist Agent Implementations** | ✅ Complete | 4 domain specialists (Forecasting, Simulation, Optimization, Knowledge), BaseSpecialist with RBAC & clinical guard, deterministic SpecialistRegistry, 22/22 tests passed (359 total) |
| | **5.6.3** | **Multi-Agent Coordinator & Aggregator** | ⬜ Planned | Concurrency throttling, timeouts, partial failure handling, cross-domain conflict detection |
| | **5.6.4** | **Multi-Agent API & UI Workspace** | ⬜ Planned | REST endpoints, trace inspection, React transparency panel & specialist result cards |
| | **5.6.5** | **Multi-Agent End-to-End Verification** | ⬜ Planned | Comprehensive regression, integration testing, and audit validation |

---

## 4. Completed Workstream: Milestone 3, Chunk 3.1 (What-if Simulation Engine)

* **Status:** Complete & Push-Ready.
* **Scope Delivered:**
  1. **Deterministic Scenario Modeling:** Implemented discrete-time trajectory projection ($A(t)$, $D(t) = \text{Occupied}(t-1)/\text{LOS}$, prospective unconstrained load, realized occupancy, and shortage detection).
  2. **Supported Scenarios:**
     - `ADMISSION_SURGE`: Scales admissions by $\pm X\%$, evaluates occupancy surges and peak bed shortages over horizon.
     - `BED_CAPACITY_CHANGE`: Models physical bed additions/expansions or conversions ($\Delta \text{Beds}$) on shortage duration and peak load.
     - `RESOURCE_BOTTLENECK`: Assesses equipment requirements (e.g. ventilators per occupied bed) against current operational inventory.
  3. **Safety & Isolation:** Strictly read-only against live collections (`beds`, `admissions`, `resources`, `patients`). Simulation runs are written exclusively to `simulation_runs` with audit trail in `audit_logs`.
  4. **RBAC:** Secured behind `simulation.run` (Admin, Manager) and `simulation.read` (Admin, Manager, Doctor, Viewer).

---

## 5. Completed Workstream: Milestone 2, Chunk 2.5 (Model Evaluation and Selection Engine)

* **Status:** Complete & Push-Ready.
* **Scope Delivered:**
  1. **Comprehensive Metric Calculation Suite:**
     - Implemented `calculate_mae`, `calculate_rmse`, `safe_smape`, and `safe_mape` in `app/ml/contracts/evaluation.py`.
     - Preserved physical target units (admissions for daily series, beds for weekly capacity).
     - Robust zero-handling in `safe_mape`: provides `"filter"` (evaluates on non-zero points, returns `0.0%` if all zeros match, or `None` if zero actuals have non-zero predictions to prevent false 0.0% claims), `"epsilon"` (bounded denominator), and `"raise"` modes.
     - Integrated `mape` computation directly into `MLPipelineOrchestrator` evaluation pipeline.
  2. **Strict Leakage-Free Model Selection:**
     - `ModelSelector` (`app/ml/selection/selector.py`) selects the optimal model strictly based on validation metrics (`val_mae`, tie-breaker `val_rmse`).
     - Held-out test split metrics are completely isolated from ranking and selection logic, surfaced solely for unbiased post-selection reporting.
     - Guarantees fair comparison across strictly compatible slices (dataset, target, horizon, and cadence).
  3. **Multi-Model Benchmark & Artifact Persistence:**
     - `BenchmarkEvaluator` (`app/ml/selection/benchmark.py`) loads and deduplicates runs across `backend/ml/runs` and `backend/backend/ml/runs`.
     - Generates reproducible, auditable benchmark summaries:
       - `backend/ml/evaluations/model_selection_report.json`
       - `backend/ml/evaluations/model_selection_summary.md`
     - Evaluated across Naive, Seasonal Naive, Moving Average, ARIMA/SARIMAX, Prophet, and LSTM models.
     - Explicitly surfaces missing or failed model runs (`FAILED`, `MISSING`) so gaps are transparent.
  4. **Verification & Testing:**
     - 9 comprehensive tests in `backend/tests/test_ml/test_evaluation_selection.py` (known math examples, zero actuals handling, adversarial leakage tests, split integrity, artifact roundtrip).
     - All 30 ML tests passed (29 passed, 1 skipped).
     - Full test suite: 120 passed, 10 skipped in 38.14s.
     - `ruff check` on backend: 0 errors.
     - Frontend build: built in 1.82s, zero errors.
* **Next Chunk:** Milestone 2, Chunk 2.7 (Forecasting API).

---

## 6. Completed Workstream: Milestone 2, Chunk 2.6 (MLflow Integration)

* **Status:** Complete & Push-Ready.
* **Scope Delivered:**
  1. **Decoupled Experiment Tracker Abstraction:**
     - Created `app/ml/tracking/base.py` defining `ExperimentTracker` protocol and `TrackerRunContext` context manager.
     - Implemented `NullExperimentTracker` (`null_tracker.py`) as a zero-overhead no-op tracker used when tracking is disabled or libraries are absent.
     - Implemented `MLflowTracker` (`mlflow_tracker.py`) managing experiment creation, run contexts, parameter logging, metric logging, and artifact persistence.
     - Dynamic resolution via `get_tracker(config, settings)` (`factory.py`) ensuring environment overrides and per-run config flags (`tracking_enabled`, `tracking_experiment_name`, `tracking_run_name`).
  2. **Parameter, Metric, and Artifact Logging:**
     - **Parameters:** Model type, hyperparameters (ARIMA order, seasonal order, LSTM hidden dim, layers, dropout, learning rate, epochs, batch size, MC samples), dataset, target column, forecast horizon, split configuration, and feature engineering settings.
     - **Metrics:** Preserved physical target units and logged separate validation (`val_mae`, `val_rmse`, `val_smape`, `val_mape`) and held-out test (`test_mae`, `test_rmse`, etc.) metrics. Held-out test metrics remain strictly isolated from model selection.
     - **Artifacts:** Persisted sanitized run config (`config.json`), evaluation summary (`evaluation_summary.json`), and predictions-versus-actuals datasets (`predictions_validation.csv`, `predictions_test.csv`).
  3. **Healthcare Data Privacy & Security Guardrails:**
     - Created `app/ml/tracking/artifacts.py` featuring recursive `sanitize_dict` scrubbing PHI identifiers (`patient_id`, `subject_id`, `hadm_id`, `stay_id`, `mrn`, `name`, `notes`, `diagnosis`) and security credentials (`jwt_secret_key`, `password`, `token`, `secret`, `api_key`).
     - Strictly enforced: no raw MIMIC-IV patient files or credentials are ever logged or uploaded to MLflow tracking stores.
  4. **Safe Local-Development Architecture & Model Registry Support:**
     - Designed backend tracking around SQLite URI (`sqlite:///backend/ml/mlflow.db`), avoiding deprecated MLflow file-store (`file:./mlruns`) warnings and enabling full MLflow Model Registry support locally without requiring a remote server.
     - Graceful degradation: if tracking URI is unreachable or invalid, the tracker logs a structured warning and operates without crashing or altering forecasting predictions.
  5. **Verification & Testing:**
     - 10 comprehensive tests in `backend/tests/test_ml/test_mlflow_tracking.py` covering: parameter/metric logging, null tracker no-op, factory resolution, PHI/credential sanitization, artifact upload and roundtrip, run failure status tagging, unconnectable backend fallback, model registry capability detection, orchestrator end-to-end integration, and prediction numerical parity with/without tracking.
     - All 10 MLflow tests passed.
     - Full test suite: 130 passed, 10 skipped in 64.28s.
     - `ruff check backend`: All checks passed.
     - Frontend lint (`npm run lint`): 0 warnings, 0 errors.
     - Frontend build (`npm run build`): Built in 2.06s with 0 errors.
---

## 7. Completed Workstream: Milestone 2, Chunk 2.7 (Forecasting API)

* **Status:** Complete & Push-Ready.
* **Scope Delivered:**
  1. **REST Forecasting Endpoints:**
     - `GET /api/v1/forecast/admissions`: Daily admissions forecasting (Hero DMC daily series), horizon 1–30 days. Resolves validation-winning model (`val_mae` from `model_selection_report.json`) by default with optional model override.
     - `GET /api/v1/forecast/icu`: Weekly ICU capacity projections (NHSN HRD `icu_beds_occupied` series), horizon 1–8 weeks. Strictly preserves weekly cadence and physical bed units.
     - `GET /api/v1/forecast/occupancy`: Explicit guardrail returning HTTP 400 Bad Request explaining that occupancy rate forecasting is unsupported (numerator/denominator concurrent census data unavailable in benchmarked datasets), preventing synthetic or ungrounded predictions.
     - `GET /api/v1/forecast/benchmarks`: Filtered model-selection benchmarks, cleanly separating validation and held-out test splits.
     - `GET /api/v1/forecast/runs`: Paginated experiment run history with artifact provenance, UTC timestamps, and pagination metadata.
     - `GET /api/v1/forecast/runs/{run_id}`: Detailed run metadata, target information, metrics, and prediction arrays.
  2. **Layered Architecture & Separation of Concerns:**
     - Thin route handlers in `app/api/v1/endpoints/forecast.py`.
     - Business logic, model resolution, on-demand fallback forecasting via `MLPipelineOrchestrator`, and run indexing encapsulated in `app/services/forecast.py` (`ForecastService`).
     - Strong Pydantic request/response schemas in `app/schemas/forecast.py` wrapped in standard `SuccessResponse[T]`.
     - Matching TypeScript interfaces and `forecastApi` client in `frontend/src/api/forecast.ts` for Chunk 2.8 readiness.
  3. **Security, Privacy & RBAC:**
     - Secured behind JWT authentication and `require_permission("predictions.read")` (ADMIN, OPERATIONS_MANAGER, DOCTOR).
     - Strictly read-only operational isolation: no mutation of live patient, bed, or resource collections.
     - Zero PHI or secret leakage; numerical robustness handles non-finite values (NaN/Inf clamping to 0.0).
  4. **Verification & Testing:**
     - 15 dedicated unit and API tests in `backend/tests/test_api_forecast.py` covering: default winner resolution, baseline override, horizon boundaries, invalid model rejection, weekly ICU cadence, occupancy 400 guardrail, benchmark filtering, run pagination & lookup, 401 unauthenticated & 403 unauthorized rejection, and non-finite value handling.
     - All 15 forecast tests passed.
     - Full test suite: 145 passed, 10 skipped in 62.07s.
     - `ruff check backend`: All checks passed.
     - Frontend lint (`npm run lint`): 0 warnings, 0 errors.
     - Frontend build (`npm run build`): Built in 2.30s with 0 errors.
* **Next Chunk:** Milestone 2, Chunk 2.8 (Forecast Dashboard) — Completed.

---

## 8. Completed Workstream: Milestone 2, Chunk 2.8 (Forecast Dashboard)

* **Status:** Complete & Push-Ready.
* **Scope Delivered:**
  1. **Production Forecasting Workspace (`/forecasts`):**
     - Fully integrated `CapacityForecasts.tsx` connected directly to backend forecasting endpoints (`/api/v1/forecast/admissions`, `/api/v1/forecast/icu`, `/api/v1/forecast/occupancy`, `/api/v1/forecast/benchmarks`, `/api/v1/forecast/runs/{id}`) and What-if simulation engine (`/api/v1/simulations/run`).
     - Replaces design prototypes with production application adhering to design craftsmanship, tokens, brand mark, and responsive hierarchy.
  2. **Daily Admissions & Weekly ICU Cadence Semantics:**
     - **Hero DMC Daily Admissions:** 1D daily cadence, physical unit `admissions`, horizons 1–30d (+7d, +14d, +30d interactive toggles). Clear retrospective aggregate disclaimer.
     - **NHSN HRD Weekly ICU Capacity:** 1W weekly cadence, physical unit `beds`, horizons 1–8w (+1w, +2w, +4w, +8w interactive toggles). Distinct time axis preserving weekly interval integrity.
  3. **Strict Time-Series Integrity & Coordinate-Mapped SVG Chart:**
     - `CapacityForecastChart.tsx` renders real historical observations leading up to forecast origin ($T_0$) with vertical origin boundary line, continuing into model point prediction curve.
     - **Strict Confidence Interval Policy:** Uncertainty bands render only when the selected model genuinely provides valid bounds (e.g. LSTM MC dropout); no artificial multiplier bands (`* 1.015`) are fabricated.
  4. **Occupancy Rate Guardrail View:**
     - Explicit handling of HTTP 400 response from `/api/v1/forecast/occupancy` with an amber warning banner and detailed operational explanation: derived occupancy percentages cannot be manufactured without concurrent population-matched licensed capacity. Includes direct action buttons switching back to valid benchmarks.
  5. **Scenario-Adjusted Forecast Preview:**
     - Allows previewing simulated admission surge trajectories (+15%, +30%) from the Chunk 3.1 What-if simulation engine overlaid as a dashed line against baseline forecasts, with an amber banner distinguishing simulated projections from baseline models without mutating live records.
  6. **Model Provenance & Run Artifact Inspection:**
     - Benchmark leaderboard displaying validation-winning models (`val_mae`), held-out test MAE strictly isolated for post-selection reporting, and run status indicators (`COMPLETED`, `FAILED`, `PENDING`).
     - Clickable run ID triggers full JSON artifact inspector modal querying `/api/v1/forecast/runs/{run_id}`.
  7. **Backend Enhancements & Numerical Robustness:**
     - Added `historical_points: list[PredictionPoint]` to `ForecastResponse` schema and service to supply actual series preceding $T_0$.
     - Corrected non-finite prediction handling: raises `HTTPException(502 Bad Gateway)` if predictions contain NaN or Inf instead of silently replacing with corrupt `0.0`.
  8. **Verification & Testing:**
     - Added backend tests in `test_api_forecast.py` for historical points and 502 non-finite error responses.
     - All 16 forecast API tests passed.
     - Full backend test suite: 146 passed, 10 skipped in 58.83s.
     - `ruff check backend`: 0 errors.
     - Frontend lint (`npm run lint`): 0 warnings, 0 errors.
     - Frontend build (`npm run build`): Built in 2.09s with 0 errors.
* **Next Chunk:** Milestone 3, Chunk 3.2 (Scenario Comparison & Simulation UI) — Completed.

---

## 9. Completed Workstream: Milestone 3, Chunk 3.2 (Scenario Comparison & Simulation UI)

* **Status:** Complete & Push-Ready.
* **Scope Delivered:**
  1. **Production Scenario Comparison Workspace (`/simulations`):**
     - Full interactive analytical workspace (`ScenarioComparison.tsx`) replacing mockups with a dedicated operational scenario runner.
     - Accessible via top-level sidebar navigation (`GitCompare` icon) and via cross-dashboard deep link ("Open in Scenario Workspace") from the Forecast Dashboard (`/forecasts`).
  2. **Three Verified Simulation Archetypes:**
     - **Admission Surge (`ADMISSION_SURGE`):** Models surge percentages ($\pm 100\%$, presets: +15%, +30%) and projection horizon (1–30 days) to evaluate surges and bed deficit intervals.
     - **Bed Capacity Change (`BED_CAPACITY_CHANGE`):** Hypothesizes physical ward expansions or contractions ($\pm 50$ beds, presets: +10, +25, -10 beds) while explicitly isolating hypothetical capacity adjustments from live bed inventory.
     - **Resource Bottleneck (`RESOURCE_BOTTLENECK`):** Evaluates equipment demand ratios (ventilators, infusion pumps, dialysis machines) per occupied bed against current verified inventory limits.
  3. **Multi-Scenario Comparison Matrix:**
     - Orchestrates concurrent and incremental simulation executions against a common operational baseline ($T_0$, horizon, target unit).
     - Side-by-side comparison table reporting: Peak Occupancy %, Peak Bed Deficit, Days in Shortage, Cumulative Unmet Admissions, and Bottleneck Resource.
     - Retains individual scenario results and inputs on rerun, addition, or removal without cross-scenario contamination.
  4. **Dynamic SVG Trajectory & Shortage Chart:**
     - `ScenarioTrajectoryChart.tsx` plots baseline occupancy curve against up to 4 concurrent scenario trajectories with distinct color mapping (`#f59e0b`, `#06b6d4`, `#a855f7`, `#ec4899`).
     - Renders effective capacity threshold line ($C$) and highlights active shortage/deficit intervals where simulated demand exceeds capacity.
     - Interactive coordinate tooltip and legend toggles for individual scenario curve visibility.
  5. **Shortage Interval Breakdown & Operational Implications:**
     - Tabular analysis of contiguous shortage periods: Start Day, End Day, Duration, Peak Deficit, and Affected Resource.
     - Deterministic operational takeaways synthesized strictly from backend outcome fields (no LLM hallucination, no clinical prescriptive claims).
  6. **Run History Drawer & Raw Artifact Inspector:**
     - Slide-over run history drawer listing completed and session-persisted simulation runs with UTC timestamps and scenario parameters.
     - Clickable run ID opens raw JSON modal to inspect genuine backend simulation responses (`outcome`, `projections`, `shortage_periods`).
  7. **Backend Resilience & Session Persistence:**
     - Updated `init_db` in `backend/app/database/client.py` to reset `_database = None` upon connection failure, eliminating 5-second socket stalls during local development when MongoDB is offline.
     - Enhanced `SimulationService` with in-memory session persistence (`_session_runs`) ensuring instant fallback, run history tracking, and retrieval across requests.
  8. **Verification & Testing:**
     - 7/7 backend simulation tests in `backend/tests/test_simulation.py` passed in 7.57s.
     - Full backend test suite: 146 passed, 10 skipped.
     - `ruff check backend`: 0 errors.
     - Frontend lint (`npm run lint`): 0 warnings, 0 errors.
     - Frontend build (`npm run build`): Built in 2.04s with 0 errors.
* **Next Chunk:** Milestone 3, Chunk 3.3 (Resource Optimization Engine MIP) — Completed.

---

## 10. Completed Workstream: Milestone 3, Chunk 3.3 (Resource Optimization Engine MIP)

* **Status:** Complete & Push-Ready.
* **Roadmap Reconciliation:**
  - Reconciles the former Milestone 4, Chunk 4.1 MIP planning reference into Milestone 3 as Chunk 3.3 (Decision Intelligence suite), enabling seamless synergy with Chunk 3.1 simulation and Chunk 3.2 scenario modeling.
* **Scope Delivered:**
  1. **Mathematically Grounded MILP Formulation:**
     - Decision variables: Department surge bed activation ($x_{d,t}^{\text{surge}} \in \mathbb{Z}_{\ge 0}$), bed shortages ($s_{d,t}^{\text{bed}} \ge 0$), movable equipment assignments ($y_{r,d,t} \in \mathbb{Z}_{\ge 0}$), equipment deficits ($s_{r,d,t}^{\text{equip}} \ge 0$), and transfer churn linearization ($z_{r,d,t}^{\Delta} \ge 0$).
     - Multi-criteria objective minimizing unmet bed demand, equipment deficits, surge bed operational costs, and transfer churn.
     - Hard constraints: Surge bed pool conservation ($\sum_d x_{d,t}^{\text{surge}} \le B^{\text{surge}}$), equipment inventory conservation ($\sum_d y_{r,d,t} \le Q_r^{\text{avail}}$), and linearized demand satisfaction balance.
  2. **Solver Abstraction Layer (`ScipyMilpSolver`):**
     - Powered by the state-of-the-art **HiGHS** linear/MIP solver via `scipy.optimize.milp`.
     - Zero external C-binary dependencies; executes multi-department 30-day horizons in milliseconds.
     - Decoupled solver protocol with timeout handling, feasibility tracking, and MIP gap reporting.
  3. **Independent Solution Validation (`SolutionValidator`):**
     - Pre-solve input checking (horizons, non-negativity, dimension consistency).
     - Post-solve verification auditing integrality ($\le 10^{-5}$), non-negativity, and all linear constraints.
     - Automated binding bottleneck discovery (exhausted surge capacity, fully utilized equipment pools).
  4. **Counterfactual Baseline Comparison:**
     - Automatically evaluates status quo baseline ($x^{\text{surge}}=0$, static inventory) on identical demand series.
     - Quantifies exact percentage reduction in shortages, equipment deficits, and net patient-days averted.
  5. **Persistence, API & RBAC:**
     - REST endpoints: `POST /api/v1/optimization/solve`, `GET /api/v1/optimization/baseline`, `GET /api/v1/optimization/runs`, and `GET /api/v1/optimization/runs/{run_id}`.
     - Secured via RBAC permissions: `optimization.run` (ADMIN, OPERATIONS_MANAGER) and `optimization.read` (ADMIN, OPERATIONS_MANAGER, DOCTOR).
     - Dual persistence in MongoDB `optimization_runs` and in-memory session cache for resilience.
  6. **Strict Operational Safety Boundary:**
     - Read-only decision support: never mutates live patient, bed, or resource collections.
  7. **Verification & Testing:**
     - 13 comprehensive unit and API tests in `test_optimization_math.py` and `test_api_optimization.py` covering hand-calculable examples, scarce pool competition, equipment deficit tracking, synthetic violation detection, RBAC, and operational isolation.
     - Full backend test suite: 159 passed, 10 skipped.
     - `ruff check backend`: 0 errors.
* **Next Planned Work:** Milestone 3, Chunk 3.4 (Recommendation Explanation & Optimization Plan Review) — Completed.

---

## 11. Completed Workstream: Milestone 3, Chunk 3.4 (Recommendation Explanation & Optimization Plan Review)

* **Status:** Complete & Push-Ready.
* **Scope Delivered:**
  1. **Deterministic & Evidence-Based Explanation Layer (`backend/app/optimization/explanation.py`):**
     - Developed `OptimizationExplanationGenerator` to translate raw MILP decision vectors and validation outputs into transparent, auditable natural-language explanations.
     - Operates strictly deterministically from verified mathematical results; no remote LLMs, zero hallucination risk, no patient or private hospital data sent externally.
  2. **Multi-Criteria Objective Function Deconstruction:**
     - Deconstructs the four-component penalty objective: Unmet Bed Demand Penalty, Surge Bed Activation Overhead, Equipment Deficit Penalty, and Equipment Transfer Friction.
     - Quantifies physical units, weight multipliers, evaluated component scores, and percentage contributions to total objective value.
     - Clarifies operational penalty incentives (penalty weights discourage shortages/churn rather than representing direct monetary accounting costs).
  3. **Department & Resource Allocation Rationales:**
     - Department-level diagnostics reporting baseline bed capacity, projected demand, surge beds allocated, effective capacity, unmet demand, and assigned movable equipment.
     - Distinguishes observed constraint states from clinical prioritization claims (explains decisions based strictly on configured weights, demand ratios, and pool conservation).
     - Equipment allocation diagnostics auditing available inventory, required equipment, proposed allocations, and remaining deficits.
  4. **Constraint & Bottleneck Diagnostics:**
     - Audits active hard and soft constraints from `SolutionValidator`: surge-bed pool limits ($\sum_d x_{d,t}^{\text{surge}} \le B^{\text{surge}}$), equipment inventory conservation ($\sum_d y_{r,d,t} \le Q_r^{\text{avail}}$), and department-specific capacity ceilings.
     - Reports exact bound limits ($L$), actual solution values ($A$), and remaining slack ($L - A$).
     - Distinguishes `BINDING` constraints (zero slack, fully exhausted capacity) from `SLACK` constraints (surplus reserves remain), providing operational consequence narratives.
  5. **Counterfactual Baseline Comparison:**
     - Side-by-side comparison against the unoptimized status quo baseline ($x^{\text{surge}}=0$, static inventory) under identical demand trajectories and horizon.
     - Calculates net patient-days of shortage averted, peak bed deficit reductions, and percentage improvements with robust zero-baseline handling (`0.0%` when baseline demand does not exceed capacity).
  6. **Solver Diagnostics & Feasibility Handling:**
     - Transparently reports solver status (`OPTIMAL`, `FEASIBLE`, `INFEASIBLE`, `TIME_LIMIT`, `SOLVER_ERROR`).
     - Infeasible problems return diagnostic bottleneck identification from pre-solve and validator checks without inventing fabricated hypothetical plans.
  7. **Optimization Plan Review Workspace (`frontend/src/pages/Operations/OptimizationReview.tsx`):**
     - Production React/TypeScript workspace accessible at `/optimizations` and `/operations/optimization`.
     - Adheres to the HospitalOps dark design system (`#19191b`, `#202024`, `#9ba8ff`, Lucide icons).
     - Features:
       - Status badge (`OPTIMAL`, `FEASIBLE`, etc.) and executive rationale banner.
       - KPI summary metric cards (Total Objective Score, Surge Beds Allocated, Averted Shortage Days, Active Binding Bottlenecks).
       - Five tabbed review views:
         1. *Baseline & Objective:* Objective deconstruction bar chart and baseline comparison matrix.
         2. *Department Allocations:* Capacity, surge beds, effective capacity, and unmet demand per department.
         3. *Equipment & Inventory:* Mobilization and allocation tables per resource type.
         4. *Constraints & Bottlenecks:* Binding state pills (`BINDING` vs `SLACK`), limits, values, and slack tolerances.
         5. *Trade-offs & Assumptions:* Detailed operational trade-offs, model limitations, and explicit advisory disclaimer.
       - Interactive "Run Optimizer" modal with custom horizon, surge bed pool, solver timeout, and penalty weight configuration.
       - Slide-over plan history drawer with status pills and timestamps.
       - Raw JSON inspection modal for full solver metadata and explanation verification.
  8. **API & RBAC Security:**
     - `GET /api/v1/optimization/runs/{run_id}/explanation` returning typed `OptimizationExplanationResponse`.
     - Secured via `optimization.read` permission (ADMIN, OPERATIONS_MANAGER, DOCTOR).
     - Unauthenticated requests rejected with 401; unauthorized roles rejected with 403.
     - Aliased `/optimizations` and `/optimization` router paths for plural/singular backwards compatibility.
  9. **Strict Healthcare Safety Invariants:**
     - Operational decision support only; never diagnoses, prescribes, or discharges patients.
     - Advisory recommendations explicitly marked as hypothetical proposals awaiting human operational/clinical sign-off.
     - Strictly read-only against live collections (`beds`, `resources`, `patients`, `admissions`).
  10. **Verification & Testing:**
      - 20 comprehensive unit, math, and API tests in `test_optimization_math.py`, `test_api_optimization.py`, and `test_optimization_explanation.py` passing in ~57s.
      - Full backend test suite passing cleanly.
      - `ruff check backend`: 0 errors.
      - `npm run lint` & `npm run build`: 0 warnings, 0 errors.
* **Next Planned Work:** Milestone 3, Chunk 3.5 (Unified Simulation & Optimization Workspace) — Completed.

---

## 12. Completed Workstream: Milestone 3, Chunk 3.5 (Unified Simulation & Optimization Workspace)

* **Status:** Complete & Push-Ready.
* **Scope Delivered:**
  1. **Unified Decision Cockpit (`frontend/src/pages/Decision/DecisionWorkspace.tsx`):**
     - Mounted at `/decision` and `/decision-workspace`, integrated into sidebar navigation (`Compass` icon).
     - Provides an end-to-end 5-stage analytical progression: Operational Baseline Context ➔ Scenario Simulation Selection ➔ HiGHS Optimization Bridge ➔ 3-Way Cross-Workflow Comparison ➔ Deep-Dive Allocation & Explanation Review.
     - Dark `#111113` / `#161619` craft styling with responsive desktop and mobile support.
  2. **Simulation-to-Optimization Parameter Derivation Adapter:**
     - `prepare_optimization_from_simulation(simulation_id)` automatically derives validated optimization parameters directly from completed what-if simulations.
     - Scales department demands by simulated admission surge percentages (+X%), adjusts available surge pools for bed conversions (+ΔBeds), and configures equipment ratios/inventory deltas for bottleneck scenarios without fabricating synthetic data.
     - Pre-solve review modal allows adjusting surge buffer limits or custom penalty weights prior to execution.
  3. **3-Way Cross-Workflow Comparison Matrix (`DecisionComparison`):**
     - Directly compares Baseline (Status Quo), Unmitigated Simulation, and Optimized Plan on identical time horizons and target units.
     - Compares Peak Bed Deficit, Shortage Duration, Cumulative Unmet Demand, Surge Beds Deployed, and Equipment Shortages.
     - Computes net shortage days eliminated, peak bed deficit reductions (with division-by-zero protection), and equipment fulfillment percentages.
  4. **Decision Provenance & Traceability:**
     - Links optimization plans to originating simulation runs via `origin_simulation_id` and `origin_scenario_name` across schemas, database documents, and API responses.
     - Combined slide-over run history drawer and raw JSON inspection modal for both simulation and optimization artifacts.
  5. **Cross-Page Workflow Integration:**
     - Scenario Comparison (`/simulations`) features "Optimize in Decision Workspace →" deep-link buttons.
     - Optimization Review (`/optimizations`) features origin simulation link badges and direct navigation to the unified cockpit.
  6. **REST API & Security:**
     - `GET /api/v1/optimization/prepare-from-simulation/{simulation_id}` (requires `optimization.run`).
     - `GET /api/v1/optimization/compare-decision/{simulation_id}/{run_id}` (requires `optimization.read`).
     - Aliased under `/api/v1/decision/...`.
  7. **Strict Operational Safety Boundary:**
     - Advisory decision-support proposals only; never applies allocations automatically to live beds or physical equipment.
     - Fully read-only against live collections (`beds`, `resources`, `patients`, `admissions`).
  8. **Verification & Testing:**
     - 8 dedicated integration and API tests in `backend/tests/test_decision_workspace.py` covering parameter derivation, 3-way evaluation, zero-baseline safety, and RBAC permissions.
     - Full Decision Intelligence test suite: 35/35 passed in ~58s.
     - Full backend test suite: 174 passed, 10 skipped.
     - `ruff check backend`: 0 errors.
     - `npm run lint` & `npm run build`: 0 warnings, 0 errors.
* **Next Planned Work:** Milestone 4, Chunk 4.1 (Document Ingestion Pipeline — RAG Knowledge Foundation) — Completed.

---

## 13. Completed Workstream: Milestone 4, Chunk 4.1 (Document Ingestion Pipeline — RAG Knowledge Foundation)

* **Status:** Complete & Push-Ready.
* **Scope Delivered:**
  1. **10-Stage Document Ingestion Pipeline (`backend/app/knowledge/pipeline.py`):**
     - Sequentially executes `DOCUMENT_INPUT` ➔ `FILE_VALIDATION` ➔ `DOCUMENT_EXTRACTION` ➔ `CONTENT_CLEANING` ➔ `METADATA_EXTRACTION` ➔ `DOCUMENT_CHUNKING` ➔ `PRIVACY_VALIDATION` ➔ `EMBEDDING_GENERATION` ➔ `VECTOR_INDEXING` ➔ `COMPLETED`.
     - Sub-millisecond stage duration tracking, status recording, and comprehensive error containment with rollback safety.
  2. **Multi-Format Extraction (`backend/app/knowledge/extractors/`):**
     - PDF extraction with page-level tracking via `pypdf`, detecting scanned empty PDFs lacking text layers (`requires_ocr = True`).
     - DOCX extraction via `python-docx` preserving headings (`#`, `##`, `###`) and formatting tables as Markdown tables (`| col1 | col2 |`).
     - Markdown and plain text extraction with encoding fallbacks (`utf-8`, `latin-1`).
     - HTML extraction via `BeautifulSoup4` stripping scripts/styles/nav/footers and converting tables to Markdown.
  3. **Content Cleaning & Clinical Preservation (`backend/app/knowledge/cleaners.py`):**
     - Unicode NFKC normalization, whitespace cleanup, while strictly preserving medical notations (`SpO2: 98%`, `pH: 7.35-7.45`, `p < 0.05`, `ICU-A`).
  4. **Healthcare Privacy & PHI Quarantine Boundary (`backend/app/knowledge/privacy.py`):**
     - Automatic regex and pattern scanning for Protected Health Information (SSNs, MRNs, phone numbers, patient DOBs) and MIMIC-IV keys (`hadm_id`, `subject_id`, `stay_id`).
     - Documents violating clinical privacy boundaries are quarantined and blocked from vector indexing.
  5. **Structure-Aware Chunking (`backend/app/knowledge/chunkers.py`):**
     - Partitions along structural boundaries (headings, paragraphs, atomic tables) with configurable target tokens (default: 512), max tokens (800), and sliding overlap (64).
     - Generates deterministic chunk IDs (`{doc_id}_v{version}_c{idx}`) with section headings, token counts, and page markers.
  6. **Vector Persistence & Embeddings (`backend/app/knowledge/vectorstore/`, `embedders/`):**
     - Persistent on-disk vector store via **ChromaDB** (`hospitalops_knowledge` collection) with exact metadata filtering and version isolation.
     - Fast deterministic 384-dimensional dense vector embedder (`LocalDeterministicEmbedder`) for offline development/CI, and `SentenceTransformerEmbedder` (`all-MiniLM-L6-v2`).
  7. **Document Versioning & Deduplication (`backend/app/services/knowledge.py`):**
     - SHA-256 content hashing detects exact duplicates (`is_duplicate = True`).
     - Automatic incremental versioning ($v1 \to v2 \dots$) for updated documents with atomic activation and previous version retention.
     - Document reindexing endpoint with custom chunk parameters.
  8. **Hospital Knowledge Base Interface (`frontend/src/pages/Knowledge/KnowledgeBase.tsx`):**
     - Mounted at `/knowledge`, integrated into sidebar navigation (`BookOpen` icon).
     - Features KPI stat cards (documents, chunks, tokens, storage, privacy guard), search & filters, file upload modal (drag-and-drop), chunk inspector drawer, and 10-stage pipeline telemetry drawer.
  9. **REST API & RBAC:**
     - `POST /api/v1/knowledge/documents/upload` (requires `knowledge.manage`).
     - `GET /api/v1/knowledge/documents` (requires `knowledge.read`).
     - `GET /api/v1/knowledge/documents/{id}/chunks` (requires `knowledge.read`).
     - `POST /api/v1/knowledge/documents/{id}/reindex` (requires `knowledge.manage`).
     - `DELETE /api/v1/knowledge/documents/{id}` (requires `knowledge.manage`).
     - `GET /api/v1/knowledge/stats` and `/categories` (requires `knowledge.read`).
  10. **Verification & Testing:**
      - 15 dedicated unit and API tests in `backend/tests/test_knowledge_ingestion.py` covering all extractors, cleaners, privacy scanners, chunking, embeddings, ChromaDB CRUD, pipeline execution, deduplication/versioning, and RBAC.
      - 189 tests in full test suite (179 passed, 10 skipped).
      - `ruff check backend`: 0 errors.
      - `npm run lint` & `npm run build`: 0 warnings, 0 errors.
* **Next Planned Work:** Milestone 4, Chunk 4.2 (Semantic Vector Search & Knowledge Retrieval Engine) — Completed.

---

## 14. Completed Workstream: Milestone 4, Chunk 4.2 (Semantic Vector Search & Knowledge Retrieval Engine)

* **Status:** Complete & Push-Ready.
* **Scope Delivered:**
  1. **Embedding Space Compatibility Verification (`backend/app/knowledge/retrieval/`):**
     - Formulated `embedding_space_id = f"{provider}:{model}:d{dimension}:{metric}"` stored in collection metadata.
     - `KnowledgeRetriever` verifies space identity before executing searches and raises `EmbeddingSpaceMismatchError` on divergence to prevent mathematically invalid cross-model vector distance calculations.
  2. **Query Sanitization & Normalized Encoding (`backend/app/knowledge/retrieval/query_encoder.py`):**
     - Enforces query length limits ($1 \le L \le 500$ chars), rejects whitespace-only queries, checks finite numerical values (`NaN`, `Inf` prevention), and verifies unit L2 vector normalization.
  3. **Server-Side RBAC & Scope Enforcement (`backend/app/knowledge/retrieval/filters.py`):**
     - Derives authorized access levels directly from user JWT claims:
       - `Role.ADMIN`: All access classifications (`PUBLIC`, `INTERNAL`, `RESTRICTED`, `CONFIDENTIAL`).
       - `Role.OPERATIONS_MANAGER`: Operational access (`PUBLIC`, `INTERNAL`, `RESTRICTED`).
       - `Role.DOCTOR`: Standard staff access (`PUBLIC`, `INTERNAL`).
     - Rejects unauthorized client-requested access tiers server-side. Enforces department scoping and compound `$and` filters.
  4. **Repository Post-Validation:**
     - Cross-references candidate chunks against the persistent MongoDB document repository to guarantee only active, non-quarantined documents are surfaced.
  5. **Normalized Provenance & Diversity Ranking (`backend/app/knowledge/retrieval/ranking.py`):**
     - Converts cosine distance $d \in [0, 2]$ to normalized similarity score $s = \max(0.0, \min(1.0, 1.0 - d))$.
     - Implements diversity capping (`max_chunks_per_doc = 3`), min-similarity filtering, and sentence-bounded excerpt extraction.
     - Provides complete provenance: rank position, similarity percentage, cosine distance, document title, active version, section heading, and page marker.
  6. **Retrieval Quality Evaluation Benchmark:**
     - Evaluated across operational policy documents (ED Surge Protocol, Ventilator SOP, Infection Prevention Guidelines): **MRR = 1.0**, **Precision@1 = 1.0**, **Recall@3 = 1.0**.
  7. **Interactive Semantic Search Workbench (`frontend/src/pages/Knowledge/KnowledgeBase.tsx`):**
     - Added dedicated "Semantic Search Engine" tab with natural-language query input, sample prompt shortcuts, Top-K selector, similarity threshold selector, latency/vector-space telemetry pills, and expandable chunk cards with links to the Chunk Inspector and Document Detail drawers.
  8. **REST Endpoints & Security:**
     - `POST /api/v1/knowledge/search` (requires `knowledge.read`).
     - `GET /api/v1/knowledge/search/health` (requires `knowledge.read`).
     - Privacy guard: user query texts are never logged in plaintext server logs.
  9. **Verification & Testing:**
     - 13 dedicated unit, integration, and API tests in `backend/tests/test_knowledge_retrieval.py`.
     - 28 knowledge subsystem tests passing (13 retrieval + 15 ingestion).
     - Full regression test suite: 202 passed, 10 skipped, 0 failures.
     - `ruff check backend`: 0 errors.
     - `npm run lint` & `npm run build`: 0 warnings, 0 errors.
* **Next Planned Work:** Milestone 4, Chunk 4.3 (Retrieval API — RAG Context Retrieval & Assembly Layer) — Completed.

---

## 15. Completed Workstream: Milestone 4, Chunk 4.3 (Retrieval API — RAG Context Retrieval & Assembly Layer)

* **Status:** Complete & Push-Ready.
* **Scope Delivered:**
  1. **Strict Context Token Budgeting (`backend/app/knowledge/retrieval/token_budget.py`):**
     - Enforces configured token ceilings (`max_context_tokens`, 200–16,000 tokens).
     - Accurate offline token counting via `tiktoken` (`cl100k_base`) with conservative word-ratio fallback (`~1.33` tokens/word).
     - Tracks content tokens and reserves overhead for citation headers and boundary enclosures.
     - Automatically records an audit trail of skipped candidate chunks (`SkippedChunkInfo`) with reasons (`token_budget_exceeded`).
  2. **Deterministic Source Citation Mapping (`backend/app/knowledge/retrieval/citation_builder.py`):**
     - Generates sequential, stable citation identifiers (`S1`, `S2`) and bracketed markers (`[S1]`, `[S2]`).
     - Constructs traceable source reference strings incorporating document title, active version, section heading, and page number.
     - Estimates exact token overhead for headers and boundary wrappers.
  3. **Prompt Injection Defense & Context Ordering (`backend/app/knowledge/retrieval/context_builder.py`):**
     - Wraps retrieved material inside `<reference_content>` boundary tags, neutralizing injection attempts (`</reference_content>` $\to$ `&lt;/reference_content&gt;`).
     - Prepends an authoritative operational boundary header that explicitly declares retrieved content as reference data, preventing prompt escaping.
     - Supports three ordering strategies:
       - `RELEVANCE`: Highest semantic similarity first.
       - `DOCUMENT_ORDER`: Grouped by document and sorted sequentially by `chunk_index` to maintain procedural flow.
       - `GROUPED_BY_DOC`: Grouped by document prioritizing highest peak similarity.
  4. **Retrieval Orchestration & Sufficiency Classification (`backend/app/knowledge/retrieval/orchestrator.py`):**
     - Expands initial candidate search ($k_{\text{cand}} = \max(\text{top\_k} \times 3, 15)$) before token budgeting.
     - Evaluates grounding against calibrated similarity thresholds ($s \ge 0.10$).
     - Categorizes execution status into explicit operational contracts: `SUCCESS`, `PARTIAL_CONTEXT`, `INSUFFICIENT_CONTEXT`, `NO_RESULTS`, `FAILED`.
  5. **Interactive RAG Context Workbench (`frontend/src/pages/Knowledge/KnowledgeBase.tsx`):**
     - Added dedicated "RAG Context Assembler" tab to the Knowledge Base interface.
     - Real-time token budget utilization meter (content vs. overhead breakdown) and progress bar.
     - View switchers: Context Blocks, Source Citations table, Prompt-Safe Formatted Context (with one-click copy), and Excluded Chunks audit table.
     - Controls for Top-K, Token Budget (500–8,000), Context Ordering, and Min Relevance Threshold.
  6. **REST API Endpoint & Security:**
     - `POST /api/v1/knowledge/retrieve` (requires `knowledge.read`).
     - Request validation: query length ($1 \le L \le 500$), budget bounds ($200 \le \text{tokens} \le 16,000$), top_k ($1 \le K \le 50$).
     - Server-side RBAC scoping (ADMIN, OPERATIONS_MANAGER, DOCTOR).
     - Inquiry privacy: queries are never logged in plaintext.
  7. **Verification & Testing:**
     - 12 dedicated unit, integration, and API tests in `backend/tests/test_knowledge_retrieval_context.py`.
     - 40 knowledge subsystem tests passing (12 context retrieval + 13 semantic search + 15 ingestion).
     - Full regression test suite: 214 passed, 10 skipped, 0 failures.
     - `ruff check backend`: 0 errors.
     - `npm run lint` & `npm run build`: 0 warnings, 0 errors.
* **Next Planned Work:** Milestone 4, Chunk 4.4 (RAG Answer Generation — Grounded Operational QA) — Completed.

---

## 16. Completed Workstream: Milestone 4, Chunk 4.4 (RAG Answer Generation — Grounded Operational Question Answering)

* **Status:** Complete & Push-Ready.
* **Scope Delivered:**
  1. **Direct In-Memory Retrieval Invocation (`KnowledgeAnswerService`):**
     - Invokes `await self.orchestrator.retrieve_context(...)` directly via Python, avoiding HTTP loopbacks and redundant serialization overhead.
  2. **Strict Healthcare Safety Boundary & Clinical Query Screening:**
     - Regex-based pre-generation classifier `is_clinical_query` screens questions for diagnostic, prescriptive, and medication dosage inquiries.
     - Clinical inquiries are immediately rejected with `AnswerType.OUT_OF_SCOPE` and an authoritative non-clinical advisory notice, preserving the non-negotiable boundary from `AGENTS.md`.
  3. **Adversarial Boundary Tag Enclosure (`PromptBuilder`):**
     - Assembles context inside `<reference_content>` boundary tags with XML escaping (`</reference_content>` $\to$ `&lt;/reference_content&gt;`) to defend against prompt injection.
     - Injects strict operational system instructions demanding structured JSON output with citation markers (`[S1]`, `[S2]`) and explicit abstention directives.
  4. **Deterministic Citation Validation & 1-Shot Retry (`CitationValidator`, `GroundedAnswerGenerator`):**
     - Audits answer text to verify that every citation marker exists in the retrieved context.
     - Automatically triggers a bounded 1-shot correction retry if hallucinated markers (e.g. `[S99]`) are returned.
     - Strips ungrounded markers deterministically if correction retry fails.
  5. **Pluggable LLM Provider Architecture (`LLMProvider`):**
     - `MockLLMProvider`: Deterministic offline synthesis for test suites and offline local environments.
     - `OpenAICompatibleProvider`: Async HTTP provider supporting OpenAI, vLLM, Ollama, and local OpenAI-compatible endpoints with configurable timeouts.
     - `NullLLMProvider`: Safe no-op fallback when RAG generation is toggled off (`rag_generation_enabled = False`).
  6. **Interactive RAG Answer Assistant Workspace (`frontend/src/pages/Knowledge/KnowledgeBase.tsx`):**
     - Added 4th navigation tab "RAG Answer Assistant" with operational sample query shortcuts.
     - Clickable citation pills `[S1]`, `[S2]` that scroll to and highlight corresponding source chunks.
     - Split evidence panel ("Cited in Answer" vs "All Retrieved Chunks") and telemetry footer displaying model, provider, latency, and tokens.
  7. **REST Endpoints & RBAC Security:**
     - `POST /api/v1/knowledge/answer` (requires `knowledge.read`).
     - `GET /api/v1/knowledge/answer/health` (requires `knowledge.read`).
     - Privacy guard: user question text is never logged in plaintext server logs.
  8. **Verification & Testing:**
     - 15 dedicated unit, integration, and API tests in `backend/tests/test_knowledge_answer.py`.
     - 55 knowledge subsystem tests passing (15 answer generation + 12 context retrieval + 13 semantic search + 15 ingestion).
     - Full regression test suite: 229 passed, 10 skipped, 0 failures.
     - `ruff check backend`: 0 errors.
     - `npm run lint` & `npm run build`: 0 warnings, 0 errors.
* **Next Planned Work:** Milestone 4, Chunk 4.5 (RAG UI — Dedicated Hospital Knowledge Assistant Workspace) — Completed.

---

## 17. Completed Workstream: Milestone 4, Chunk 4.5 (RAG UI — Dedicated Hospital Knowledge Assistant Workspace)

* **Status:** Complete & Push-Ready.
* **Scope Delivered:**
  1. **Dedicated Workspace Architecture & Routing:**
     - Registered `/knowledge/assistant` (primary) and `/knowledge-assistant` (alias) in `App.tsx`.
     - Integrated `Knowledge assistant` into the main navigation `Sidebar.tsx` with a `Bot` icon.
     - Added direct launcher banner from Tab 4 of `KnowledgeBase.tsx` to launch the dedicated workspace.
     - Supported URL search query parameter `?q=...` for seamless cross-module deep-linking.
  2. **Live Readiness & Diagnostic Header (`AssistantHeader`):**
     - Live subsystem health query to `GET /api/v1/knowledge/answer/health` displaying active LLM provider, underlying model, and indexed knowledge chunks.
     - Visible non-clinical operational advisory banner: *"Operational Decision Support Only — Not for clinical diagnosis or direct patient management"*.
     - Session query count badge and toggle button for the in-memory history drawer.
  3. **Multi-line Question Composer & Operational Suggestions (`QuestionComposer`, `SuggestedQuestions`):**
     - Auto-resizing textarea with 500-character boundary counter, keyboard triggers (`Enter` to submit, `Shift+Enter` for newline), clear button, and input retention on error.
     - Curated operational suggested queries across four operational domains: Bed Allocation, Surge Protocols, Equipment Maintenance, and Regulatory Compliance.
  4. **Collapsible Advanced Search Settings (`AdvancedSearchSettings`):**
     - Accordion drawer with one-click "Reset to Defaults".
     - Controls for `Top-K` (1–20), `Token Budget` (500–8,000), `Max Sources` (1–10), `Category Scope`, `Access Level Scope`, `Temperature` (0.0–1.0), and `Require Citations`.
     - Strict RBAC: no simulated role elevation controls in the UI.
  5. **Safe Markdown Rendering with Embedded Citations (`SafeMarkdownAnswer`):**
     - Custom, XSS-free React node parser operating without `dangerouslySetInnerHTML`.
     - Renders headings, bold text, code blocks, bullet/numbered lists, and tables.
     - Dynamically compiles bracketed citation markers `[S#]` into interactive `<CitationPill>` elements.
  6. **Interactive Dual-Tier Citation Evidence Inspector (`CitationEvidencePanel`):**
     - Dual-tab view: "Cited in Answer" vs. "All Retrieved Candidates".
     - Smooth scroll and highlight synchronization when clicking `[S#]` citation pills.
     - Quick filter pill (`[S1] ✕`) to isolate specific sources.
     - Expandable excerpt toggle displaying exact source text passages populated from `CitationReference.excerpt`.
  7. **Generation Metadata & Diagnostics Drawer (`GenerationMetadataPanel`):**
     - Expandable telemetry inspector detailing model identifier, provider type, prompt version, latency breakdown (retrieval vs. LLM generation), token usage (context vs. completion), and citation validation counts.
  8. **In-Memory Tab-Local Session History Drawer (`SessionHistoryDrawer`):**
     - Ephemeral session history stored strictly in React component state (holds up to 25 inquiries).
     - Zero `localStorage` or `sessionStorage` footprint, preventing sensitive facility query leakage on shared hospital terminals.
     - 1-click restore to reload past questions and answers.
  9. **Backend Contract Alignment (`contracts.py`, `citation_validator.py`):**
     - Added `excerpt: str | None = Field(default=None)` to `CitationReference`.
     - `CitationValidator` automatically populates the excerpt string from retrieved context blocks for both verified citations and candidates.
  10. **Verification & Testing:**
      - 15/15 answer generation tests passing in `backend/tests/test_knowledge_answer.py`.
      - Full backend test suite: 229 passed, 10 skipped, 0 failures.
      - `ruff check backend`: 0 errors.
      - `npm run lint` (frontend): 0 warnings, 0 errors.
      - `npm run build` (frontend): Built cleanly in 4.82s.
* **Next Planned Work:** Milestone 5, Chunk 5.1 (First Agent: Hospital Operations Analyst Agent) — Completed.

---

## 18. Completed Workstream: Milestone 5, Chunk 5.1 (First Agent: Hospital Operations Analyst Agent)

* **Status:** Complete & Push-Ready.
* **Scope Delivered:**
  1. **Agent ID, Role, and Responsibility:**
     - Agent ID: `hospital_operations_analyst`.
     - Agent Name: Hospital Operations Analyst Agent.
     - Role: Operational Decision Intelligence Assistant.
     - Responsibility: Investigate hospital capacity questions, policies, surge simulations, and resource optimization plans across multiple operational subsystems and synthesize evidence-grounded answers.
  2. **Bounded Execution Lifecycle & State Machine (`AgentRuntime`):**
     - Enforces an explicit finite state progression:
       $\text{RECEIVED} \to \text{VALIDATING} \to \text{SCOPE\_CHECK} \to \text{PLANNING} \to \text{EXECUTING\_TOOLS} \to \text{EVALUATING\_RESULTS} \to \text{GENERATING\_FINAL\_RESPONSE} \to \text{COMPLETED}$.
     - Clamped execution bounds: default `max_steps=5` (max 10), `max_tool_calls=5` (max 10), `timeout_seconds=30` (max 60).
     - Deterministic typed `StopReason` termination codes: `SUFFICIENT_EVIDENCE`, `FINAL_ANSWER_READY`, `OUT_OF_SCOPE`, `NO_RELEVANT_TOOLS`, `MAX_STEPS_REACHED`, `MAX_TOOL_CALLS_REACHED`, `TIMEOUT`, `PROVIDER_UNAVAILABLE`, `TOOL_FAILURE`.
  3. **Typed Tool Registry with 5 Read-Only Subsystem Tools (`backend/app/agents/tools/`):**
     - `search_hospital_knowledge`: Reuses semantic vector search (`KnowledgeService.search`) for policy excerpts and administrative SOPs.
     - `answer_from_hospital_knowledge`: Reuses grounded in-memory RAG question answering (`KnowledgeService.generate_answer`).
     - `get_existing_forecast`: Accesses verified Hero DMC daily admissions or NHSN HRD weekly ICU occupancy projections (`ForecastService`).
     - `get_simulation_result`: Inspects what-if Monte Carlo simulation outcomes, shortage days, and bed/resource deficits (`SimulationService`).
     - `get_optimization_explanation`: Explains MILP solver plans, surge allocations, binding constraints, and trade-offs (`OptimizationService`).
     - Strict Read-Only Guarantee: Zero tool mutations to live bed, patient, admission, or equipment records.
  4. **Policy & Safety Enforcement Layer (`AgentPolicyEnforcer`):**
     - **Clinical Scope Guard:** Pre-generation keyword and intent classifier immediately rejects diagnostic and prescribing queries (`OUT_OF_SCOPE`) before any tool execution, strictly preserving `AGENTS.md` boundaries.
     - **Server-Side RBAC Enforcement:** Each tool enforces required user permissions (`knowledge.read`, `predictions.read`, `simulation.read`, `optimization.read`). Unprivileged callers are rejected with explicit denial reasons.
     - **Duplicate Call & Loop Prevention:** Identical tool calls with identical arguments are detected and blocked.
     - **Output Clamping & Tag Encapsulation:** Raw tool outputs are clamped to 3,500 characters and enclosed in safe `<tool_output>` tags.
  5. **Pluggable Agent Planner (`AgentPlanner`):**
     - Uses `LLMProvider` abstraction (`MockLLMProvider` for deterministic testing/offline and `OpenAICompatibleProvider` for live production model execution).
     - Multi-step structured JSON decision output: `{"action": "CALL_TOOL", ...}` or `{"action": "FINAL_ANSWER", ...}`.
  6. **REST API Endpoints (`/api/v1/agents`):**
     - `POST /api/v1/agents/run` (requires `agents.run`).
     - `GET /api/v1/agents/health` (requires `agents.read`).
     - `GET /api/v1/agents` (requires `agents.read`).
     - `GET /api/v1/agents/{agent_id}` (requires `agents.read`).
     - Updated role permissions in `security.py`: `agents.read` and `agents.run` granted to `ADMIN`, `OPERATIONS_MANAGER`, and `DOCTOR`.
  7. **Frontend Agent Workbench (`/agents`):**
     - `AgentHeader`: Telemetry badge from `GET /api/v1/agents/health`, active model indicator, registered tools count, and healthcare advisory disclaimer.
     - `AgentTaskComposer`: Multi-line task textarea with auto-resize, 1,000-character counter, suggested task quick-picks, collapsible execution controls (`max_steps`, `max_tool_calls`, `timeout_seconds`).
     - `AgentExecutionTimeline`: Visual step-by-step trace viewer with duration badges, status indicators, and expandable arguments/output accordions.
     - `AgentAnswerPanel`: Synthesized response rendered via XSS-safe markdown with interactive citation pills, limitations list, and human review alert.
     - `AgentProvenanceCards`: Categorized source cards grouped by Knowledge Documents, Demand Forecasts, What-if Simulations, and Optimization Plans.
     - `AgentEmptyState`: 4-pillar overview cockpit shown on initial launch.
  8. **Architecture Decision Record:**
     - Created `docs/decisions/ADR-013-first-hospital-operations-analyst-agent.md`.
  9. **Verification & Testing:**
     - 16 dedicated unit, integration, and security tests in `backend/tests/test_agents.py`.
     - Full backend regression suite: 245 passed, 10 skipped, 0 failures.
     - `python -m ruff check backend`: 0 errors.
     - `npm --prefix frontend run lint`: 0 errors, 0 warnings.
     - `npm --prefix frontend run build`: Production build passes cleanly in 5.40s.
* **Next Planned Work:** Milestone 5, Chunk 5.2 (Tool Schemas & Standardized Tool Contracts) — Completed.

---

## 19. Completed Workstream: Milestone 5, Chunk 5.2 (Tool Schemas & Standardized Tool Contracts)

* **Status:** Complete & Push-Ready.
* **Scope Delivered:**
  1. **Dual Pydantic Contract Architecture (`app.agents.contracts` & `app.agents.tools.base`):**
     - Overhauled `AgentTool` base class with mandatory `input_schema: type[BaseModel]` and `output_schema: type[BaseModel]`.
     - Standardized taxonomy: `ToolCategory` (KNOWLEDGE, FORECASTING, SIMULATION, OPTIMIZATION, OPERATIONS, SYSTEM), `ExecutionType` (READ_ONLY, WRITE), and `ToolErrorCode` (UNKNOWN_TOOL, INVALID_INPUT, UNSUPPORTED_SCHEMA_VERSION, PERMISSION_DENIED, TOOL_DISABLED, APPROVAL_REQUIRED, OUTPUT_VALIDATION_FAILED, EXECUTION_TIMEOUT, EXECUTION_FAILED, OUTPUT_LIMIT_EXCEEDED).
     - Standard semver tracking (`schema_version: str = "1.0.0"`) and semver compatibility checking (`is_compatible_semver`).
  2. **Deterministic Schema Generation & OpenAI Export:**
     - Deterministic standard JSON Schema (Draft 2020-12) generated via Pydantic v2 `model_json_schema()`.
     - OpenAI function calling format export: `{"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}`.
  3. **Dual-Stage Execution & Boundary Validation (`execute_with_validation`):**
     - Pre-execution input validation catches invalid or missing parameters, raising `ToolExecutionError(ToolErrorCode.INVALID_INPUT)`.
     - Post-execution output validation guarantees service responses conform to `output_schema`, raising `ToolExecutionError(ToolErrorCode.OUTPUT_VALIDATION_FAILED)` upon failure.
     - Centralized error mapping and structured `ToolResult` tracking execution status, schema version, duration, and error codes.
  4. **Domain Tool Contracts Updated:**
     - `search_hospital_knowledge`: Input `SearchHospitalKnowledgeInput`, Output `SearchHospitalKnowledgeOutput`.
     - `answer_from_hospital_knowledge`: Input `AnswerFromHospitalKnowledgeInput`, Output `AnswerFromHospitalKnowledgeOutput`.
     - `get_existing_forecast`: Input `GetExistingForecastInput`, Output `GetExistingForecastOutput` (with `ForecastPointOutput`).
     - `get_simulation_result`: Input `GetSimulationResultInput`, Output `GetSimulationResultOutput` (with `SimulationRunSummary`).
     - `get_optimization_explanation`: Input `GetOptimizationExplanationInput`, Output `GetOptimizationExplanationOutput` (with `OptimizationPlanSummary`).
  5. **Permission-Aware Registry & Discovery Boundary:**
     - `ToolRegistry.discover_tools(user_permissions)` strictly filters out unauthorized tools from discovery and inspection.
     - Restrictive RBAC boundaries prevent unprivileged users from probing tool signatures.
  6. **REST API Discovery Endpoints:**
     - `GET /api/v1/agents/tools`: Filter by domain category, tag, or schema inclusion. Unauthorized tools are excluded.
     - `GET /api/v1/agents/tools/{tool_id}`: Inspect tool details and schemas; returns HTTP 403 Forbidden for unauthorized tools and 404 for unknown tools.
  7. **Frontend Tool Schemas & Contracts Inspector (`AgentToolsModal`):**
     - Interactive modal launched from `/agents` header.
     - Domain category filter pills (All, Knowledge, Forecasting, Simulation, Optimization).
     - Search by tool ID, label, or tags.
     - Read-only execution guarantee badge.
     - Dual-tab Schema Inspector: "Input Schema (Arguments)" vs. "Output Schema (Contract)".
     - Structured parameter table (Field, Type, Required/Optional, Description) and syntax-highlighted raw JSON Schema box with one-click copy.
  8. **Architecture Decision Record:**
     - Created `docs/decisions/ADR-014-standardized-agent-tool-schemas.md`.
  9. **Verification & Testing:**
     - 15 new tests in `backend/tests/test_agent_tools.py` covering metadata, schema generation, OpenAI export, input/output validation, registry filtering, semver checks, and REST endpoints.
     - Full backend regression suite: 260 passed, 10 skipped, 0 failures.
     - `python -m ruff check backend`: 0 lint errors.
     - `npm --prefix frontend run lint`: 0 lint errors, 0 warnings.
     - `npm --prefix frontend run build`: Clean production build in 4.54s.
* **Next Planned Work:** Milestone 5, Chunk 5.3 (Agent Orchestration Engine) — Completed.

---

## 20. Completed Workstream: Milestone 5, Chunk 5.3 (Agent Orchestration Engine)

* **Status:** Complete & Push-Ready.
* **Scope Delivered:**
  1. **Lifecycle State Machine:**
     - Implemented `OrchestrationStateTracker` managing transitions across 14 distinct states (`PENDING`, `UNDERSTANDING`, `PLANNING`, `TOOL_SELECTION`, `TOOL_EXECUTION`, `EVIDENCE_REVIEW`, `RESPONSE_GENERATION`, `COMPLETED`, `REJECTED`, `FAILED`, `CANCELLED`, `TIMED_OUT`, `MAX_STEPS_REACHED`, `INSUFFICIENT_EVIDENCE`).
     - Terminal state protection: terminal states cannot be exited; illegal transitions are blocked and logged.
  2. **Structured Task Planning:**
     - `AgentPlanner.understand_and_plan(...)` produces structured `AgentTaskPlan` capturing objective, task type, strategic formulation, required evidence types, candidate tools, and expected outcomes.
     - Supports direct no-tool answering for general inquiries, immediate rejection of non-operational/out-of-scope requests, and clinical safety boundary checks.
  3. **Evidence Collection & Domain Classification:**
     - `AgentEvidenceCollector` gathers structured `AgentEvidence` with category mapping: `OBSERVED_DATA`, `FORECAST`, `SIMULATION`, `OPTIMIZATION`, `KNOWLEDGE_POLICY`.
     - Explicit domain qualifiers: `is_projection`, `is_hypothetical`, `is_recommendation`.
     - Context budgeting clamps output summaries if evidence exceeds `max_chars` budget (default 12,000 characters).
  4. **Safe Tool Execution Coordination:**
     - `ToolExecutionCoordinator` verifies caller RBAC permissions against `required_permission` before invocation.
     - Prevents duplicate tool loops by blocking consecutive identical invocations with identical arguments.
     - Enforces per-tool execution timeouts and pre/post Pydantic schema validation.
  5. **Grounded Response Generation & Citation Verification:**
     - `AgentResponseGenerator` synthesizes evidence-backed answers.
     - Citation verification strictly verifies `CitationReference` IDs against ingested sources, rejecting hallucinated markers.
     - Enforces operational disclaimers and domain-specific caveats.
  6. **Trace Auditing & API Endpoints:**
     - Preserves immutable execution history via `AgentExecutionTrace` in `_TRACE_STORE`.
     - `POST /api/v1/agents/execute`: Executes operational inquiries through the bounded orchestration engine.
     - `GET /api/v1/agents/traces/{execution_id}`: Retrieves complete step-by-step state transitions, tool invocations, and timing telemetry.
  7. **Frontend Workbench Enhancements:**
     - `AgentTaskPlanPanel`: Visualizes strategic plan, objective, and candidate tools.
     - `AgentExecutionTimeline`: Renders an interactive state transition pill trail with hover reasons and step durations.
     - `AgentProvenanceCards`: Visualizes ingested operational evidence with domain badges (`Projection`, `Hypothetical`, `Advisory Proposal`).
     - Wired `AgentWorkbench` to `executeAgent(...)` endpoint.
  8. **Architecture Decision Record:**
     - Created `docs/decisions/ADR-015-agent-orchestration-engine.md`.
  9. **Verification & Testing:**
     - 17 new tests in `backend/tests/test_agent_orchestrator.py` covering state transitions, planning, tool coordination, loop blocking, timeouts, evidence collection, citation verification, and REST endpoints.
     - Full backend regression suite: 277 passed, 10 skipped, 0 failures.
     - `python -m ruff check backend`: 0 lint errors.
     - `npm --prefix frontend run lint`: 0 lint errors, 0 warnings.
     - `npm --prefix frontend run build`: Clean production build in 5.86s.
* **Next Planned Work:** Milestone 5, Chunk 5.4 (Agent State Management & Conversation Continuity) — Completed.

---

## 21. Completed Workstream: Milestone 5, Chunk 5.4 (Agent State Management & Conversation Continuity)

* **Status:** Complete & Push-Ready.
* **Scope Delivered:**
  1. **Persistent Session & Message Persistence:**
     - Created MongoDB models and collections `agent_sessions` (`AgentSessionDocument`) and `agent_messages` (`AgentMessageDocument`).
     - Implemented `AgentSessionRepository` and `AgentMessageRepository` with compound indexes for scoped queries: `(user_id, status, last_activity_at DESC)`, `(session_id, created_at ASC)`.
  2. **Bounded Context Reconstruction Engine:**
     - `AgentContextBuilder` reconstructs chronological conversational turns (`AgentConversationTurn`) working backwards from the latest message.
     - Enforces strict character/token budget clamping (`max_context_chars`), safely setting `is_truncated = True` when older turns are omitted.
     - Dynamic RBAC Revalidation: revalidates user permissions (`predictions.read`, `simulation.read`, `optimization.read`, `knowledge.read`) against cached evidence before injecting into prompts.
     - Formats prompt context with clear epistemic headers and disclaimer notices that historical dialogue does not override live operational reality.
  3. **State Management Coordinator:**
     - `AgentStateManager` coordinates session creation, retrieval, updates, status transitions (`ACTIVE`, `ARCHIVED`, `EXPIRED`), and deletion.
     - Enforces strict ownership boundaries (`user_id == current_user.user_id`) ensuring callers cannot inspect or post to others' sessions.
     - Enforces active status guards: rejects execution attempts on archived sessions with HTTP 400 Bad Request.
     - Implements maximum message guardrails (`MAX_MESSAGES_PER_SESSION = 100`).
     - Manages atomic message increments and timestamp updates via `update_activity(...)`.
  4. **Preserved Execution Engine:**
     - The Chunk 5.3 `AgentOrchestrator` remains the sole execution engine; `AgentStateManager` supplies reconstructed context and persists user and assistant turns with structured provenance metadata.
  5. **Canonical 4-Turn Operational Inquiry:**
     - Validated end-to-end multi-turn dialogue:
       - Turn 1: "Show me the latest available ICU forecast."
       - Turn 2: "Now compare it with the previous forecast."
       - Turn 3: "What happens if admissions increase by 15%?"
       - Turn 4: "Summarize the operational implications."
  6. **REST Endpoints (`/api/v1/agents/sessions`):**
     - `POST /api/v1/agents/sessions`: Create persistent conversational thread.
     - `GET /api/v1/agents/sessions`: List caller's sessions with lifecycle status filtering and pagination.
     - `GET /api/v1/agents/sessions/{id}`: Inspect session metadata.
     - `PATCH /api/v1/agents/sessions/{id}`: Modify title or custom tags.
     - `POST /api/v1/agents/sessions/{id}/archive` & `POST /api/v1/agents/sessions/{id}/restore`: Lifecycle transitions.
     - `DELETE /api/v1/agents/sessions/{id}`: Purge conversational messages while preserving execution audit logs.
     - `GET /api/v1/agents/sessions/{id}/messages`: List chronological message history.
     - `POST /api/v1/agents/sessions/{id}/messages`: Submit follow-up inquiry and execute conversational turn.
     - `POST /execute` & `POST /run`: Updated with optional `session_id` to route execution seamlessly through state management.
  7. **Frontend Multi-Turn Workbench Integration:**
     - `AgentSessionSidebar`: Interactive sidebar displaying user sessions, status filter tabs (Active, Archived, All), message counts, relative timestamps, and thread action controls (Archive, Restore, Delete, New Thread).
     - `AgentConversationStream`: Chronological dialogue stream rendering user message bubbles, assistant cards with epistemic badges, formatted markdown answers, and expandable provenance accordions.
     - Suggested Canonical Workflow: One-click quick-start buttons guiding users through the 4-turn operational scenario.
     - Collapsible Diagnostics: Preserved full execution timeline and provenance card inspection for the latest turn.
  8. **Architecture Decision Record:**
     - Created `docs/decisions/ADR-016-agent-state-management-and-conversation-continuity.md`.
  9. **Verification & Testing:**
     - 10 new unit and API tests in `backend/tests/test_agent_sessions.py` covering session CRUD, ownership isolation, status guards, context reconstruction, RBAC revalidation, budget clamping, canonical 4-turn inquiry, and REST endpoints.
     - 58/58 agent tests passed (`test_agents.py`, `test_agent_tools.py`, `test_agent_orchestrator.py`, `test_agent_sessions.py`).
     - Full backend regression suite: 287 passed, 10 skipped, 0 failures.
     - `python -m ruff check backend`: 0 lint errors.
     - `npm --prefix frontend run lint`: 0 lint errors, 0 warnings.
     - `npm --prefix frontend run build`: Clean production build in 6.67s.
* **Next Planned Work:** Milestone 5, Chunk 5.5 (Agent Memory & Cross-Session Intelligence) — Completed.

---

## 22. Completed Workstream: Milestone 5, Chunk 5.5 (Agent Memory & Cross-Session Intelligence)

* **Status:** Complete & Push-Ready.
* **Scope Delivered:**
  1. **Persistent Memory Persistence & Lifecycles (`agent_memories`):**
     - Implemented `AgentMemoryDocument` capturing `memory_id`, `user_id`, `agent_id`, `category` (`USER_PREFERENCE`, `WORKFLOW_PREFERENCE`, `EXPLICIT_USER_CONTEXT`), `key`, `value`, `summary`, `status` (`PENDING_APPROVAL`, `ACTIVE`, `SUPERSEDED`, `EXPIRED`, `REJECTED`, `DELETED`), provenance IDs, timestamps, and concurrency version.
     - MongoDB compound indexes: `(memory_id)`, `(user_id, status, category)`, `(user_id, status, last_used_at DESC)`, `(user_id, agent_id, key)`, `(expires_at)`.
     - `AgentMemoryRepository` with strict user ownership scoping and atomic status transitions.
  2. **Deterministic Safety Policy Boundary (`AgentMemoryPolicy`):**
     - Enforces zero PHI/patient-level identifiers (`scan_privacy_and_access`: SSN, MRN, MIMIC hadm/subject/stay IDs, phone, DOB).
     - Enforces non-clinical operational boundary (`is_clinical_query`: rejects diagnosis, medication prescriptions, drug dosages, intubation, treatment regimens).
     - Credential/secret scanning (Bearer tokens, JWTs, API keys, passwords).
     - Anti-injection scanning (ignore previous instructions, developer mode, system prompt spoofing).
     - Privilege escalation scanning (role is admin, bypass rbac, elevate permission).
     - Sizing bounds (key: 2-100 chars, value: 2-2000 chars, summary: 2-500 chars).
  3. **Memory Extraction Engine (`AgentMemoryExtractor`):**
     - Recognizes preference cues ("remember that I prefer...", "always include...", "for future reports...", "in our hospital, our standard...") via compiled regex heuristics and optional structured LLM extraction.
     - Rejects unsafe phrases and standard operational inquiries (zero hallucinated candidates).
  4. **Memory Service & Lifecycle Management (`AgentMemoryService`):**
     - Explicit consent workflow: candidates are created in `PENDING_APPROVAL`.
     - Approval re-validates safety policies, detects conflicting active keys, supersedes older active versions, and sets status to `ACTIVE`.
     - Rejection and soft-deletion transitions (`REJECTED`, `DELETED`).
     - Bounded retrieval (`max_memories=5`, `max_chars=1500`) with keyword relevance scoring and recency prioritization. Asynchronously updates `last_used_at`.
     - Non-blocking post-response extraction hook in `AgentStateManager.execute_in_session`.
  5. **Context Builder & Prompt Integration:**
     - `AgentContextBuilder` injects retrieved approved memories into `AgentConversationContext`.
     - Formats prompt section `### Approved User Preferences & Operational Context` with clear warnings that stored preferences represent reporting conventions and never override live operational data.
  6. **REST API Endpoints (`/api/v1/agents/memories`):**
     - `GET /api/v1/agents/memories/pending`: List pending memory candidates (`agents.read`).
     - `POST /api/v1/agents/memories/candidate`: Manually register a candidate (`agents.run`).
     - `POST /api/v1/agents/memories/{id}/approve`: Approve candidate to `ACTIVE` (`agents.run`).
     - `POST /api/v1/agents/memories/{id}/reject`: Reject candidate (`agents.run`).
     - `GET /api/v1/agents/memories`: List approved active memories with filtering and pagination (`agents.read`).
     - `GET /api/v1/agents/memories/{id}`: Inspect memory details (`agents.read`).
     - `PATCH /api/v1/agents/memories/{id}`: Edit memory content with policy re-validation (`agents.run`).
     - `DELETE /api/v1/agents/memories/{id}`: Soft-delete memory (`agents.run`).
  7. **Frontend Memory & Preferences Workspace:**
     - `AgentMemoryModal.tsx`: Dual-tab modal for reviewing pending candidates with 1-click Approve/Reject, and managing active preferences with inline creation, editing, and deletion.
     - `AgentHeader.tsx`: Added "Memory" button displaying an indicator badge for pending candidates awaiting review.
     - `AgentWorkbench.tsx`: Wired modal state, pending count polling, and automatic refresh on conversational turns.
  8. **Architecture Decision Record:**
     - Created `docs/decisions/ADR-017-agent-memory-and-cross-session-intelligence.md`.
  9. **Verification & Testing:**
     - 24 unit and API tests in `backend/tests/test_agent_memory.py` covering policy validation (PHI, clinical, secrets, injection, RBAC claims), candidate extraction, approval/supersession/rejection/deletion lifecycle, user isolation, bounded retrieval, prompt formatting, and REST API endpoints.
     - 82/82 agent tests passed across all suites (`test_agents.py`, `test_agent_tools.py`, `test_agent_orchestrator.py`, `test_agent_sessions.py`, `test_agent_memory.py`).
     - Full backend regression suite: 311 passed, 10 skipped, 0 failures.
     - `python -m ruff check backend`: 0 lint errors.
     - `npm --prefix frontend run lint`: 0 lint errors, 0 warnings.
     - `npm --prefix frontend run build`: Clean production build in 5.70s.
* **Next Planned Work:** Milestone 5, Chunk 5.6.1 (Multi-Agent Architecture & Contracts) — Completed.

---

## 23. Completed Workstream: Milestone 5, Chunk 5.6.1 (Multi-Agent Architecture & Contracts)

* **Status:** Complete & Push-Ready.
* **Scope Delivered:**
  1. **Supervisor-and-Specialist Architecture Design:**
     - Established hierarchical multi-agent architecture where the Hospital Operations Analyst Agent acts as the sole user-facing supervisor.
     - Four deterministic domain specialists: Forecasting (`forecasting_specialist`), Simulation (`simulation_specialist`), Optimization (`optimization_specialist`), and Knowledge (`knowledge_specialist`).
     - Bounded delegation flow: User Request -> Session Context -> Primary Analyst -> Validated Delegation Plan -> Multi-Agent Coordinator -> Selected Specialists -> Structured Results -> Aggregator -> Final Response.
  2. **Typed Pydantic v2 Multi-Agent Contracts (`backend/app/agents/multi_agent/contracts.py`):**
     - `SpecialistId` & `SpecialistDomain`: Authoritative string enums for deterministic specialist registry.
     - `SpecialistDefinition`: Identity and capability descriptors with RBAC mapping and allowed tool IDs (`extra="forbid"`).
     - `STANDARD_SPECIALISTS`: Static registry definitions for all 4 domain specialists.
     - `DelegationRequest`: Bounded task delegation contract ($5 \le \text{chars} \le 1500$, $1.0 \le t \le 45.0\text{s}$, evidence limits, `extra="forbid"`).
     - `DelegationPlan`: Multi-agent delegation specification enforcing $\le 4$ specialists, unique targets, strict `max_depth = 1` (no recursive agent spawning), total timeout bounds ($5.0 \le t \le 60.0\text{s}$), and DAG dependency validation (`extra="forbid"`).
     - `SpecialistExecutionStatus` & `MultiAgentErrorCode`: Standardized lifecycle and failure classifications.
     - `SpecialistResult`: Domain result contract encapsulating `AgentEvidence`, `ProvenanceItem`, `CitationReference`, epistemic categories, and duration telemetry (`extra="forbid"`).
     - `AggregatedSpecialistResult`: Cross-specialist synthesis contract capturing successful and unsuccessful contributors, detected contradictions, combined evidence, and partial-result resilience without synthetic confidence metrics.
     - `MultiAgentTraceEvent` & `MultiAgentExecutionTrace`: Structured audit contracts omitting raw LLM chain-of-thought to prevent prompt leakage.
  3. **Healthcare Safety & Epistemic Boundaries:**
     - Reused foundational `EvidenceCategory` classifications (`OBSERVED_DATA`, `FORECAST`, `SIMULATION`, `OPTIMIZATION`, `KNOWLEDGE_POLICY`).
     - Strictly prohibited relabeling hypothetical or projected evidence as observed facts.
     - Preserved clinical safety filter (`ClinicalSafetyPolicy`), zero-PHI quarantine, and read-only operational guarantees.
  4. **Architectural Decision Record:**
     - Created `docs/decisions/ADR-018-multi-agent-coordination.md`.
  5. **Verification & Testing:**
     - Created 26 contract-level tests in `backend/tests/test_agent_multi_agent_contracts.py`.
     - Validated specialist coverage, request bounds, depth=1 enforcement, max 4 specialists, duplicate rejection, timeout alignment, dependency checks, failure handling, timestamp sequences, arbitrary confidence score rejection, partial failure tolerance, trace auditing, and roundtrip JSON serialization.
     - All 26 contract tests passed.
     - `python -m ruff check backend`: 0 lint errors.
* **Next Planned Work:** Milestone 5, Chunk 5.6.2 (Specialist Agent Implementations & Registry) — Completed.

---

## 24. Completed Workstream: Milestone 5, Chunk 5.6.2 (Specialist Agent Implementations & Registry)

* **Status:** Complete & Push-Ready.
* **Scope Delivered:**
  1. **Abstract Base Specialist Runtime (`backend/app/agents/multi_agent/specialists/base.py`):**
     - Implemented `BaseSpecialist(ABC)` enforcing:
       - Target specialist identity validation against `request.target_specialist_id`.
       - Enabled state validation (`specialist.enabled`).
       - Server-side RBAC revalidation using `context.permissions` against `required_permissions` (`predictions.read`, `simulation.read`, `optimization.read`, `knowledge.read`).
       - Healthcare safety boundary: `AgentPolicyEnforcer.check_clinical_scope` immediately rejects clinical diagnosis/prescribing inquiries with `MultiAgentErrorCode.POLICY_VIOLATION`.
       - Timeout containment: `asyncio.wait_for` enforcing `request.timeout_seconds` (clamped to 45.0s) and converting `TimeoutError` into `SpecialistExecutionStatus.TIMED_OUT`.
       - Unhandled exception containment: prevents stack trace or credential leaks by returning structured `SpecialistExecutionStatus.FAILED`.
       - Post-execution clamping: truncates `summary` to `request.max_output_chars` and clamps `evidence` to `request.max_evidence_items`.
  2. **Forecasting Specialist (`backend/app/agents/multi_agent/specialists/forecasting.py`):**
     - Reuses `GetExistingForecastTool` (`predictions.read`).
     - Parses daily admissions (Hero DMC) vs weekly ICU bed capacity (NHSN HRD) inquiries and horizons.
     - Preserves genuine prediction intervals (e.g. 95% CI) and explicitly notes when models provide point estimates only; never fabricates intervals or future values.
     - Sets `EvidenceCategory.FORECAST` and `is_projection=True`.
  3. **Simulation Specialist (`backend/app/agents/multi_agent/specialists/simulation.py`):**
     - Reuses `GetSimulationResultTool` (`simulation.read`).
     - Inspects what-if scenarios (admission surges, bed capacity changes, equipment bottlenecks).
     - Explicitly classifies findings as `EvidenceCategory.SIMULATION` with `is_hypothetical=True`.
     - Enforces read-only operational boundary: rejects live database mutation attempts with `POLICY_VIOLATION`.
  4. **Optimization Specialist (`backend/app/agents/multi_agent/specialists/optimization.py`):**
     - Reuses `GetOptimizationExplanationTool` (`optimization.read`).
     - Interprets MILP solver solutions, objective deconstruction, surge bed allocations, and binding capacity bottlenecks.
     - Explicitly classifies findings as `EvidenceCategory.OPTIMIZATION` with `is_recommendation=True`.
     - Rejects automatic application or execution of plans with `POLICY_VIOLATION`.
  5. **Knowledge Specialist (`backend/app/agents/multi_agent/specialists/knowledge.py`):**
     - Reuses `SearchHospitalKnowledgeTool` (`knowledge.read`).
     - Retrieves institutional SOPs, surge guidelines, and operational policies.
     - Formats authoritative bracketed citations (`[S1]`, `[S2]`) with chunk provenance.
     - Rejects patient-level PHI inquiries (SSN, MRN) and clinical queries.
  6. **Deterministic Specialist Registry (`backend/app/agents/multi_agent/registry.py`):**
     - Implemented `SpecialistRegistry` managing the 4 canonical specialists.
     - Rejects unknown or non-enum specialist IDs and prevents duplicate registrations.
     - Guarantees strict canonical deterministic iteration order: `[FORECASTING, SIMULATION, OPTIMIZATION, KNOWLEDGE]`.
     - Provides `get_specialist`, `list_specialists`, `get_definition`, `is_enabled`, `set_enabled`, and `is_fully_registered`.
  7. **Verification & Testing (`backend/tests/test_agent_specialists.py`):**
     - 22 unit tests covering BaseSpecialist (RBAC, clinical filter, timeout, exception containment, output clamping), Forecasting (daily/weekly cadence, point estimates, confidence intervals), Simulation (scenario inspection, read-only mutation block), Optimization (MILP explanation, binding bottlenecks, no auto-apply), Knowledge (semantic search, citations, PHI rejection), and Registry (order, duplicate rejection, enable/disable).
     - 130/130 agent tests passed across all 7 agent suites.
     - Full backend regression suite: 359 passed, 10 skipped, 0 failures (148.72s).
     - `python -m ruff check backend`: 0 lint errors.
* **Next Planned Work:** Milestone 5, Chunk 5.6.3 (Multi-Agent Coordinator Runtime, Concurrency Throttling, and Aggregator Implementation) — Completed.

---

## 25. Completed Workstream: Milestone 5, Chunk 5.6.3 (Multi-Agent Coordinator, Aggregator & Execution Tracking)

* **Status:** Complete & Push-Ready.
* **Scope Delivered:**
  1. **Bounded Multi-Agent Coordinator (`backend/app/agents/multi_agent/coordinator.py`):**
     - Implemented `MultiAgentCoordinator` coordinating `DelegationPlan` execution across registered domain specialists.
     - Enforces maximum delegation depth of 1 (strictly non-recursive, rejecting sub-delegation).
     - Limits maximum specialists to 4 per parent execution.
     - Implements bounded concurrency throttling using `asyncio.Semaphore(max_concurrency)`.
     - Supports dependency resolution via `plan.dependencies`: independent tasks run concurrently; dependent tasks await prerequisites and inherit verified evidence IDs.
     - Implements failure cascading: when a prerequisite specialist fails, dependent specialists are automatically skipped (`SpecialistExecutionStatus.SKIPPED`) with `MultiAgentErrorCode.SPECIALIST_FAILED`.
     - Enforces individual task timeouts (`request.timeout_seconds`) and total coordination wall-clock timeouts (`plan.total_timeout_seconds`), cancelling running tasks and marking uncompleted delegations as `TIMED_OUT`.
     - Handles unregistered (`SPECIALIST_NOT_FOUND`) and disabled (`SPECIALIST_DISABLED`) specialists safely without crashing.
  2. **Domain Evidence Aggregator (`backend/app/agents/multi_agent/aggregator.py`):**
     - Implemented `MultiAgentAggregator` consolidating multiple `SpecialistResult` objects into an `AggregatedSpecialistResult`.
     - Enforces epistemic classification integrity: strictly verifies each specialist's output category (`FORECAST`, `SIMULATION`, `OPTIMIZATION`, `KNOWLEDGE_POLICY`) and prevents projections from ever being mislabeled as `OBSERVED_DATA`.
     - Cross-domain inconsistency and contradiction detection:
       - Occupancy metric divergence: flags significant (>20% or >20 beds) discrepancies between Forecasting and Simulation for overlapping departments.
       - Operational polarity contradictions: flags conflicts when one specialist reports bed/resource shortages while another reports surplus or ample capacity.
       - Policy alignment notices: flags when Knowledge SOP requires reserve capacity while Optimization proposes 100% capacity utilization.
     - Deduplicates evidence artifacts by `evidence_id`, provenance records by `(category, id)`, and citations by `(document_id, chunk_id)`.
     - Resolves aggregation status (`COMPLETED`, `PARTIAL_SUCCESS`, `FAILED`, `NO_RESULTS`) and identifies `successful_contributors` vs `unsuccessful_contributors`.
     - Enforces healthcare safety invariant: `requires_human_review = True` on all aggregated operational recommendations.
  3. **Multi-Agent Execution Tracker & Telemetry (`backend/app/agents/multi_agent/tracer.py`):**
     - Implemented `MultiAgentExecutionTracker` managing in-memory trace lifecycle and audit event emission.
     - Emits chronological trace events (`PARENT_EXECUTION_STARTED`, `DELEGATION_PLAN_CREATED`, `SPECIALIST_STARTED`, `SPECIALIST_COMPLETED`, `SPECIALIST_FAILED`, `SPECIALIST_TIMED_OUT`, `SPECIALIST_CANCELLED`, `SPECIALIST_SKIPPED`, `AGGREGATION_COMPLETED`).
     - Recursively sanitizes event details (`_sanitize_telemetry`), redacting credentials, tokens, passwords, API keys, system prompts, and raw chain-of-thought tokens.
     - Computes wall-clock coordination duration in milliseconds (`total_duration_ms`).
  4. **Agent Trace Repository & Database Indexing (`backend/app/repositories/agent_traces.py`):**
     - Implemented `AgentTraceRepository` managing the `agent_traces` MongoDB collection.
     - Supports `save_trace`, `get_by_trace_id`, `get_by_parent_execution_id`, and `list_user_traces`.
     - Added collection index definitions to `backend/app/database/client.py` (`trace_id` unique, `parent_execution_id`, compound `user_id + created_at DESC`).
  5. **Subsystem Package Exports (`backend/app/agents/multi_agent/__init__.py`):**
     - Exported `MultiAgentCoordinator`, `MultiAgentAggregator`, and `MultiAgentExecutionTracker`.
  6. **Comprehensive Unit & Integration Test Suite (`backend/tests/test_agent_multi_agent_runtime.py`):**
     - 14 tests verifying telemetry scrubbing, trace lifecycle, trace repository persistence, aggregator empty results, full success epistemic preservation, metric contradiction detection, polarity contradiction detection, partial success / total failure handling, coordinator concurrency, dependency resolution & evidence forwarding, prerequisite failure cascading to SKIPPED, unregistered/disabled specialist rejection, plan timeout cancellation, and recursion depth enforcement.
     - All 62 multi-agent tests passing (contracts, specialists, runtime).
     - Full backend regression suite: 373 passed, 10 skipped, 0 failures.
     - `python -m ruff check backend`: 0 lint errors.
* **Next Planned Work:** Milestone 5, Chunk 5.6.4 (Primary Agent Delegation Integration, REST API Endpoints, and Frontend Transparency UI).
