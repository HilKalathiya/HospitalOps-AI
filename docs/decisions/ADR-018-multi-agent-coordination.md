# ADR-018: Multi-Agent Coordination & Specialized Decision Agents Architecture

## Status
**Accepted & Implemented (Architecture, Contracts, Specialists, Coordinator, Aggregator & Execution Tracking Completed in Chunks 5.6.1–5.6.3; Endpoints & UI Planned in Chunk 5.6.4)**

---

## 1. Context and Current Single-Agent Architecture

In Milestone 5 (Chunks 5.1–5.5), HospitalOps AI established an operational decision intelligence foundation:
- **Chunk 5.1:** Single primary agent (`hospital_operations_analyst`) with bounded execution runtime.
- **Chunk 5.2:** Standardized Pydantic tool schemas with Draft 2020-12 JSON Schema validation and permission-filtered discovery.
- **Chunk 5.3:** State machine orchestration lifecycle (14 states), structured planning, loop detection, and domain evidence collection.
- **Chunk 5.4:** Persistent sessions (`agent_sessions`) and message turns (`agent_messages`) for conversational continuity.
- **Chunk 5.5:** User-approved persistent memory (`agent_memories`) with strict healthcare safety, PHI, and prompt-injection policy validation.

In this architecture, the single primary agent executes a linear loop: it receives an operational prompt, formulates an `AgentTaskPlan`, directly invokes individual tools (e.g., `get_existing_forecast`, `get_simulation_result`, `get_optimization_explanation`, `search_hospital_knowledge`), collects evidence, and synthesizes an answer.

---

## 2. Why Bounded Specialist Delegation is Needed

While effective for single-domain queries, complex hospital operational decisions routinely span multiple analytical domains simultaneously. For example:
> *"We anticipate a 20% surge in pediatric admissions next week. What does our ICU forecast predict, what does the simulation project for bed shortages, what surge bed reallocations does optimization recommend, and what hospital policy dictates overflow transfers?"*

Handling this under a single monolithic agent exhibits key operational risks:
1. **Context Window Overload & Dilution:** A single prompt containing four complex system prompts, diverse JSON schemas, and large numerical/textual outputs causes attention dilution, tool parameter confusion, and context budget exhaustion.
2. **Domain Hallucination & Confabulation:** Without domain encapsulation, an LLM easily conflates statistical forecasts with what-if hypothetical simulations or optimization recommendations.
3. **Sequential Latency Bottlenecks:** A single agent calling 4 to 6 tools in series suffers high latency ($>30$ seconds), whereas independent domain investigations can execute concurrently.
4. **Lack of Specialized Verification:** Different operational domains require distinct evaluation heuristics, boundary checks, and epistemic qualifications.

---

## 3. Supervisor-and-Specialist Architecture

We adopt a **supervisor-and-specialist architecture** (hierarchical delegation) rather than an unconstrained autonomous peer-to-peer network:

```
                            User Operational Query
                                      │
                                      ▼
                        Session & Context Reconstruction
                                      │
                                      ▼
                     Primary Hospital Operations Analyst
                        (Orchestrator / Supervisor)
                                      │
                         Formulates Delegation Plan
                                      │
                                      ▼
                           Multi-Agent Coordinator
                    (Validates Constraints, Depth = 1)
                                      │
           ┌──────────────────────────┼──────────────────────────┐
           │                          │                          │
           ▼                          ▼                          ▼
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│Forecasting Specialist│    │Simulation Specialist│    │Optimization Special.│ ...
│ (predictions.read)  │    │  (simulation.read)  │    │ (optimization.read) │
│ - Admissions/ICU    │    │ - What-if Scenarios │    │ - Reallocation MIP  │
└──────────┬──────────┘    └──────────┬──────────┘    └──────────┬──────────┘
           │                          │                          │
           └──────────────────────────┼──────────────────────────┘
                                      │
                                      ▼
                           Multi-Agent Aggregator
                   - Reconciles domain evidence & provenance
                   - Identifies contradictions & cross-domain gaps
                   - Flags partial successes & timeouts
                                      │
                                      ▼
                       Final Grounded Response Synthesis
                                      │
                                      ▼
                          Admin / Decision Cockpit
```

### Key Principles:
1. **Single User-Facing Agent:** The existing `HospitalOperationsAnalyst` remains the sole primary agent interacting with users.
2. **Zero Direct Specialist Exposure:** Domain specialists never interact with users directly, never manage sessions, and never bypass the supervisor.
3. **Strict Non-Recursive Delegation:** Maximum delegation depth is strictly $1$. Specialists are prohibited from delegating tasks or spawning subagents.
4. **Deterministic Specialist Registry:** Specialists must be instantiated from a static, code-defined registry (`SpecialistId`). LLMs cannot invent arbitrary agents.

