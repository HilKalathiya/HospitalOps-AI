# HospitalOps AI — Service & Repository Patterns

> **Document status:** Chunk 0.2 — Architecture & API Contract
> **Last updated:** August 2026

This document defines the **implementation patterns** for services and repositories
that all future domain chunks must follow.

---

## The Core Pattern

```
HTTP Request
    ↓
API Route Handler
    ↓ (validated Pydantic schema)
Application Service
    ↓ (domain operations)
    ├── Repository (database reads/writes)
    ├── ML Layer (inference, if needed)
    ├── Simulation / Optimization Engine (if needed)
    └── Other Services (cross-domain, if needed)
    ↓
Response Schema
    ↓
HTTP Response (wrapped in SuccessResponse[T])
```

```
Agent Tool Call
    ↓
Application Service  (same services as above)
    ↓
Repository / Domain Engine
    ↓
Typed Result returned to Agent
```

---

## Service Layer Rules

### What services OWN

- Business rules and domain invariants
- Multi-step transactional workflows
- Coordination between repositories
- Invocation of ML, simulation, and optimization components
- Cross-domain orchestration

### What services MUST NOT do

| ❌ Forbidden | ✅ Correct alternative |
|---|---|
| Access MongoDB directly via motor | Delegate to a repository method |
| Read `request.headers` or `response.status_code` | API layer handles HTTP concerns |
| Call an LLM for a calculation | Perform the calculation deterministically |
| Raise `HTTPException` | Raise a `HospitalOpsError` subclass |
| Import from `fastapi` | Services have no FastAPI dependency |

### Service class pattern

```python
# backend/app/services/admissions.py  (future)

class AdmissionsService:
    """
    Owns all business logic for the admissions domain.
    """

    def __init__(
        self,
        admissions_repo: AdmissionsRepository,
        beds_repo: BedsRepository,
    ) -> None:
        self._admissions = admissions_repo
        self._beds = beds_repo

    async def create_admission(
        self,
        data: AdmissionCreate,
        *,
        request_id: str,
    ) -> AdmissionResponse:
        """
        Record a new patient admission.
        Validates bed availability before committing.
        """
        bed = await self._beds.get_by_id(data.bed_id)
        if bed is None:
            raise NotFoundError(f"Bed {data.bed_id} not found.")
        if bed.status != BedStatus.AVAILABLE:
            raise ConflictError(f"Bed {data.bed_id} is not available.")

        return await self._admissions.create(data)
```

### Dependency injection

Services are created and injected via FastAPI's `Depends()` mechanism.

```python
# backend/app/api/v1/endpoints/admissions.py  (future)

async def get_admissions_service(
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> AdmissionsService:
    admissions_repo = AdmissionsRepository(db)
    beds_repo = BedsRepository(db)
    return AdmissionsService(admissions_repo, beds_repo)

@router.post("/", response_model=SuccessResponse[AdmissionResponse])
async def create_admission(
    body: AdmissionCreate,
    service: AdmissionsService = Depends(get_admissions_service),
) -> SuccessResponse[AdmissionResponse]:
    result = await service.create_admission(body, request_id=...)
    return SuccessResponse(data=result, meta=...)
```

---

## Repository Layer Rules

### What repositories OWN

- All MongoDB collection read and write operations
- Index-aware query construction
- Hydration of raw MongoDB documents into typed Pydantic models
- Query filtering and pagination (accepting filter/pagination schema objects)

### What repositories MUST NOT do

| ❌ Forbidden | ✅ Correct alternative |
|---|---|
| Contain business rules | Delegate to service layer |
| Call other repositories | Service layer coordinates between repos |
| Raise `HTTPException` | Raise `HospitalOpsError` or return `None` |
| Import from `fastapi` | Repos have no FastAPI dependency |
| Contain application logging for business events | Service layer logs domain events |

### Repository class pattern

