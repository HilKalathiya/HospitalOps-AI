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
| **M3: Decision Intelligence**| **3.1** | **What-if Simulation Engine** | 🟡 **Active** | **Deterministic scenario simulation engine** |
| **M4: Resource Optimization**| 4.1 | Optimization Engine (MIP) | ⬜ Planned | PuLP/OR-Tools constraint solver |
| **M5: Agentic AI & RAG** | 5.1 | Multi-Agent Orchestration & RAG | ⬜ Planned | LangChain tools, vector retrieval |

---

## 4. Current Workstream: Milestone 3, Chunk 3.1 (What-if Simulation Engine)

* **Goal:** Implement a deterministic simulation engine allowing hospital operators to model hypothetical operational shocks without mutating real hospital state.
* **Supported Scenarios:**
  1. `ADMISSION_SURGE`: Evaluates bed and ICU occupancy when admission volumes spike by $X\%$ over a future horizon.
  2. `BED_CAPACITY_CHANGE`: Models the impact of converting standard beds to ICU beds or activating surge capacity.
  3. `RESOURCE_BOTTLENECK`: Identifies equipment (e.g. ventilators, monitors) or staffing constraints during surge conditions.
* **Output Persistence:** Stored in `simulation_runs` collection with metadata, base timestamp, parameters, and projected time-series outcomes.
