# HospitalOps AI — Data Contracts

> **Document status:** Chunk 0.2 — Architecture & API Contract
> **Last updated:** August 2026

This document defines the data conventions for MongoDB, Pydantic schemas, and
inter-layer data contracts. All future domain implementations must follow these conventions.

---

## MongoDB Conventions

### Database

| Environment | Database Name |
|---|---|
| Development (local Docker) | `hospitalops` |
| Staging | `hospitalops_staging` |
| Production (Atlas) | `hospitalops_prod` |

The database name is configured via `MONGODB_DATABASE` environment variable.

---

### Collection Naming

| Rule | Example |
|---|---|
| **Plural snake_case** | `admissions`, `audit_log` |
| No hyphens | `agent_runs` not `agent-runs` |
| No camelCase | `bed_status` not `bedStatus` |
| Multi-word: underscore separator | `simulation_runs`, `knowledge_chunks` |

**Planned collections:**

| Domain | Collection(s) |
|---|---|
| identity | `users` |
| patients | `patients` |
| admissions | `admissions` |
| departments | `departments` |
| beds | `beds` |
| resources | `resources` |
| predictions | `predictions` |
| alerts | `alerts` |
| simulation | `simulation_runs` |
| optimization | `optimization_runs` |
| knowledge | `knowledge_documents`, `knowledge_chunks` |
| agents | `agent_runs`, `agent_memory` |
| audit | `audit_log` |

---

### Document Identifiers

All MongoDB documents use the native `_id` field (ObjectId by default).

**External / API identifier convention:**

- The `_id` ObjectId is never exposed in API responses directly.
- Each domain document exposes a human-meaningful string alias:
  - `admissions._id` → exposed as `id` in API (string representation of ObjectId)
  - `beds._id` → exposed as `id` in API
- Optional: domain-specific prefixed identifiers may be stored as a separate field:
  - `admission_number: "ADM-00456"` (human-readable, for UI display)
  - `bed_number: "BED-042"` (physical bed label)

**Pydantic aliasing example (future):**
```python
from pydantic import Field
from bson import ObjectId

class AdmissionResponse(BaseModel):
    id: str = Field(alias="_id")
    # ...
```

---

### Timestamp Conventions

Every MongoDB document that represents a mutable entity MUST have:

| Field | Type | Rule |
|---|---|---|
| `created_at` | `datetime` (UTC, timezone-aware) | Set on creation, never modified |
| `updated_at` | `datetime` (UTC, timezone-aware) | Updated on every write |

Both fields are inherited from `TimestampedModel` defined in `backend/app/models/base.py`.

**MongoDB storage:** Timestamps are stored as BSON `Date` type (UTC milliseconds).
Motor (the async MongoDB driver) handles Python `datetime` ↔ BSON `Date` conversion automatically.

**Never store naive datetimes.** All `datetime` objects must have `tz=UTC` before persistence.

---

### Soft Delete Policy

HospitalOps AI uses **soft deletes** for domain entities where audit history matters
(admissions, optimization runs, agent runs, alerts).

```python
# Soft delete fields (future)
is_deleted: bool = False
deleted_at: datetime | None = None
deleted_by: str | None = None   # user_id of the actor
```

**Hard deletes** are only used for truly ephemeral data (e.g., cache entries).

The default query filter for all repositories must exclude soft-deleted records
unless explicitly requested (e.g., audit views).

---

### Indexing Guidelines

Indexes must be defined as part of the repository layer, not ad-hoc in service code.

**Rules:**
1. Every collection must have indexes for its primary query patterns.
2. Compound indexes should be preferred over multiple single-field indexes where
   multiple fields are always queried together.
3. Do not create indexes speculatively — only for actual query patterns.
4. TTL indexes for time-limited data (cache-like collections).
5. Text indexes for full-text search fields (before vector search is introduced).

**Example planned indexes (future):**
```
admissions: { status: 1, admitted_at: -1 }         → list active admissions by time
admissions: { department_id: 1, status: 1 }         → beds-by-department queries
beds: { department_id: 1, status: 1 }               → available beds in department
predictions: { generated_at: -1, forecast_type: 1 } → latest forecast of type
audit_log: { entity_type: 1, entity_id: 1, ts: -1 } → entity audit history
```

---

## Pydantic Schema Conventions