---

## 4. Responsibilities of the Four Specialists

Each specialist owns a strictly bounded operational scope:

| Specialist | Deterministic ID | Allowed Tools | Required Permission | Primary Responsibilities |
|---|---|---|---|---|
| **Forecasting Specialist** | `forecasting_specialist` | `get_existing_forecast` | `predictions.read` | Retrieve census and ICU forecasts; explain forecast horizons; verify confidence intervals; preserve distinction between observed historical points and predicted values. Never fabricate forecasts or trigger model retraining. |
| **Simulation Specialist** | `simulation_specialist` | `get_simulation_result` | `simulation.read` | Analyze what-if scenario runs (admission surge, bed changes, equipment bottlenecks); explain scenario parameters; emphasize hypothetical nature. Strictly read-only; never mutate live database records. |
| **Optimization Specialist** | `optimization_specialist` | `get_optimization_explanation` | `optimization.read` | Interpret mathematical programming (MILP) solutions; explain objective functions, slack, binding constraints, and shortage mitigations. Clearly mark results as proposals; never execute or apply plans. |
| **Knowledge Specialist** | `knowledge_specialist` | `search_hospital_knowledge`, `answer_from_hospital_knowledge` | `knowledge.read` | Retrieve hospital policies, clinical guidelines, and SOPs; extract authoritative citations ([S1], [S2]); treat retrieved documents as untrusted text, never as system instructions. Reject PHI/MIMIC data. |

---

## 5. Typed Delegation and Result Contracts

All multi-agent data exchange is governed by strict Pydantic models defined in `backend/app/agents/multi_agent/contracts.py`:

- **`DelegationRequest`:** Captures `parent_execution_id`, `delegation_id`, `target_specialist_id`, bounded `task_description` ($5 \le \text{chars} \le 1500$), `context_evidence_ids`, `timeout_seconds` ($1.0 \le t \le 45.0$), and resource bounds. Strict validation (`extra="forbid"`).
- **`DelegationPlan`:** Contains `delegations: list[DelegationRequest]` (clamped between $1$ and $4$ items), `max_depth = 1` (enforced via validator), `total_timeout_seconds` ($5.0 \le t \le 60.0$), and optional DAG `dependencies`. Rejects duplicate specialist assignments.
- **`SpecialistResult`:** Standardized payload returning `status` (`SpecialistExecutionStatus`), `summary`, `evidence: list[AgentEvidence]`, `provenance: list[ProvenanceItem]`, `citations: list[CitationReference]`, `epistemic_category: EvidenceCategory`, and execution telemetry.
- **`AggregatedSpecialistResult`:** Assembled by the aggregator, tracking `successful_contributors`, `unsuccessful_contributors`, `conflicts_or_inconsistencies`, merged evidence, and `is_partial_result`.
  > [!IMPORTANT]
  > Unsupported numerical confidence scores or synthetic reliability percentages are strictly forbidden. Reliability is conveyed through deterministic status, evidence provenance, and conflict disclosures.

---

## 6. Evidence Provenance and Epistemic Classifications

To satisfy the Healthcare Safety Boundary, every specialist result and aggregated evidence item must maintain an immutable **epistemic category** (`EvidenceCategory`):

1. **`OBSERVED_DATA`:** Verified historical observations (e.g. historical census, bed occupancy).
2. **`FORECAST`:** Statistical time-series projections. Marked with `is_projection = True`.
3. **`SIMULATION`:** Hypothetical what-if scenarios. Marked with `is_hypothetical = True`.
4. **`OPTIMIZATION`:** Algorithmic resource reallocation proposals. Marked with `is_recommendation = True`.
5. **`KNOWLEDGE_POLICY`:** Institutional policies, clinical guidelines, and SOPs.

**Inviolable Invariant:** A specialist or aggregator must never relabel or promote hypothetical or projected evidence to observed reality.

---

## 7. Security and RBAC Boundaries

