# HospitalOps AI — System Architecture Overview

> **Document status:** Chunk 0.2 — Architecture & API Contract
> **Last updated:** August 2026

---

## Implementation Status Key

```
✅ CURRENTLY IMPLEMENTED   — code exists and is running
📐 DEFINED THIS CHUNK      — contract / boundary defined; code not yet written
⬜ PLANNED / FUTURE        — not yet defined or implemented
```

---

## Full System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        React Frontend  ✅                               │
│              Dashboard / Operations / AI Copilot / UI                  │
│         React 18 · TypeScript · Vite · Tailwind CSS                    │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │ HTTP REST  (WebSocket ⬜)
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       FastAPI API Layer  ✅                              │
│  Routing · Request validation · Response serialization                  │
│  CORS · API versioning · Error envelopes                                │
│  Auth hooks ⬜ · Request-ID propagation 📐                              │
│                                                                         │
│  /api/v1/health       ✅  implemented                                   │
│  /api/v1/admissions   ⬜  planned                                       │
│  /api/v1/beds         ⬜  planned                                       │
│  /api/v1/resources    ⬜  planned                                       │
│  /api/v1/predictions  ⬜  planned                                       │
│  /api/v1/simulations  ⬜  planned                                       │
│  /api/v1/optimizations ⬜ planned                                       │
│  /api/v1/knowledge    ⬜  planned                                       │
│  /api/v1/agents       ⬜  planned                                       │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────────┐
│                     Application Service Layer  📐                        │
│  Hospital Operations · Admissions · Bed Management                      │
│  Resource Planning · Forecasting · Simulation                           │
│  Optimization · Knowledge · Agent Orchestration                         │
│                                                                         │
│  Rule: no API concerns here. No HTTP status codes.                      │
│  Rule: no LLM calls for calculations.                                   │
└────────┬─────────────────────┬──────────────────────┬───────────────────┘
         │                     │                      │
         ▼                     ▼                      ▼
┌─────────────────┐  ┌──────────────────┐  ┌─────────────────────────────┐
│  Repository     │  │   ML Layer  ⬜   │  │  Decision Engines  ⬜       │
│  Layer  📐      │  │  Forecasting ·   │  │  Simulation Engine          │
│  MongoDB CRUD   │  │  ICU prediction  │  │  Optimization Engine        │
│  Typed queries  │  │  Occupancy pred  │  │  Constraint solver          │
│  Index access   │  │  Feature pipes   │  │  Allocation recommendations │
└────────┬────────┘  └──────────────────┘  └─────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  MongoDB  ✅  (system of record)                                         │
│  Redis    ✅  (cache · transient state · future event bus)              │
└─────────────────────────────────────────────────────────────────────────┘

                   ┌─────────────────────────────────────────────────────┐
                   │           Agentic AI Layer  ⬜                       │
                   │  Orchestrator Agent                                  │
                   │    → selects and calls typed tool functions          │
                   │    → reasons about tool results                      │
                   │    → produces structured recommendations             │
                   │  Sub-agents (specialist, scoped tools)               │
                   │  Agent memory (Redis-backed)                         │
                   └────────────┬──────────────────┬──────────────────────┘
                                │                  │
              ┌─────────────────┘                  └────────────────────┐
              ▼                                                          ▼
┌─────────────────────────┐                              ┌──────────────────────────┐
│  RAG Pipeline  ⬜        │                              │  Operation Tools  ⬜      │
│  Document ingestion      │                              │  get_hospital_status     │
│  Chunking · Embedding    │                              │  get_bed_availability    │
│  Vector retrieval        │                              │  get_forecast            │
│  Source metadata         │                              │  run_simulation          │
│  Grounded context        │                              │  optimize_resources      │
└─────────────────────────┘                              └──────────────────────────┘

               ┌──────────────────────────────────────────────────────────┐
               │       Human-in-the-Loop Layer  ⬜                         │
               │  Recommendation → Pending Review → Approve/Reject/Modify │
               │  → Action → Audit Log                                     │
               └──────────────────────────────────────────────────────────┘
