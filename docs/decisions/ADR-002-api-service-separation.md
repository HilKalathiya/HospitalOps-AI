# ADR-002 — API Layer Contains No Business Logic

**Date:** August 2026
**Status:** Accepted
**Deciders:** Engineering team
**Chunk:** 0.2 — Architecture & API Contract

---

## Context

As the team begins defining the domain API endpoints, it is critical to establish a
clear rule about where business logic lives.

FastAPI makes it syntactically easy to put logic directly inside route handler functions.
In small applications this causes no immediate problems. In a system of this complexity —
with hospital operations, ML forecasts, simulations, agent orchestration, and human-in-the-loop
approval — allowing business logic in route handlers creates serious long-term problems:

1. **Untestability**: Business logic in route handlers requires HTTP test clients even for
   unit tests, slowing the test suite and making isolation impossible.

2. **Duplication**: Agents calling the same operations as API consumers would need to
   replicate the logic or call internal HTTP endpoints, both of which are bad patterns.

3. **Mixing concerns**: HTTP error codes, Pydantic validation errors, and domain errors
   become entangled, making error handling brittle.

4. **Audit gaps**: When an agent changes resource state via a separate code path from the
   API, the audit trail becomes inconsistent.

---

## Decision

**The API layer contains no business logic.**

API route handlers are allowed to:
- Parse and validate request bodies (via Pydantic models)
- Call a single application service method
- Map service results to response schemas
- Return HTTP responses

API route handlers are **not allowed** to:
- Implement domain rules or invariants
- Access MongoDB or Redis directly
- Call repositories
- Invoke ML models or engines
- Make conditional decisions based on domain state

```python
# ✅ Correct: thin route handler
@router.post("/admissions", response_model=SuccessResponse[AdmissionResponse])
async def create_admission(
    body: AdmissionCreate,
    service: AdmissionsService = Depends(get_admissions_service),
) -> SuccessResponse[AdmissionResponse]:
    result = await service.create_admission(body)
    return SuccessResponse(data=result, meta=build_meta())

# ❌ Incorrect: business logic in route handler
@router.post("/admissions")
async def create_admission(body: AdmissionCreate, db = Depends(get_db)):
    bed = await db["beds"].find_one({"_id": body.bed_id})
    if bed["status"] != "available":
        raise HTTPException(status_code=409, detail="Bed not available")
    # ... more domain logic
```

---

## Consequences

### Positive
- Service methods are unit-testable without HTTP overhead
- Agents and API consumers use identical business logic
- Audit trail is consistent regardless of how an operation is triggered
- Switching transport (HTTP → gRPC → message queue) requires no service changes

### Negative / Trade-offs
- Requires more files and classes than a minimal FastAPI app
- Junior engineers may be tempted to add logic to route handlers for speed

### Mitigation
- Code review must catch route handlers that grow beyond the allowed pattern
- This ADR serves as the documented enforcement standard
- `backend/app/services/` directory structure makes the correct location obvious

---

## Alternatives Considered

### Fat controllers (logic in route handlers)
Rejected: untestable, causes duplication, breaks audit consistency.

### Logic in Pydantic validators
Partially acceptable for pure input validation, but rejected for domain rules that
require database state (e.g., checking bed availability).

---

## Related Decisions

- ADR-001: Layered architecture overview
- ADR-003: Domain-modular backend organisation
