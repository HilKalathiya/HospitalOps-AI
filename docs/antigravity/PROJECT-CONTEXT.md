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
| | 2.6 | MLflow Integration | ⬜ Planned | Centralized experiment tracking, model registry |
| | 2.7 | Forecasting API | ⬜ Planned | REST endpoints for inferences & predictions |
| | 2.8 | Forecast Dashboard | ⬜ Planned | Dynamic forecast charts, CI bounds, UI telemetry |
| **M3: Decision Intelligence**| **3.1** | **What-if Simulation Engine** | ✅ Complete | Deterministic engine, 7/7 tests passed, 120 total passed |
| | 3.2 | Simulation UI & Scenario Comparison | ⬜ Planned | Frontend scenario runner, overlay charts |
| **M4: Resource Optimization**| 4.1 | Optimization Engine (MIP) | ⬜ Planned | PuLP/OR-Tools constraint solver |
| **M5: Agentic AI & RAG** | 5.1 | Multi-Agent Orchestration & RAG | ⬜ Planned | LangChain tools, vector retrieval |

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
* **Next Chunk:** Milestone 2, Chunk 2.6 (MLflow Integration) or Milestone 2, Chunk 2.7 (Forecasting API).