### Schema Naming Pattern

All request and response schemas follow the `{Domain}{Purpose}` naming convention:

| Suffix | Purpose | Example |
|---|---|---|
| `Create` | Data required to create a resource | `AdmissionCreate` |
| `Update` | Fields permitted in a partial update (all optional) | `AdmissionUpdate` |
| `Response` | Fields returned to API consumers | `AdmissionResponse` |
| `Internal` | Internal service-layer representation (not exposed to API) | `AdmissionInternal` |
| `Filter` | Query filter parameters for list endpoints | `AdmissionFilter` |

**Examples (not yet implemented — illustrative):**

```python
class AdmissionCreate(BaseModel):
    """Fields required to record a new admission."""
    patient_id: str
    department_id: str
    bed_id: str
    admission_type: AdmissionType
    estimated_los_days: int | None = None

class AdmissionUpdate(BaseModel):
    """Fields that may be updated on an existing admission."""
    estimated_los_days: int | None = None
    notes: str | None = None

class AdmissionResponse(BaseModel):
    """Fields returned to API consumers for an admission."""
    id: str
    patient_id: str
    department_id: str
    bed_id: str
    status: AdmissionStatus
    admitted_at: datetime
    discharged_at: datetime | None
    created_at: datetime
    updated_at: datetime

class AdmissionInternal(AdmissionResponse):
    """Internal representation with audit fields."""
    created_by: str
    updated_by: str
```

---

### Schema Organisation on Disk

```
backend/app/schemas/
├── common.py          ← shared envelopes: SuccessResponse, ErrorResponse, PaginationMeta
├── admissions.py      ← AdmissionCreate, AdmissionUpdate, AdmissionResponse  (future)
├── beds.py            ← BedCreate, BedUpdate, BedResponse                    (future)
├── resources.py       ← ResourceCreate, ResourceUpdate, ResourceResponse     (future)
├── predictions.py     ← ForecastResponse, SurgeAlert                         (future)
├── simulation.py      ← ScenarioRequest, ScenarioResult                      (future)
├── optimization.py    ← OptimizationRequest, OptimizationResult              (future)
├── knowledge.py       ← KnowledgeSearchRequest, KnowledgeSearchResult        (future)
└── agents.py          ← AgentRunRequest, AgentRunResult                      (future)
```

Each schema file maps 1:1 to a domain.

---

### Field Validation Rules

1. **Required fields** have no default. Pydantic will reject missing required fields.
2. **Optional fields** use `field: Type | None = None`.
3. **Enum fields** use Python `Enum` classes, stored as string values (via `use_enum_values=True`).
4. **String lengths** are validated via `Field(max_length=...)` where appropriate.
5. **Positive integers** use `Field(gt=0)` or `Field(ge=0)` as appropriate.
6. **Timestamps** are always `datetime` with UTC awareness (never `str`).

---

## Inter-Layer Data Contracts

### API → Service

The API layer passes **validated Pydantic `Create` / `Update` objects** to services.
It does not pass raw dicts or request objects.

```python
# API layer
@router.post("/admissions", response_model=SuccessResponse[AdmissionResponse])
async def create_admission(body: AdmissionCreate) -> SuccessResponse[AdmissionResponse]:
    result = await admissions_service.create_admission(body)
    return SuccessResponse(data=result, meta=ResponseMeta(...))
```

### Service → Repository

Services pass **validated domain objects or primitive parameters** to repositories.
They do not construct raw MongoDB query dicts.

```python
# Service layer
async def create_admission(admission: AdmissionCreate) -> AdmissionResponse:
    # business validation
    await self.beds_repo.assert_bed_available(admission.bed_id)
    # delegate to repository
    return await self.admissions_repo.create(admission)
```

### Repository → MongoDB

Repositories own **all query construction**.

```python
# Repository layer
async def create(self, admission: AdmissionCreate) -> AdmissionResponse:
    doc = {**admission.model_dump(), "created_at": datetime.now(tz=UTC), ...}
    result = await self._collection.insert_one(doc)
    return AdmissionResponse(id=str(result.inserted_id), **doc)
```

### ML / Simulation / Optimization → Service

These engines accept typed input objects and return typed result objects.
They are called by the service layer, not directly from API routes.
Full interface contracts are defined in `docs/architecture/integration-contracts.md`.
