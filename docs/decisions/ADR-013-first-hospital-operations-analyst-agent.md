# ADR-013: First Agent — Hospital Operations Analyst Agent & Bounded Agent Runtime

## Context and Problem Statement

Throughout Milestones 1 through 4, HospitalOps AI built individual, robust operational subsystems:
- Operational core: Admissions, bed management, equipment resources, and RBAC authentication (Milestone 1).
- Demand forecasting: Hero DMC daily admissions and NHSN HRD weekly ICU occupancy forecasting with ARIMA, Prophet, LSTM, and evaluation benchmarks (Milestone 2).
- Simulation & Optimization: What-if Monte Carlo simulations and MILP resource optimization with explainability (Milestone 3).
- Hospital Knowledge & RAG: Ingestion, semantic vector search, context retrieval, and grounded answer generation with deterministic citations (Milestone 4).

However, hospital operational leadership often faces composite questions that cut across these silos:
* "What is our ICU bed escalation protocol, and how does it compare against projected ICU admissions over the next two weeks?"
* "What did our high winter surge simulation predict for ventilator deficits, and does the recommended optimization plan resolve it?"
* "Why was surgery prioritized over ICU in the latest surge plan, and what hospital policy governed that constraint?"

To answer these inquiries, HospitalOps AI requires an **Agentic AI** layer that can understand complex operational tasks, plan multi-step investigation paths, invoke verified analytical subsystems, inspect structured results, and synthesize evidence-backed answers.

At the same time, operating in a hospital environment requires uncompromising safety guarantees:
1. **Clinical Boundary Enforcement:** In strict compliance with `AGENTS.md`, the agent must never diagnose patients, prescribe treatments, or offer clinical authority. Non-operational or medical queries must be screened and rejected before executing tools.
2. **Deterministic Bounded Execution:** The runtime must be bounded by strict maximum steps, maximum tool calls, timeout limits, and loop/duplicate detection to prevent runaway executions.
3. **Strict Read-Only Access:** The agent must only inspect existing records, policies, and forecasts. It must possess zero permissions to mutate live bed allocations, discharge patients, or modify hospital configurations.
4. **Transparent Auditability & Provenance:** Every tool invocation, parameter, duration, and output must be logged in a structured timeline (`tool_trace`), with clear source provenance separated by domain.

---

## Decision Drivers

1. **First Working Agent with Immediate Utility:** Implement `hospital_operations_analyst` as an operational decision-intelligence assistant rather than an abstract proof-of-concept.
2. **Modular & Extensible Runtime:** Establish a clean, decoupled architecture (`ToolRegistry`, `AgentRegistry`, `AgentRuntime`, `AgentPlanner`, `AgentPolicyEnforcer`) that can host additional specialized agents in Chunk 5.2 and beyond.
3. **Pluggable Multi-Provider Support:** Support both offline deterministic testing (via `MockLLMProvider`) and live model execution (via `OpenAICompatibleProvider`).
4. **Server-Side RBAC Enforcement:** Validate caller permissions before dispatching tool calls, ensuring that unauthorized callers cannot access restricted tools (e.g., `predictions.read`, `optimization.read`).
5. **Production-Ready Frontend Workbench:** Provide a dedicated `/agents` workbench featuring live readiness telemetry, multiline composer, suggested operational tasks, execution timeline, tool activity inspector, and structured provenance cards.

---

## Considered Options

1. **Option 1: Open-Ended Conversational Chatbot with Function Calling**
   - *Rejected:* General-purpose conversational chat lacks deterministic lifecycle states, does not guarantee read-only immutability, provides opaque reasoning traces, and risks hallucinating medical recommendations.

2. **Option 2: Heavy Third-Party Agent Frameworks (LangChain / CrewAI / AutoGPT)**
   - *Rejected:* Introduces heavy, frequently breaking external dependencies, opaque middleware layers, difficult-to-sandbox tools, and non-conforming error paradigms contrary to HospitalOps architectural principles.

3. **Option 3: Custom Bounded Agent Runtime with Typed Contracts & Policy Enforcer**
   - *Selected:* Built entirely on FastAPI, Pydantic, and existing HospitalOps domain services. Implements an explicit finite lifecycle, typed tool registry, server-side policy guards, duplicate call prevention, structured tool trace logging, and provenance isolation.

---

## Decision Outcome

Adopted **Option 3**:

