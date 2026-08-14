# HospitalOps AI — Domain Boundaries

> **Document status:** Chunk 0.2 — Architecture & API Contract
> **Last updated:** August 2026

This document defines the **responsibility boundaries** for each domain module in HospitalOps AI.

No domain is implemented yet (except the `health` system endpoint from Chunk 0.1).
This document defines what each domain **owns** so that future chunks can be built without ambiguity.

---

## Domain Overview

```
┌─────────────────────────────────────────────────────────┐
│                    HospitalOps AI Domains                │
│                                                         │
│  identity       patients       admissions               │
│  departments    beds           resources                │
│  predictions    alerts         simulation               │
│  optimization   knowledge      agents        audit      │
└─────────────────────────────────────────────────────────┘
```

---

## Domain Definitions

---

### `identity` *(future)*

**Owns:**
- User accounts for hospital administrators, analysts, and approvers
- Role definitions (Admin, Analyst, Viewer, Approver)
- Authentication state (session tokens, refresh tokens)
- Authorization policies (who can see/do what)

**Does NOT own:**
- Clinical staff credentials or clinical access management
- Patient identity

**API prefix (future):** `/api/v1/auth/`, `/api/v1/users/`

**MongoDB collection (future):** `users`

---

### `patients` *(future)*

**Owns:**
- Operational patient identifiers (anonymous/de-identified where required)
- Current location (ward, bed, department)
- Admission status (admitted, discharged, pending)

**Does NOT own:**
- Diagnoses, medications, clinical notes
- Any clinical record management

> ⚠️ **Healthcare Boundary**: This domain holds only the operational data necessary for
> bed management and resource planning. It must never expand into clinical record territory.

**API prefix (future):** `/api/v1/patients/`

**MongoDB collection (future):** `patients`

---

### `admissions` *(future)*

**Owns:**
- Admission events (patient arrives, assigned to ward/bed)
- Discharge events (patient leaves, bed becomes available)
- Transfer events (patient moves between wards)
- Admission queue state (patients waiting for bed assignment)
- Historical admission records (for ML feature generation)

**Does NOT own:**
- Clinical reason for admission
- Treatment plans

**API prefix (future):** `/api/v1/admissions/`

**MongoDB collection (future):** `admissions`

---

### `departments` *(future)*

**Owns:**
- Department/ward definitions (ICU, General, Emergency, etc.)
- Department capacity configuration (total beds, reserved beds)
- Department operational status
- Staffing level metadata per department

**Does NOT own:**
- Individual patient assignments (owned by `admissions`)
- Bed-level state (owned by `beds`)

**API prefix (future):** `/api/v1/departments/`

**MongoDB collection (future):** `departments`

---

### `beds` *(future)*

**Owns:**
- Individual bed inventory (bed ID, ward, type)
- Current occupancy state (available, occupied, maintenance, reserved)
- Bed status change history

**Does NOT own:**
- Which patient is in the bed (that link lives in `admissions`)
- Ward-level capacity totals (computed from `beds`, owned as a view)

**API prefix (future):** `/api/v1/beds/`

**MongoDB collection (future):** `beds`

---

### `resources` *(future)*

**Owns:**
- Operational resource inventory (ventilators, monitors, portable equipment, etc.)
- Resource availability state (available, in-use, maintenance)
- Resource location (which ward/department)
- Resource usage history

**Does NOT own:**
- Clinical protocols for resource use
- Procurement or financial data

**API prefix (future):** `/api/v1/resources/`

**MongoDB collection (future):** `resources`

---

### `predictions` *(future)*

**Owns:**
- Model-generated forecasts (admission demand, ICU utilization, occupancy)
- Forecast metadata (model name, version, horizon, confidence)
- Surge risk signals
- Historical prediction accuracy records

**Does NOT own:**
- The ML models themselves (owned by the `ml/` layer)
- Optimization recommendations (owned by `optimization`)

**API prefix (future):** `/api/v1/predictions/`

**MongoDB collection (future):** `predictions`

---

### `alerts` *(future)*

**Owns:**
- Operational alert definitions (surge risk threshold, capacity threshold, etc.)
- Active alert instances (triggered, acknowledged, resolved)
- Alert routing configuration (who receives which alerts)

**Does NOT own:**
- Clinical patient alerts (out of scope)
- Notification delivery details (owned by a future notification service)

**API prefix (future):** `/api/v1/alerts/`

**MongoDB collection (future):** `alerts`

---

### `simulation` *(future)*

**Owns:**
- Scenario definitions (what-if parameter sets)
- Scenario execution results (projected outcomes)
- Scenario comparison metadata

**Does NOT own:**
- Actual hospital state (reads from `beds`, `admissions`, `resources` as inputs)
- Optimization recommendations (owned by `optimization`)

**API prefix (future):** `/api/v1/simulations/`

**MongoDB collection (future):** `simulation_runs`

---

### `optimization` *(future)*

**Owns:**
- Optimization requests (resource allocation problems)
- Optimization results (recommendations, allocation plans)
- Constraint definitions
- Recommendation status (PENDING_REVIEW → APPROVED / REJECTED)

**Does NOT own:**
- Simulation scenarios (owned by `simulation`)
- The action execution itself (executed by the relevant domain service after approval)

**API prefix (future):** `/api/v1/optimizations/`

**MongoDB collection (future):** `optimization_runs`

---

### `knowledge` *(future)*

**Owns:**
- Hospital operational documents (policies, procedures, protocols)
- Document metadata (title, version, department, last updated)
- Embedded document chunks for semantic search
- Retrieval query history

**Does NOT own:**
- Clinical guidelines or treatment protocols (out of scope)
- General internet knowledge

**API prefix (future):** `/api/v1/knowledge/`

**MongoDB collection (future):** `knowledge_documents`, `knowledge_chunks`

---

### `agents` *(future)*

**Owns:**
- Agent run requests and results
- Agent conversation state
- Tool execution logs
- Agent memory entries (backed by Redis, persisted summaries to MongoDB)

**Does NOT own:**
- Direct MongoDB queries for hospital data (delegates via typed tools to domain services)
- Calculations (delegates to service layer)

**API prefix (future):** `/api/v1/agents/`

**MongoDB collection (future):** `agent_runs`, `agent_memory`

---

### `audit` *(future)*

**Owns:**
- All consequential system decisions
- Human approval / rejection records
- Agent recommendation lifecycle events
- Configuration changes

**Does NOT own:**
- Application debug logs (those belong in the logging infrastructure)

**Design principle:** The audit log is **append-only**. Records are never deleted or modified.

**API prefix (future):** `/api/v1/audit/`

**MongoDB collection (future):** `audit_log`

---

## Cross-Domain Rules

1. **Domains do not directly query each other's collections.** Cross-domain data needs go through the service layer.
2. **The `agents` domain calls typed tool functions** — it does not read MongoDB collections.
3. **The `audit` domain receives writes from every other domain** for consequential actions.
4. **The `predictions` domain consumes outputs from the ML layer** — it does not train models.
5. **The `optimization` domain consumes outputs from the prediction and simulation domains** as inputs.
6. **Healthcare boundary applies to all domains** — none of them manage clinical records.