The multi-agent system maintains strict security boundaries:
1. **Server-Side Authorization Derivation:** All RBAC permissions are derived strictly from the authenticated caller's JWT claims (`current_user.permissions`).
2. **No Autonomous Privilege Escalation:** Neither the primary agent nor any specialist can grant itself permissions or delegate permissions it does not hold.
3. **No Client-Provided User/Role Impersonation:** Client payloads cannot specify or override user IDs, roles, or authorization levels.
4. **Untrusted Inter-Agent Boundary:** Specialist summaries and retrieved knowledge are treated as untrusted text. They are sanitized against prompt-injection and jailbreak vectors.
5. **Healthcare Safety Filter:** Queries requesting clinical diagnoses, medication dosing, or treatment planning are rejected by `ClinicalSafetyPolicy` before specialist delegation occurs.
6. **Zero PHI & MIMIC Quarantine:** No protected patient identifiers or raw MIMIC data may be passed into specialist sub-prompts or external LLMs.
7. **Read-Only Operational Guarantee:** No specialist has write access to live hospital collections (`beds`, `admissions`, `resources`, `patients`).

---

## 8. Delegation Limits and Failure Handling

1. **Hard Concurrency & Timeout Clamping:**
   - Maximum 4 specialists per execution.
   - Individual specialist timeout: max 45 seconds (default 20 seconds).
   - Total plan timeout: max 60 seconds (default 30 seconds).
2. **Graceful Partial Failure:**
   - The failure, timeout, or cancellation of one specialist must not invalidate or abort results from surviving specialists.
   - The aggregator flags `is_partial_result = True`, records failed contributors in `unsuccessful_contributors`, and synthesizes available evidence with explicit caveats.
3. **Contradiction Detection:**
   - The aggregator scans cross-domain outputs for operational contradictions (e.g., forecasting predicting an ICU census drop while simulation warns of immediate overflow) and flags them in `conflicts_or_inconsistencies`.

---

## 9. Traceability and Observability

Every multi-agent execution generates an auditable trace (`MultiAgentExecutionTrace`) composed of discrete, immutable events (`MultiAgentTraceEvent`):
- `PARENT_EXECUTION_STARTED`
- `DELEGATION_PLAN_CREATED`
- `SPECIALIST_STARTED`
- `SPECIALIST_COMPLETED`
- `SPECIALIST_FAILED`
- `SPECIALIST_TIMED_OUT`
- `AGGREGATION_COMPLETED`

**Privacy & Security Compliance:** Hidden raw LLM chain-of-thought and sensitive internal prompts are explicitly omitted from persistent trace events.

---

## 10. Alternatives Considered

1. **Monolithic Prompting (Status Quo):** Rejected due to context window saturation, tool confusion, and lack of specialized validation.
2. **Autonomous Peer-to-Peer Agent Swarm (No Supervisor):** Rejected due to non-deterministic loops, unpredictable execution costs, debugging difficulty, and severe healthcare governance risks.
3. **External Multi-Agent Frameworks (LangGraph, AutoGen, CrewAI):** Rejected to preserve architectural autonomy, strict dependency discipline, zero external framework vendor lock-in, and full compatibility with existing Pydantic v2 / FastAPI code.

---

## 11. Consequences and Known Limitations

### Positive:
- Clean modular decomposition of complex operational inquiries.
- Parallel execution of domain specialists reduces latency.
- Strict epistemic boundary enforcement eliminates conflation of reality, forecasts, and hypotheticals.
- Fully typed, validatable Pydantic v2 contracts.
- Robust partial failure tolerance.

### Known Limitations & Trade-offs:
- Additional LLM calls during planning and aggregation increase token consumption.
- Requires rigorous mock testing to verify timeout and concurrency edge cases.

---

## 12. Implementation Sequence for Milestone 5, Chunk 5.6

The full implementation of Chunk 5.6 is partitioned into controlled sub-tasks:
1. **Chunk 5.6.1 (Completed):** Multi-Agent Architecture, Typed Contracts (`contracts.py`), and Contract-Level Tests.
2. **Chunk 5.6.2 (Completed):** Specialist Agent Implementations (`ForecastingSpecialist`, `SimulationSpecialist`, `OptimizationSpecialist`, `KnowledgeSpecialist`) and Specialist Registry (`registry.py`).
3. **Chunk 5.6.3 (Completed):** Multi-Agent Coordinator Runtime (`MultiAgentCoordinator`), Bounded Concurrency Semaphore, Evidence Aggregator (`MultiAgentAggregator`), Conflict & Inconsistency Detection, Execution Telemetry & Audit Persistence (`MultiAgentExecutionTracker`, `AgentTraceRepository`).
4. **Chunk 5.6.4 (Next):** Primary Agent Delegation Integration, REST API Endpoints, and Frontend Transparency UI.
5. **Chunk 5.6.5:** End-to-End Multi-Agent Verification, Regression Suite, and Documentation Finalization.