```python
# backend/app/repositories/admissions.py  (future)

class AdmissionsRepository:
    """
    All MongoDB operations for the admissions collection.
    """

    COLLECTION = "admissions"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db[self.COLLECTION]

    async def create(self, data: AdmissionCreate) -> AdmissionResponse:
        doc = {
            **data.model_dump(),
            "status": AdmissionStatus.ACTIVE,
            "created_at": datetime.now(tz=UTC),
            "updated_at": datetime.now(tz=UTC),
        }
        result = await self._col.insert_one(doc)
        doc["_id"] = result.inserted_id
        return AdmissionResponse(**doc)

    async def get_by_id(self, admission_id: str) -> AdmissionResponse | None:
        doc = await self._col.find_one({"_id": ObjectId(admission_id), "is_deleted": False})
        if doc is None:
            return None
        return AdmissionResponse(**doc)

    async def list(
        self,
        filters: AdmissionFilter,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[AdmissionResponse], int]:
        query = self._build_query(filters)
        total = await self._col.count_documents(query)
        cursor = self._col.find(query).skip((page - 1) * page_size).limit(page_size)
        docs = await cursor.to_list(length=page_size)
        return [AdmissionResponse(**d) for d in docs], total

    def _build_query(self, filters: AdmissionFilter) -> dict:
        q: dict = {"is_deleted": False}
        if filters.status:
            q["status"] = filters.status
        if filters.department_id:
            q["department_id"] = filters.department_id
        return q
```

---

## Agent → Tool → Service Pattern

The agent layer calls typed **tool functions**. Tool functions are thin wrappers that:
1. Accept a typed input schema
2. Call the appropriate application service
3. Return a typed result schema

```
Agent (LLM orchestrator)
    ↓ selects tool based on reasoning
Tool function  (typed Python function)
    ↓ calls service with validated input
Application Service  (deterministic logic)
    ↓
Repository / ML / Optimization
    ↓
Typed result returned to tool
    ↓
Typed result returned to agent
    ↓
Agent reasons about result (LLM)
```

### Why agents must NOT become a database layer

If agents called MongoDB directly:
- No business rule validation
- No audit logging
- No authorization checks
- Test isolation becomes impossible (agent tests require live MongoDB)
- Business logic leaks into LLM prompt engineering

All agent data access goes through the same service layer used by the REST API.
This ensures that agents and API consumers always receive the same validated, business-rule-compliant data.

### Tool function pattern

```python
# agents/tools/operations.py  (future)

async def get_bed_availability(
    department_id: str,
    *,
    beds_service: BedsService,
    request_id: str,
) -> BedAvailabilityResult:
    """
    Tool: Get current bed availability for a department.
    Called by the agent orchestrator; delegates to service layer.
    """
    return await beds_service.get_availability_summary(
        department_id=department_id,
        request_id=request_id,
    )
```

The agent calls `get_bed_availability(department_id="ICU")` and receives back a
typed `BedAvailabilityResult` — it never touches the `beds` collection directly.

---

## Cross-Domain Service Interaction

When a service needs data from another domain, it:
1. Accepts the other domain's **repository** (or **service**) as a constructor argument
2. Calls the other repo/service methods via the injected dependency
3. Does NOT import or instantiate the other repo/service itself

This keeps dependency graphs explicit and testable.

```python
# CORRECT: dependency injected
class SimulationService:
    def __init__(self, beds_repo: BedsRepository, admissions_repo: AdmissionsRepository):
        ...

# INCORRECT: direct instantiation inside service
class SimulationService:
    async def run(self, ...):
        beds_repo = BedsRepository(db)  # ← anti-pattern
```

---

## Testing Implications

Because services and repositories are fully decoupled from FastAPI:

| Test type | What is mocked | What runs for real |
|---|---|---|
| Service unit test | Repositories (use `AsyncMock`) | Service logic |
| Repository integration test | Nothing | MongoDB (test database) |
| API endpoint test | Services (use `AsyncMock`) | FastAPI routing + validation |
| Agent tool test | Services (use `AsyncMock`) | Tool function |
| Full integration test | Nothing | All layers + real MongoDB + Redis |

This structure enables fast, isolated unit tests for all business logic.
