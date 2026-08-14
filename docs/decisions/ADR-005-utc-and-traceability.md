# ADR-005 — UTC Timestamps and Request Correlation IDs

**Date:** August 2026
**Status:** Accepted
**Deciders:** Engineering team
**Chunk:** 0.2 — Architecture & API Contract

---

## Context

### Timestamp problem

HospitalOps AI will operate in hospitals that may span multiple time zones and will
eventually be deployed to cloud infrastructure that may itself be in a different timezone
from the hospital.

Hospital operational data is inherently time-sensitive: admission times, discharge times,
forecast horizons, alert timestamps, audit trail entries. A single ambiguous or naive timestamp
can cause:
- Incorrect duration calculations
- Mismatched forecast horizons
- Audit log entries that cannot be compared across services
- Bugs that are extremely difficult to reproduce (timezone-dependent)

Without a firm rule, engineers will mix:
- Naive datetimes (no timezone info)
- Local-timezone datetimes
- UTC datetimes

Any mixture is a persistent bug source.

### Correlation / traceability problem

HospitalOps AI will have a complex multi-layer request path:
```
Frontend → API → Service → Repository → ML → Simulation → Agent Tools → Audit Log
```

Without a correlation mechanism, debugging failures that span multiple layers requires
matching log timestamps (imprecise) and hoping log entries from different components
can be linked manually. This is unworkable at production scale.

---

## Decision

### Rule 1: UTC Everywhere

**All timestamps stored, computed, and returned by HospitalOps AI are UTC.**

- Python backend: always use `datetime.now(tz=UTC)` (from `datetime import UTC`)
- Never use `datetime.utcnow()` (returns a naive datetime — deprecated in Python 3.12)
- Never use `datetime.now()` without a `tz` argument
- MongoDB storage: BSON Date type (UTC milliseconds — handled automatically by Motor)
- API responses: ISO 8601 UTC strings (`"2026-08-13T10:30:00Z"` or `+00:00`)
- Frontend: parses UTC timestamps; converts to local time for display only

**Validation:**
- Pydantic models use `datetime` fields with timezone validation
- The ruff `UP017` rule (already enabled) catches legacy `timezone.utc` usage
- Code review must reject any `datetime.now()` without `tz=UTC`

### Rule 2: Request Correlation IDs

**Every backend request is assigned a UUID correlation ID (`request_id`).**

**Mechanics:**
1. Frontend may send `X-Request-ID: <uuid>` header with any request.
2. If the header is present and a valid UUID, the backend uses it.
3. If absent, the backend generates a new UUID.
4. The `request_id` is attached to the request context (FastAPI `Request.state`).
5. All structured log entries during the request include the `request_id`.
6. The `request_id` is returned in every API response's `meta.request_id` field.
7. The `request_id` is propagated into service calls via function argument.
8. The `request_id` is stored in audit log entries.

**Implementation note for Chunk 0.2:** The contract is defined here.
The `X-Request-ID` middleware implementation is deferred to the chunk that introduces
the first domain endpoint, to avoid unnecessary infrastructure before it can be tested.

---

## Consequences

### Positive
- UTC rule eliminates entire class of timezone-related bugs
- Correlation IDs make production debugging tractable
- Audit logs are unambiguously traceable
- ML forecast horizons are unambiguous
- Cross-service log correlation works without additional tooling

### Negative / Trade-offs
- UTC conversion for display must be handled in the frontend
- Engineers must be disciplined about always using `UTC` — requires culture + tooling
- Correlation ID propagation requires threading context through function signatures

### Mitigation
- Ruff `UP017` rule enforces the UTC alias pattern
- `TimestampedModel` base class (Chunk 0.1) already uses `UTC` — sets the pattern
- Correlation ID will be propagated as a keyword argument (`request_id: str`),
  not via a global / thread-local, to keep it explicit and testable

---

## Alternatives Considered

### Store timestamps in local hospital timezone
Rejected: creates ambiguity when hospitals span timezones, makes cross-service log
correlation impossible, and creates permanent bugs in duration calculations.

### Use Unix timestamps (integer)
Considered: eliminates ambiguity but makes logs and debug output unreadable.
ISO 8601 UTC strings are unambiguous AND human-readable. Rejected.

### Thread-local / contextvars for request_id propagation
Considered: reduces function signature verbosity. Rejected for Chunk 0.2 because
it introduces implicit global state that makes testing harder. May be revisited
if the explicit propagation becomes too verbose at scale.

---

## Related Decisions

- ADR-001: Layered architecture overview
- ADR-002: API layer contains no business logic
