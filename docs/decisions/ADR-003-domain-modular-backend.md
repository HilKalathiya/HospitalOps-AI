# ADR-003 — Domain-Oriented Modular Backend Architecture

**Date:** August 2026
**Status:** Accepted
**Deciders:** Engineering team
**Chunk:** 0.2 — Architecture & API Contract

---

## Context

The backend must eventually support 13+ distinct domains:
admissions, beds, resources, departments, predictions, simulation, optimization,
knowledge (RAG), agents, identity, patients, alerts, and audit.

Two common structural approaches exist:

**Option A: Technical layering**
```
backend/app/
├── routes/         (all route handlers together)
├── services/       (all services together)
├── repositories/   (all repositories together)
├── models/         (all models together)
└── schemas/        (all schemas together)
```

**Option B: Domain-oriented modules**
```
backend/app/
├── api/v1/endpoints/
│   ├── admissions.py
│   ├── beds.py
│   └── ...
├── services/
│   ├── admissions.py
│   ├── beds.py
│   └── ...
├── repositories/
│   ├── admissions.py
│   ├── beds.py
│   └── ...
└── schemas/
    ├── admissions.py
    ├── beds.py
    └── ...
```

With 13+ domains, Option A results in files with thousands of lines and unclear
responsibility ownership. It also makes parallel development across domains difficult.

Option B keeps each domain's code co-located by concern. Adding or modifying the
`beds` domain means touching `api/v1/endpoints/beds.py`, `services/beds.py`,
`repositories/beds.py`, and `schemas/beds.py` — all clearly named, easy to find.

---

## Decision

Adopt **Option B: domain-oriented modules within each technical layer**.

The directory structure for each domain follows this pattern:

```
backend/app/
├── api/
│   └── v1/
│       ├── router.py              ← aggregates all endpoint routers
│       └── endpoints/
│           ├── health.py          ← ✅ implemented
│           ├── admissions.py      ← ⬜ future
│           ├── beds.py            ← ⬜ future
│           └── ...
├── core/
│   ├── config.py                  ← ✅ implemented
│   ├── exceptions.py              ← ✅ implemented
│   └── logging.py                 ← ✅ implemented
├── models/
│   ├── base.py                    ← ✅ implemented
│   └── ...                        ← ⬜ future domain models
├── repositories/
│   ├── base.py                    ← ⬜ future (common repo base class)
│   ├── admissions.py              ← ⬜ future
│   └── ...
├── schemas/
│   ├── common.py                  ← ✅ implemented
│   ├── admissions.py              ← ⬜ future
│   └── ...
└── services/
    ├── admissions.py              ← ⬜ future
    └── ...
```

Within each domain file:
- One domain = one file per layer
- Files stay focused (< 300 lines preferred)
- If a domain file grows too large, split by concern (e.g., `admissions_queries.py`)

---

## Consequences

### Positive
- Parallel development: team members work on different domain files without conflicts
- Easy to locate all code related to a domain
- New chunks simply add new files without modifying existing ones
- Each domain can be independently reviewed, tested, and deployed

### Negative / Trade-offs
- More files than a technical-layer-only approach
- Requires consistent naming discipline

### Mitigation
- Naming convention is enforced by this ADR and documented in `data-contracts.md`
- The `core/` directory remains for truly shared infrastructure
- The `schemas/common.py` file holds cross-cutting schemas only

---

## Alternatives Considered

### Single-file-per-layer (anti-pattern at scale)
Rejected: becomes unmaintainable as domains multiply. A single `services.py` with
13 domain service classes would be thousands of lines.

### Feature-folder (all files for a domain in one folder)
```
backend/app/domains/admissions/
    endpoints.py
    service.py
    repository.py
    schemas.py
```
Considered reasonable but rejected because it hides the layer structure.
The current approach keeps the layering visible in the directory tree while
still achieving per-domain file granularity.

---

## Related Decisions

- ADR-001: Layered architecture overview
- ADR-002: API layer contains no business logic
