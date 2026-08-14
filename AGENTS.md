# HospitalOps AI — Engineering Constitution

## Project Identity

**Project:** HospitalOps AI
**Purpose:** Agentic AI-powered hospital operations intelligence and resource optimization platform.

HospitalOps AI is an **operational decision-support system** that combines hospital operational
data, real-time occupancy information, machine-learning forecasting, resource optimization,
retrieval-augmented generation, and multi-agent orchestration to help hospital administrators
make better operational decisions.

---

## Architecture Principles

The system is built on a strict separation of responsibilities:

```
LLM / Agents
    → reasoning and orchestration only
    → never used for deterministic calculations
    → never allowed to silently invent database facts

Python Services
    → deterministic business logic
    → calculations, transformations, validations

ML Models
    → prediction and forecasting
    → inference only, never decision authority

Optimization Engine
    → resource allocation algorithms
    → deterministic, explainable outputs

RAG
    → hospital knowledge retrieval
    → grounded in real documents

MongoDB
    → system of record
    → authoritative persistence layer

Redis
    → cache, transient state, and event infrastructure
    → not a system of record
```

**Key invariants:**
- Never use an LLM for calculations that should be deterministic.
- Never allow an LLM to silently invent database facts.
- Never mix clinical diagnosis functionality into this project.
- All consequential operational recommendations must support human review before action.

---

## Healthcare Safety Boundary

HospitalOps AI is an **operational decision-support platform**, not a clinical decision-making
system. This distinction is non-negotiable and must be enforced at every layer.

### The system MAY:
- Analyze hospital operations
- Predict bed demand and occupancy
- Predict ICU and ward utilization
- Identify operational risks
- Simulate what-if scenarios
- Recommend resource allocations
- Retrieve operational policies via RAG
- Summarize operational data
- Generate operational alerts
- Assist hospital administrators

### The system MUST NOT:
- Diagnose patients
- Prescribe medications or treatments
- Determine medical treatment plans
- Independently discharge patients
- Replace or override clinicians
- Autonomously make clinical decisions
- Present operational recommendations as clinical authority

Any feature that risks crossing this boundary must be reviewed and explicitly rejected or scoped.

---

## Engineering Rules

### Code Quality
- Prefer clear, maintainable code over clever code.
- Keep modules small and focused on a single responsibility.
- Use strong typing wherever practical (TypeScript on frontend, Pydantic on backend).
- Avoid duplicated business logic.
- Separate API, service, repository, and model concerns.
- Do not introduce unnecessary abstractions.
- Do not rewrite working code without a strong documented reason.
- Preserve backwards compatibility unless a breaking change is explicitly justified.

### Configuration
- Never hardcode credentials anywhere in the codebase.
- Never commit secrets or API keys.
- Use environment variables for all environment-specific configuration.
- Maintain `.env.example` with all required keys and safe placeholder values.
- Validate required configuration at application startup; fail fast with a clear error.

### APIs
- Use RESTful naming conventions.
- Version all APIs under `/api/v1/` from the start.
- Use Pydantic schemas for request and response validation.
- Return consistent error response structures.
- Keep API contracts documented.
- Do not expose internal implementation details in API responses.

### Testing
Every meaningful backend feature must have tests. Prefer:
```
unit tests       → isolated logic, no external dependencies
integration tests → service interaction with real or mock databases
API tests        → endpoint behavior via HTTP client
```
Tests must pass before a chunk is considered complete.

### Logging
- Use structured logging.
- Log at appropriate levels (DEBUG, INFO, WARNING, ERROR, CRITICAL).
- Never log credentials, tokens, or patient data.
- Include correlation IDs for request tracing where practical.

### Error Handling
- Handle errors at the appropriate layer.
- Return user-friendly error messages from APIs.
- Log full error details server-side.
- Never expose stack traces to API consumers.

### Git
- Each completed chunk should produce a focused, atomic commit.
- Do not make unrelated changes in the same commit.
- Write meaningful commit messages describing what changed and why.

### Auditability
- Every consequential action should be traceable.
- Design for audit logs from the beginning, even if not fully implemented yet.
- Agent decisions must be explainable and logged.

### Dependency Discipline
- Do not install packages merely because they may be useful later.
- Every dependency must serve a current, justified purpose.
- Review dependencies for security and maintenance status.
- Prefer well-maintained, widely-used libraries.

---

## Architectural Decision Records

All significant architectural decisions must be documented in `docs/decisions/`.

Format: `ADR-NNN-short-title.md`

See `docs/decisions/ADR-001-layered-architecture.md` for the founding architectural decision.

---

## Technology Stack

| Layer          | Technology                        |
|----------------|-----------------------------------|
| Frontend       | React, TypeScript, Vite, Tailwind |
| Backend        | Python, FastAPI, Pydantic, Uvicorn|
| Database       | MongoDB (Atlas in production)     |
| Cache / Events | Redis                             |
| ML (future)    | To be determined per chunk        |
| Agents (future)| To be determined per chunk        |
| RAG (future)   | To be determined per chunk        |
| Infrastructure | Docker, Docker Compose            |

---

## Implementation Status

| Chunk | Description                                      | Status      |
|-------|--------------------------------------------------|-------------|
| 0.1   | Project initialization & foundation              | ✅ Complete |
| 0.2   | Architecture, API contracts & domain boundaries  | ✅ Complete |
| 0.3   | Docker runtime validation & dev env hardening    | ✅ Complete |
| 1.1   | MongoDB data model & persistence layer           | ✅ Complete |
| 1.2   | (next)                                           | ⬜ Not started |

---

## Contributing

1. Read this file before making any changes.
2. Follow the engineering rules above.
3. Run tests before submitting.
4. Document architectural decisions in `docs/decisions/`.
5. Update `README.md` if setup steps change.