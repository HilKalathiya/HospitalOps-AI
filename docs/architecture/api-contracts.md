# HospitalOps AI — API Contracts

> **Document status:** Chunk 0.2 — Architecture & API Contract
> **Last updated:** August 2026

This document defines the API conventions that **all** current and future HospitalOps AI
endpoints must follow. Any deviation requires a documented justification.

---

## Base URL

All endpoints are versioned under:

```
/api/v1/
```

**Current endpoints (implemented):**

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/health` | GET | Application health check |

**Future endpoints follow the pattern** defined in this document.

---

## Versioning Strategy

### Current version: `/api/v1/`

All new endpoints added to the system extend `/api/v1/` until a breaking change is necessary.

### What constitutes a breaking change requiring `/api/v2/`:

- Removing a field from a response
- Renaming a field
- Changing a field type
- Changing an error code that clients depend on
- Changing URL structure of an existing endpoint

### What does NOT require a new version:

- Adding a new optional field to a response
- Adding a new endpoint
- Adding a new optional query parameter
- Adding a new error code (additive)

### Versioning mechanics:

When `/api/v2/` is introduced, both `/api/v1/` and `/api/v2/` remain operational for a
documented deprecation period. The deprecation date and sunset date must be documented in
the relevant ADR.

---

## Response Envelopes

### Success Response

All successful API responses use the `SuccessResponse[T]` envelope:

```json
{
  "data": { ... },
  "meta": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2026-08-13T10:30:00Z"
  }
}
```

| Field | Type | Description |
|---|---|---|
| `data` | object or array | The primary response payload |
| `meta.request_id` | string (UUID) | Correlation ID from `X-Request-ID` header |
| `meta.timestamp` | string (ISO 8601 UTC) | Server-side response timestamp |

**List responses** include pagination in `meta`:

```json
{
  "data": [ ... ],
  "meta": {
    "request_id": "550e8400-...",
    "timestamp": "2026-08-13T10:30:00Z",
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 143,
      "total_pages": 8
    }
  }
}
```

> **Note**: The `/api/v1/health` endpoint returns a `HealthResponse` directly (not wrapped
> in `SuccessResponse`) because it is a system-level diagnostic endpoint, not a domain resource.
> Domain endpoints use `SuccessResponse[T]`.

---

### Error Response

All application errors use a consistent error envelope:

```json
{
  "error": "RESOURCE_NOT_FOUND",
  "message": "The requested bed was not found.",
  "detail": "bed_id=BED-042",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

| Field | Type | Description |
|---|---|---|
| `error` | string | Machine-readable code in `SCREAMING_SNAKE_CASE` |
| `message` | string | Human-readable description, safe to surface to users |
| `detail` | string or null | Optional additional context (never a stack trace) |
| `request_id` | string or null | Correlation ID (when available) |

**Standard error codes:**

| Code | HTTP Status | Meaning |
|---|---|---|
| `NOT_FOUND` | 404 | Resource does not exist |
| `VALIDATION_ERROR` | 422 | Input data failed validation |
| `CONFLICT` | 409 | State conflict (e.g., duplicate resource) |
| `UNAUTHORIZED` | 401 | Authentication required |
| `FORBIDDEN` | 403 | Authenticated but not authorized |
| `SERVICE_UNAVAILABLE` | 503 | Dependency (MongoDB, Redis) unreachable |
| `INTERNAL_SERVER_ERROR` | 500 | Unexpected server error |

Stack traces are **never** included in API responses. Full error details are logged server-side.

---

## HTTP Verb Conventions

| Verb | Meaning | Body | Idempotent |
|---|---|---|---|
| `GET` | Read resource(s) | None | Yes |
| `POST` | Create resource | Required | No |
| `PUT` | Replace resource entirely | Required | Yes |
| `PATCH` | Partial update | Required (partial) | Yes |
| `DELETE` | Remove resource | None | Yes |

---

## URL Naming Conventions

| Rule | Example |
|---|---|
| Resources are **plural nouns** | `/api/v1/admissions` not `/api/v1/admission` |
| Use **kebab-case** for multi-word resources | `/api/v1/agent-runs` |
| Sub-resources use nested paths | `/api/v1/admissions/{id}/discharge` |
| Actions that don't map to CRUD use verbs as sub-paths | `/api/v1/simulations/{id}/cancel` |
| No trailing slashes | `/api/v1/beds` not `/api/v1/beds/` |
| IDs in path segments, not query string | `/api/v1/beds/{bed_id}` |

**Illustrative future endpoint examples** (not yet implemented):

```
GET    /api/v1/admissions                 → list admissions
POST   /api/v1/admissions                 → create admission record
GET    /api/v1/admissions/{id}            → get single admission
PATCH  /api/v1/admissions/{id}            → update admission
POST   /api/v1/admissions/{id}/discharge  → discharge event

GET    /api/v1/beds                       → list beds
GET    /api/v1/beds/{id}                  → get single bed

GET    /api/v1/predictions/icu            → current ICU demand forecast
GET    /api/v1/predictions/occupancy      → current occupancy forecast

POST   /api/v1/simulations                → submit scenario
GET    /api/v1/simulations/{id}           → get scenario result

POST   /api/v1/optimizations              → request resource optimization
GET    /api/v1/optimizations/{id}         → get optimization result
POST   /api/v1/optimizations/{id}/approve → human approval action

POST   /api/v1/knowledge/search           → semantic document search

POST   /api/v1/agents/runs                → start agent run
GET    /api/v1/agents/runs/{id}           → get agent run result
```

---

## Pagination

All list endpoints that can return multiple items support cursor- or page-based pagination.

**Query parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `page` | integer | 1 | Page number (1-indexed) |
| `page_size` | integer | 20 | Items per page (max: 100) |

**Response (in `meta.pagination`):**

| Field | Type | Description |
|---|---|---|
| `page` | integer | Current page |
| `page_size` | integer | Items per page |
| `total` | integer | Total matching items |
| `total_pages` | integer | Total pages |

---

## Filtering

List endpoints support filtering via query parameters:

```
GET /api/v1/beds?status=available&department_id=ICU
GET /api/v1/admissions?admitted_after=2026-08-01T00:00:00Z&status=active
```

Filter parameter names match the field names in the resource schema.
Date filters use ISO 8601 UTC format.

---

## Sorting

```
GET /api/v1/admissions?sort_by=admitted_at&sort_order=desc
```

| Parameter | Values | Default |
|---|---|---|
| `sort_by` | field name | resource-dependent |
| `sort_order` | `asc`, `desc` | `desc` |

---

## Date / Time Contract

> **Rule**: All timestamps are stored and returned as **timezone-aware ISO 8601 UTC**.

```
✅  "2026-08-13T10:30:00Z"        (UTC with Z suffix)
✅  "2026-08-13T10:30:00+00:00"   (UTC with explicit offset)
❌  "2026-08-13T10:30:00"         (naive datetime — NEVER use)
❌  "2026-08-13T16:00:00+05:30"   (non-UTC timezone — NEVER return from API)
```

- Backend stores `datetime` objects with `tz=UTC` (Python `datetime.UTC`)
- Backend serializes using Pydantic's ISO 8601 serialization (includes timezone)
- Frontend must parse timestamps with timezone awareness
- Client-side display conversion to local time is acceptable, but the wire format is always UTC

See `ADR-005-utc-and-traceability.md` for the full rationale.

---

## Request ID / Correlation ID

Every request and response will support a correlation ID for end-to-end tracing.

### Mechanics

**Inbound:** Clients may send `X-Request-ID: <uuid>` in the request header.

**Server behaviour:**
1. If `X-Request-ID` is present and valid UUID — use it.
2. If not present — generate a new UUID.
3. Echo the ID in: response `meta.request_id` + all structured log entries for that request.

**Propagation chain:**
```
Frontend  →  X-Request-ID header
    ↓
API middleware  →  attaches to request context
    ↓
Service layer  →  receives via context / function argument
    ↓
Repository / ML / Simulation / Optimization  →  logged with ID
    ↓
Agent tool calls  →  logged with ID
    ↓
Audit log entry  →  stored with request_id
```

**Implementation note for Chunk 0.2:** The correlation ID contract is defined here.
The middleware implementation will be added in the chunk that introduces the first domain endpoint.

---

## OpenAPI Documentation

The FastAPI application automatically generates OpenAPI 3 documentation.

| URL | Description |
|---|---|
| `/docs` | Swagger UI (interactive) |
| `/redoc` | ReDoc (readable) |
| `/openapi.json` | Raw OpenAPI JSON schema |

**Rules:**
- All request and response models must have Pydantic schemas with `Field(description=...)`.
- All endpoints must have `summary` and `description` in the route decorator.
- Add `response_model` to all route functions.
- Add `responses` dict for documented error cases.
- Do not add fake schemas to inflate the spec — only implemented schemas appear.

---

## Authentication (Future)

Authentication is not implemented in Chunk 0.2.

The architecture is designed to accept an authentication middleware layer
that will be inserted at the FastAPI middleware stack level — requiring no
changes to endpoint logic.

The planned approach:
- JWT Bearer tokens in `Authorization` header
- Token validation middleware (hooks already present in architecture)
- Role claims embedded in token payload
- No API-key authentication for the operational API

---

## Future Illustrative API Contract Examples

The following shows the *contract shape* domain endpoints will use when implemented.
**These are documentation examples only — not implemented.**

### Admission resource (future)

**Request: POST /api/v1/admissions**
```json
{
  "patient_id": "PAT-00123",
  "department_id": "DEPT-ICU",
  "bed_id": "BED-042",
  "admission_type": "emergency",
  "estimated_los_days": 3
}
```

**Response: 201 Created**
```json
{
  "data": {
    "id": "ADM-00456",
    "patient_id": "PAT-00123",
    "department_id": "DEPT-ICU",
    "bed_id": "BED-042",
    "status": "active",
    "admitted_at": "2026-08-13T10:30:00Z",
    "created_at": "2026-08-13T10:30:00Z",
    "updated_at": "2026-08-13T10:30:00Z"
  },
  "meta": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2026-08-13T10:30:00Z"
  }
}
```
