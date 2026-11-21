# ADR-015: Bounded Agent Orchestration Engine, Lifecycle State Machine, and Evidence Grounding

## Context and Problem Statement

In Milestone 5, Chunk 5.1 established the first Hospital Operations Analyst Agent, and Chunk 5.2 standardized its tool contracts, machine-readable schemas, and permission-filtered discovery. However, agent execution was limited to a single pass without a formal orchestration lifecycle.

To support complex operational reasoning—such as comparing demand forecasts with hospital surge protocols, or cross-referencing simulation bottlenecks with MILP optimization explanations—the platform requires a centralized, explainable, and bounded Agent Orchestration Engine:

1. **Formal Execution Lifecycle:** Moving beyond arbitrary execution loops to a deterministic state machine that tracks transitions, prevents illegal state hops, and guarantees clean handling of terminal outcomes.
2. **Permission-Aware Coordination:** Tools must be validated and authorized before invocation, verifying caller RBAC and preventing duplicate or circular calls.
3. **Evidence Distinction & Grounding:** Tool outputs must be collected into structured evidence packages distinguishing observed historical data from statistical forecasts, hypothetical simulations, and algorithmic recommendations.
4. **Citation Verification:** Generated answers must cite verified source chunks or documents ingested during tool execution; hallucinated citations must be rejected.
5. **Auditable Execution Traceability:** Every step, state transition, and tool call duration must be preserved in an immutable trace queryable via API and visualizable in the frontend workbench.
6. **Strict Healthcare Safety Boundary:** The orchestration engine must enforce non-clinical boundaries, rejecting medical diagnosis or treatment requests immediately, and maintaining strict read-only guarantees.

---

## Decision Drivers

1. **State Machine Integrity:** Enforce valid progressions (`PENDING` -> `UNDERSTANDING` -> `PLANNING` -> `TOOL_SELECTION` -> `TOOL_EXECUTION` -> `EVIDENCE_REVIEW` -> `RESPONSE_GENERATION` -> `COMPLETED`) with terminal state immutability.
2. **Loop Prevention & Resource Bounds:** Guardrails for maximum steps (`max_steps`), tool call ceiling (`max_tool_calls`), and wall-clock execution timeouts (`timeout_seconds`).
3. **Domain Classification of Evidence:** Explicit distinction between `OBSERVED_DATA`, `FORECAST` (projections), `SIMULATION` (what-if scenarios), `OPTIMIZATION` (advisory allocations), and `KNOWLEDGE_POLICY` (hospital SOPs).
4. **Trace Auditing:** Full sequential trace queryable at `GET /api/v1/agents/traces/{execution_id}`.
5. **Full Backward Compatibility:** Seamless integration with existing `AgentRuntime` and UI components.

---

## Decision Outcome

Adopted a native Python-based, sequential Agent Orchestration Engine comprising:

### 1. Lifecycle State Machine (`OrchestrationStateTracker`)
Enforces transitions between 14 defined states:
- Active: `PENDING`, `UNDERSTANDING`, `PLANNING`, `TOOL_SELECTION`, `TOOL_EXECUTION`, `EVIDENCE_REVIEW`, `RESPONSE_GENERATION`.
- Terminal: `COMPLETED`, `REJECTED`, `FAILED`, `CANCELLED`, `TIMED_OUT`, `MAX_STEPS_REACHED`, `INSUFFICIENT_EVIDENCE`.
Every transition records source/target states, UTC timestamp, reason, and contextual metadata.

### 2. Evidence Collector (`AgentEvidenceCollector`)
Collects and categorizes evidence into `AgentEvidence` models:
- Category mapping: `OBSERVED_DATA`, `FORECAST`, `SIMULATION`, `OPTIMIZATION`, `KNOWLEDGE_POLICY`.
- Epistemic qualifiers: `is_projection`, `is_hypothetical`, `is_recommendation`.
- Evidence context budgeting: Clamps summary text if total evidence character count exceeds `max_chars` (default 12,000 characters).

### 3. Tool Execution Coordinator (`ToolExecutionCoordinator`)
- Re-verifies caller RBAC permissions prior to execution.
- Prevents infinite loops by blocking duplicate invocations of the same tool with identical arguments.
- Executes tools sequentially under per-tool timeout limits.
- Validates inputs and outputs via Chunk 5.2 standardized schemas.

### 4. Grounded Response Generator (`AgentResponseGenerator`)
- Synthesizes final answers grounded strictly in gathered evidence.
- Verifies citations against ingested evidence IDs, rejecting ungrounded or hallucinated markers.
- Adds domain caveats (e.g. model uncertainty, what-if hypothetical notices, administrative approval advisories).

### 5. API and Trace Persistence
- `POST /api/v1/agents/execute`: Executes operational inquiries through the complete orchestration lifecycle.
- `GET /api/v1/agents/traces/{execution_id}`: Retrieves the detailed execution trace, state machine history, and tool invocation log.

### 6. Frontend Workbench Integration
- `AgentTaskPlanPanel`: Visualizes objective, task type, strategic formulation, required evidence, and candidate tools.
- `AgentExecutionTimeline`: Renders an interactive state transition trail and step-by-step tool invocation log.
- `AgentProvenanceCards`: Displays gathered evidence with domain classification badges and provenance links.

---

## Healthcare Safety Boundary

In strict alignment with `AGENTS.md`:
- Purely operational decision intelligence.
- Immediate rejection of clinical queries (`check_clinical_scope`).
- All tools remain strictly `ExecutionType.READ_ONLY`.
- Consequential recommendations require human operational approval before action.
