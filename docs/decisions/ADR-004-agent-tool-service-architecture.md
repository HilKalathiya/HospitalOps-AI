# ADR-004 — Agent → Tool → Service Architecture

**Date:** August 2026
**Status:** Accepted
**Deciders:** Engineering team
**Chunk:** 0.2 — Architecture & API Contract

---

## Context

HospitalOps AI will include an LLM-powered agent orchestration layer. Agents must be
able to act on hospital operational data — querying bed availability, triggering simulations,
fetching forecasts, retrieving policies — to produce grounded operational recommendations.

The question is: **how should agents access data and execute operations?**

Three options were considered:

### Option A: Agents query MongoDB directly

Agents are given a database connection and query collections themselves.

Problems:
- No business-rule validation (e.g., checking permissions, enforcing domain invariants)
- No consistent audit trail (agent queries are outside the service layer)
- Testing requires a live database
- Business logic leaks into LLM prompts ("check if is_deleted=false")
- Any query mistake by an LLM prompt produces silent data corruption

### Option B: Agents call internal HTTP API endpoints

Agents make HTTP requests to `http://localhost:8000/api/v1/beds` to get data.

Problems:
- Network round-trip overhead for in-process operations
- Agent is coupled to HTTP transport layer
- Authentication becomes a circular problem (who authenticates the agent?)
- Complex to test

### Option C: Agents call typed Python tool functions backed by services

Agents are given a set of typed tool functions. Each tool:
- Has a clear name, description, and typed input/output schemas
- Internally calls an application service method
- Returns a structured result the agent can reason about

This keeps the service layer as the single point of authority for business logic,
regardless of whether the caller is a human via HTTP or an agent via tool calling.

---

## Decision

Adopt **Option C: Agent → Tool Function → Application Service**.

```
Agent (LLM)
    ↓  selects tool based on task
Tool function  (typed Python function, registered with the agent framework)
    ↓  validates input, calls service
Application Service  (same service used by REST API)
    ↓
Repository / ML / Simulation / Optimization
    ↓
Typed result
    ↓
Tool function returns result to agent
    ↓
Agent reasons about result
```

### Tool function contract

Every agent tool must implement:
- `name: str` — identifier used by the LLM
- `description: str` — natural language description for LLM tool selection
- `input_schema` — Pydantic model defining required inputs
- `output_schema` — Pydantic model defining the return structure
- `permissions: list[str]` — roles allowed to invoke this tool
- An `async def execute(input) -> output` method that calls a service

### What agents ARE allowed to do via tools
- Read operational state (beds, admissions, resources)
- Read forecasts and predictions
- Trigger simulations (read-only computation)
- Trigger optimization (produces a pending recommendation, not executed)
- Search knowledge base (RAG retrieval)
- Create pending recommendations for human review

### What agents are NOT allowed to do
- Write directly to MongoDB
- Execute recommendations without human approval
- Call other agents recursively without orchestrator oversight
- Access patient clinical data

---

## Consequences

### Positive
- Agents and API consumers use identical business logic and validation
- Agent tool tests can mock the service layer (fast, isolated tests)
- All agent data access is auditable through the service layer
- Business logic evolves in one place; agent prompts don't need to replicate it
- LLM provider can be swapped without touching service layer
- Tool permissions are enforceable at the service level

### Negative / Trade-offs
- Requires writing tool wrapper functions (thin but real code)
- Agent orchestration framework must support Python function tool calling
- Tool schema maintenance is additional overhead

### Mitigation
- Tool functions are intentionally thin (< 20 lines typically)
- Tool input/output schemas reuse the same Pydantic models as the REST API
- The overhead is justified by the safety, testability, and audit benefits

---

## Alternatives Considered

### Direct database access (Option A)
Rejected: violates safety boundary, breaks audit trail, untestable, LLM hallucination risk.

### Internal HTTP calls (Option B)
Rejected: transport overhead, auth complexity, circular dependencies.

### LangChain / LangGraph tool definitions with their own data access
Partially acceptable for future framework selection, but the data access pattern
(service layer, not direct DB) must be enforced regardless of which framework is chosen.

---

## Related Decisions

- ADR-001: Layered architecture overview
- ADR-002: API layer contains no business logic
- ADR-003: Domain-modular backend organisation