### 1. Bounded Lifecycle State Machine
The agent execution follows an explicit state progression:
$$\text{RECEIVED} \longrightarrow \text{VALIDATING} \longrightarrow \text{SCOPE\_CHECK} \longrightarrow \text{PLANNING} \longrightarrow \text{EXECUTING\_TOOLS} \longrightarrow \text{EVALUATING\_RESULTS} \longrightarrow \text{GENERATING\_FINAL\_RESPONSE} \longrightarrow \text{COMPLETED}$$

If any safety violation, limit exhaustion, or clinical query is detected, execution stops deterministically with typed `StopReason` codes:
- `OUT_OF_SCOPE`: Clinical diagnosis/prescription inquiry blocked immediately.
- `NO_RELEVANT_TOOLS`: Non-operational inquiries outside the platform's capabilities.
- `MAX_STEPS_REACHED` / `MAX_TOOL_CALLS_REACHED`: Bounds exceeded.
- `TIMEOUT`: Execution window expired.
- `FINAL_ANSWER_READY`: Sufficient evidence assembled.

### 2. Typed Read-Only Tool Registry
The initial agent is equipped with 5 authorized read-only tools:
1. `search_hospital_knowledge`: Semantic vector retrieval across clinical policies, administrative guidelines, and equipment SOPs.
2. `answer_from_hospital_knowledge`: In-memory grounded RAG question answering with citation validation.
3. `get_existing_forecast`: Accesses Hero DMC daily admissions or NHSN HRD weekly ICU occupancy demand projections.
4. `get_simulation_result`: Inspects what-if Monte Carlo simulation outcomes, deficit periods, and trajectories.
5. `get_optimization_explanation`: Explains MILP solver plans, surge allocations, binding constraints, and trade-offs.

### 3. Policy & Safety Guards (`AgentPolicyEnforcer`)
- **Clinical Scope Screening:** Pre-generation keyword and intent matching catches diagnostic and prescribing queries, terminating execution with `AgentExecutionStatus.REJECTED` and `StopReason.OUT_OF_SCOPE` without invoking any tools.
- **RBAC Check:** Each tool defines its required permission (`knowledge.read`, `predictions.read`, `simulation.read`, `optimization.read`). Calls from unprivileged users are blocked with structured denial reasons.
- **Duplicate Call Prevention:** Tool calls with identical arguments to a previous step in the same run are rejected to prevent infinite loops.
- **Output Clamping & Tag Encapsulation:** Raw tool outputs are clamped to 3,500 characters and enclosed in safe `<tool_output>` tags before being passed to the planner.

### 4. REST API Endpoints (`/api/v1/agents`)
- `POST /api/v1/agents/run`: Submits an inquiry to an authorized agent with configurable options (`max_steps`, `max_tool_calls`, `timeout_seconds`).
- `GET /api/v1/agents/health`: Returns runtime readiness, active LLM model/provider, and registered tools.
- `GET /api/v1/agents`: Lists registered agents and their metadata.
- `GET /api/v1/agents/{agent_id}`: Inspects specific agent configuration, role, description, and available tools.

### 5. Frontend Agent Workbench (`/agents`)
- `AgentHeader`: Live telemetry badge (`Ready`, `Degraded`, `Unavailable`), model pill, tool count, and non-clinical disclaimer.
- `AgentTaskComposer`: Multi-line task textarea with character count, suggested task chips, and expandable execution controls.
- `AgentExecutionTimeline`: Visual step-by-step trace viewer with duration badges, status indicators, and expandable arguments/output drawers.
- `AgentAnswerPanel`: Synthesized response rendered via XSS-safe markdown with interactive `[S#]` citations, limitations, and human review advisories.
- `AgentProvenanceCards`: Categorized source cards grouped by Knowledge Documents, Demand Forecasts, What-if Simulations, and Optimization Plans.

---

## Consequences

### Positive
- Fully integrates the 4 previous milestones into a unified decision intelligence interface.
- Complete auditability: every agent run produces an exact, immutable timeline of steps, tool calls, and provenance links.
- Zero clinical risk: strict screening rejects non-operational queries upfront.
- Lightweight, self-contained architecture with zero heavy third-party framework dependencies.

### Invariants Maintained
- Agents are reasoning and orchestration engines only; they never replace deterministic solvers or ML models.
- All agent tools are strictly read-only and enforce server-side RBAC.
- Human review is required for consequential operational decisions.
- Real bounded agent: authentic multi-step execution is verified by unit and integration tests.