```

---

## Layer Responsibilities

### ✅ Frontend — `frontend/`

**Currently implemented:**
- React 18 + TypeScript application shell
- Vite build toolchain with Tailwind CSS
- Typed API client (`src/api/client.ts`)
- Environment-based API base URL

**Defined (Chunk 0.2):**
- Frontend calls backend exclusively via REST API
- No direct database access
- No business logic
- All calculations performed on the backend
- API client uses `SuccessResponse<T>` / `ErrorResponse` envelopes

**Planned:**
- Hospital operations dashboard
- AI copilot chat interface
- Real-time occupancy views (WebSocket)
- Human-in-the-loop approval UI

---

### ✅ FastAPI API Layer — `backend/app/api/`

**Currently implemented:**
- Versioned routing under `/api/v1/`
- CORS middleware
- Global exception handler → consistent error envelope
- `/api/v1/health` endpoint

**Defined (Chunk 0.2):**
- API layer contains: routing, validation, serialization, error translation
- API layer does NOT contain: business rules, calculations, database queries
- All requests eventually support `X-Request-ID` header (added by middleware)
- All responses return UTC ISO 8601 timestamps
- Success responses use `SuccessResponse[T]` wrapper
- Error responses use `ErrorResponse` envelope

**Planned:**
- Authentication middleware
- Rate limiting middleware
- All domain endpoint modules

---

### 📐 Application Service Layer — `backend/app/services/` *(defined, not yet implemented)*

Owns:
- Business rules and invariants
- Transactional workflows spanning multiple repositories
- Invocation of ML inference, simulation, and optimization engines
- Coordination of domain operations

Does NOT own:
- HTTP concerns (status codes, headers)
- Database queries (delegates to repositories)
- LLM calls for calculations

---

### 📐 Repository Layer — `backend/app/repositories/` *(defined, not yet implemented)*

Owns:
- All MongoDB collection reads and writes
- Index-aware query patterns
- Typed domain model hydration

Does NOT own:
- Business rules
- HTTP concerns
- Calling other repositories directly for cross-domain queries (uses services)

---

### ⬜ ML Layer — `ml/` *(planned)*

Owns:
- Feature engineering
- Model training and evaluation
- Model artifact management
- Inference / forecast generation

Interface to services: defined in `docs/architecture/integration-contracts.md`.

---

### ⬜ Simulation Layer — `simulation/` *(planned)*

Owns:
- Scenario definitions and validation
- Deterministic scenario computation
- Projected outcome generation

---

### ⬜ Optimization Layer — `optimization/` *(planned)*

Owns:
- Resource allocation modeling
- Constraint satisfaction
- Explainable recommendation generation

---

### ⬜ RAG Layer — `rag/` *(planned)*

Owns:
- Hospital policy and procedure documents
- Embedding pipeline
- Semantic retrieval
- Source-attributed context assembly

---

### ⬜ Agent Layer — `agents/` *(planned)*

Owns:
- Orchestration state and control flow
- Tool selection and execution
- Reasoning and summarization
- Agent memory (Redis-backed)

Does NOT own:
- Direct MongoDB access (delegates to services via tools)
- Calculations (delegates to service layer)

---

### ✅ MongoDB

- System of record for all hospital operational data
- Production target: MongoDB Atlas
- Schema evolution managed exclusively through the repository layer

---

### ✅ Redis

- Application-level cache
- Transient state (agent session memory in future)
- Future: domain event bus infrastructure

---

## Frontend–Backend Communication

```
Frontend                     Backend
─────────                    ───────
fetch(url, opts)
  → X-Request-ID: <uuid>  →  received by middleware
                           →  logged with request context
  ← SuccessResponse<T>    ←  success
  ← ErrorResponse         ←  any application error
```

All communication is over HTTP REST in the current architecture.
WebSocket support (for real-time occupancy updates) is planned for a future chunk.

---

## Real-Time / Event Architecture *(Planned)*

```
Domain Event generated (e.g. PATIENT_ADMITTED)
    ↓
Domain Service publishes to Redis Stream
    ↓
Event consumers (subscribed workers):
    → Monitoring / Alert service
    → Agent trigger service
    → Notification service (future)
    → Dashboard WebSocket relay (future)
```

Full event catalog defined in `docs/architecture/integration-contracts.md`.

---

## Human-in-the-Loop Architecture *(Planned)*

```
Agent generates recommendation
    ↓
Recommendation stored in MongoDB (status: PENDING_REVIEW)
    ↓
Dashboard surfaces recommendation to administrator
    ↓
Administrator: APPROVE / REJECT / MODIFY
    ↓
Audit log written (who, what, when, rationale)
    ↓
If APPROVED: Action executed by service layer
```

No autonomous resource changes. All consequential operations require explicit human approval.

---

## Data Flow Principles

1. **Reads flow down**: frontend → API → service → repository → MongoDB
2. **Writes flow down**: frontend → API → service → repository → MongoDB
3. **ML inference is separate**: data → feature pipeline → model → result stored in MongoDB
4. **Agents orchestrate, services calculate**: LLMs call typed Python functions; Python does the math
5. **RAG grounds LLMs**: agents retrieve real documents before generating summaries
6. **Humans approve consequential actions**: no autonomous resource modifications
7. **UTC everywhere**: all timestamps are timezone-aware UTC at every layer
8. **Correlation propagates**: request ID flows from frontend → API → service → audit log

---

## API Versioning

```
/api/v1/   ← current version (all new endpoints added here)
/api/v2/   ← future, only when breaking changes require it
```

See `docs/architecture/api-contracts.md` for full versioning strategy.

---

## Healthcare Safety Boundary

This architecture explicitly excludes:

- Clinical diagnosis
- Treatment recommendations
- Medication prescriptions
- Patient health record management (beyond operational identifiers)
- Direct patient communication
- Autonomous clinical decisions

HospitalOps AI operates on **operational data** only.
Full boundary definition: `AGENTS.md`.
