# ADR-001 — Layered Architecture with Separated Concerns

**Date:** August 2026
**Status:** Accepted
**Deciders:** Engineering team
**Chunk:** 0.1 — Foundation

---

## Context

HospitalOps AI must combine several fundamentally different types of computation:

1. **LLM reasoning** — generating natural language analysis, orchestrating workflows
2. **Deterministic services** — calculations, validations, business rules
3. **ML inference** — statistical predictions from trained models
4. **Optimization** — constraint-based resource allocation
5. **Document retrieval** — searching hospital operational documents
6. **Persistence** — reliable, auditable storage of operational data

These are not interchangeable. Mixing them introduces serious risks:
- LLMs hallucinating database facts if given write access
- ML models being used where deterministic rules are needed
- Optimization algorithms being replaced by LLM guesses
- No clear boundary for clinical safety constraints

Additionally, HospitalOps AI operates in a healthcare-adjacent context. The system must be
**explainable**, **auditable**, and **safe**. Opaque, monolithic AI systems are inappropriate
for this domain.

---

## Decision

Adopt a **strict layered architecture** with separated concerns:

```
┌─────────────────────────────────────────────────────────┐
│  LLM / Agents                                           │
│  → reasoning and orchestration only                     │
│  → calls typed tools in the service layer               │
│  → never writes to database directly                    │
│  → never performs arithmetic directly                   │
└───────────────────────────┬─────────────────────────────┘
                            │ typed tool calls
                            ▼
┌─────────────────────────────────────────────────────────┐
│  Python Service Layer                                   │
│  → deterministic business logic                         │
│  → calculations, validations, transformations           │
│  → independently testable without LLMs                  │
└─────┬─────────────────────┬───────────────────────────-─┘
      │                     │
      ▼                     ▼
┌──────────────┐   ┌────────────────────────────────────┐
│  ML Models   │   │  Optimization Engine               │
│  → inference │   │  → constraint-based allocation     │
│  → numerical │   │  → explainable, deterministic      │
│    outputs   │   │  → separately testable             │
└──────────────┘   └────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│  Repository Layer                                       │
│  → all database reads and writes                        │
│  → abstracts MongoDB from business logic                │
│  → returns typed domain models                          │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  MongoDB (system of record)                             │
│  Redis (cache, transient state, events)                 │
└─────────────────────────────────────────────────────────┘

RAG runs separately:
┌─────────────────────────────────────────────────────────┐
│  Document Corpus → Embedding → Vector Search            │
│  → grounded context provided to LLM                     │
│  → LLM never fabricates document content                │
└─────────────────────────────────────────────────────────┘
```

---

## Rationale

### Testability
Each layer can be tested in isolation:
- Service layer: unit tests with no external dependencies
- Repository layer: integration tests against test MongoDB
- ML models: unit tests with synthetic data
- API layer: endpoint tests with mocked services
- Agent workflows: behavior tests with mocked tool responses

If all concerns were merged into agent logic, none of this would be possible.

### Reliability
Deterministic layers (services, optimization, repositories) behave predictably.
LLMs are probabilistic and can produce different outputs on identical inputs.
Keeping LLMs in the orchestration role and services in the calculation role means
that even if LLM behavior drifts, the calculations remain correct.

### Explainability
When a recommendation is produced:
- The optimization engine can explain which constraints drove the allocation
- The ML model can provide confidence intervals
- The service layer can show exactly what data was used
- The LLM can articulate the reasoning in natural language

This layering makes the explanation chain traceable.

### Maintainability
Each layer can be updated independently:
- ML model upgraded without touching agent logic
- Optimization algorithm improved without touching API contracts
- LLM provider swapped without touching service layer
- Database schema evolved through repository layer only

### Safety
Healthcare operations require that consequential recommendations be:
1. Grounded in real data (not LLM hallucinations)
2. Explainable (which data, which rules, which model)
3. Auditable (full trace of decision chain)
4. Subject to human review (especially for resource changes)

The layered architecture enforces these properties structurally, not just by convention.

---

## Consequences

### Positive
- Clear ownership boundaries for each component
- Safe to introduce LLMs without fear of data corruption
- Each component can be optimized, replaced, or scaled independently
- Testing is straightforward at every layer
- Compliance and audit requirements are easier to satisfy

### Negative / Trade-offs
- More initial structure than a simple monolith
- Requires discipline to maintain layer boundaries
- Some features require coordination across multiple layers

These trade-offs are considered acceptable given the healthcare-adjacent context and
the long-term maintainability requirements.

---

## Compliance

All future chunks must respect this architecture decision.

If a proposed feature requires crossing these boundaries, an ADR must be written
to justify the exception and document the mitigations.

---

## Related Decisions

- [ADR-002](ADR-002-api-service-separation.md): API layer contains no business logic
- [ADR-003](ADR-003-domain-modular-backend.md): Domain-oriented modular backend architecture
- [ADR-004](ADR-004-agent-tool-service-architecture.md): Agent → Tool → Service architecture
- [ADR-005](ADR-005-utc-and-traceability.md): UTC timestamps and request correlation IDs
