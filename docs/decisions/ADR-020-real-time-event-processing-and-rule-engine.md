# ADR-020: Real-Time Event Processing & Operational Rule Engine

## Status
**Accepted & Implemented (Milestone 6, Chunk 6.2)**

---

## 1. Context and Problem Statement

HospitalOps AI is an operational decision-support platform designed to assist hospital administrators with capacity planning, resource optimization, forecasting, and policy retrieval. Milestones 6.1 and 6.1.1 delivered an immutable, auditable, and resilient operational event infrastructure based on six canonical event categories.

While events record what has occurred across hospital operations, raw events alone do not determine which operational thresholds, surge conditions, or capacity constraints require operational attention. To bridge real-world telemetry with operational intelligence, the platform requires an event-processing and operational rule evaluation subsystem.

The core design principle governing this architecture is:
> **Events detect what happened. Rules determine what matters. Agents explain what it means. Humans retain authority over operational decisions.**

This Architecture Decision Record (ADR) codifies the operational boundaries, declarative AST condition language, epistemic safety controls, at-least-once distributed processing semantics, and deduplicated evaluation persistence for the HospitalOps AI Rule Engine.

---

## 2. Core Architectural Decisions

### 2.1 Non-Clinical Safety Boundary & Decision Authority Invariant
HospitalOps AI strictly separates operational management from clinical care. The Rule Engine operates entirely within non-clinical boundaries:
1. **Zero Clinical Diagnostics or Prescriptions:** The rule engine evaluates operational telemetry (e.g., bed occupancy rates, resource utilization, equipment turnaround time, wait lists). It never evaluates clinical parameters, patient vitals, medical diagnoses, medication regimens, or clinical risk scores.
2. **Explicit AST Field Inspection:** Field paths referencing clinical domains (e.g. `patient.diagnosis`, `patient.vitals`, `clinical_score`, `prescription`) are statically rejected during condition schema validation.
3. **Operational Findings Only:** Every evaluation record produced by rule evaluation specifies `requires_human_review = True`. The engine generates operational findings and evidence summaries; it never acts with clinical or autonomous medical authority.
4. **Zero Operational Database Mutations:** The rule engine is purely an evaluation and finding-generation engine. It never mutates operational database collections (`beds`, `admissions`, `patients`, `resources`, `staffing`).

### 2.2 Declarative Condition Specification (No Arbitrary Code Execution)
To prevent code-injection vulnerabilities, unpredictable runtime behavior, and nondeterministic evaluation:
1. **Safe Condition Grammar:** Rule conditions are expressed strictly as declarative JSON-serializable syntax trees (`SingleCondition` and `CompositeCondition`).
2. **Strictly No `eval()` / `exec()`:** The condition evaluator executes pure Python AST-like tree traversal without string code evaluation, runtime imports, or dynamic function execution.
3. **Supported Relational & Membership Operators:**
   - Relational: `eq`, `neq`, `gt`, `gte`, `lt`, `lte`
   - Membership: `in`, `not_in`
   - Existence: `exists`, `does_not_exist`
4. **Bounded Complexity:** Condition trees are bounded to a maximum nesting depth of 3 levels and a maximum of 10 conditions per composite block to prevent pathological evaluation latency.
5. **Strict Data Missing Handling:** When an event lacks the specified field, the evaluator explicitly returns `RuleEvaluationStatus.DATA_MISSING`. Missing numeric fields are **never** silently coerced to `0`, `False`, or empty strings.

### 2.3 Epistemic Category Filtering & Event Scope Isolation
The HospitalOps AI event architecture defines six canonical categories with distinct epistemic weights:
- `OBSERVED_OPERATIONAL`: Real-world operational telemetry.
- `DERIVED_OPERATIONAL`: Deterministically computed metrics.
- `FORECAST_OUTPUT`: Probabilistic predictions.
- `SIMULATION_OUTPUT`: Hypothetical what-if scenarios.
- `OPTIMIZATION_OUTPUT`: Prescriptive resource allocations.
- `AGENT_EXECUTION`: Autonomous multi-agent coordination traces.

**Epistemic Boundary Enforcement:**
Each `OperationalRule` explicitly declares `allowed_categories: list[EventCategory]`. A capacity alert rule configured for real-time ward telemetry will only evaluate `OBSERVED_OPERATIONAL` events. Synthetic simulation scenarios or future forecasts cannot accidentally trigger real-time operational capacity findings unless a rule explicitly permits multi-category evaluation.

Rules with simulated or illustrative scopes must set `is_illustrative = True` or match against explicit facility boundaries (`facility_id`).

### 2.4 Time-Window Aggregations
For operational patterns requiring temporal context (e.g., occupancy exceeding 90% for 3 consecutive readings, or admission surge exceeding 20 in 4 hours):
- Rules support `TimeWindowConfig` defining `window_duration_minutes` (up to 1,440 minutes / 24 hours), `aggregation_type` (`COUNT`, `MAX`, `MIN`, `AVG`, `LATEST`), and `min_events` (default 1).
- Events within the sliding window are chronologically sorted and evaluated with deterministic evidence referencing.

### 2.5 At-Least-Once Distributed Consumer with Crash Recovery
The `OperationalEventConsumer` operates over MongoDB persistence with distributed coordination:
1. **Lease Claiming via Atomic Find-and-Modify:** Worker nodes claim batches of pending events by atomically transitioning their status from `PENDING` to `PROCESSING` with a lease expiration timestamp (`lease_expires_at = now() + lease_duration`).
2. **Crash Recovery & Heartbeats:** If a worker crashes mid-batch, stale processing records with `lease_expires_at < now()` are automatically reclaimed by healthy workers upon the next polling cycle.
3. **Exponential Backoff & Quarantine:** Failed event evaluations increment `attempts`. If failures exceed `max_retries` (default 3), the record transitions to `QUARANTINED` with the recorded `last_error` for administrator inspection.
4. **Graceful Shutdown:** The consumer respects cancellation signals, completing in-flight evaluation batches and releasing or finishing claims before terminating.

### 2.6 Deduplicated, Immutable Evaluation Findings
Rule evaluations are persisted in the `rule_evaluations` collection:
- **Deterministic Identity:** `evaluation_id = sha256(rule_id:rule_version:sorted_source_event_ids)[:24]`.
- **Atomic Idempotency:** A unique index on `evaluation_id` guarantees that re-processing the same event against the same rule version is completely idempotent; duplicate insert attempts are silently absorbed without error or duplicate finding generation.
- **Full Evidence Provenance:** Every finding includes `source_event_ids`, an `evidence` dictionary of observed field values, and an explainable operational rationale.

### 2.7 Rule Versioning & Multi-Tenant RBAC
1. **Immutable Rule Versioning:** Updates to rule conditions, thresholds, or scopes do not mutate existing versions in place. The active rule version is incremented, and prior versions are archived in `operational_rule_versions` to ensure historical evaluation auditability.
2. **Access Control:**
   - `rules.manage`: Required to create, update, or toggle rules (assigned to `Role.ADMIN` and `Role.OPERATIONS_MANAGER`).
   - `rules.read`: Required to list rules and inspect evaluation findings (assigned to `Role.ADMIN`, `Role.OPERATIONS_MANAGER`, and `Role.DOCTOR`).
3. **Facility Isolation:** Non-admin users are automatically scoped to their assigned `facility_id` across rule definition and evaluation query endpoints.

---

## 3. Consequences and System State

### Positive Consequences
- **Safe & Predictable:** Non-clinical decision support is maintained; zero dynamic code execution risk.
- **Decoupled Architecture:** Subsystems emit events; the rule engine evaluates them asynchronously without blocking operational services.
- **Complete Traceability:** Operational findings link directly to the underlying event telemetry that triggered them.
- **Resilient:** Worker node crashes recover automatically; retry exhaustion isolates problematic events into quarantine without stopping pipeline flow.

### Negative Consequences / Trade-Offs
- Evaluating multi-event time windows requires chronological range queries against the event repository.
- Unique compound hashing requires consistent sorting of event IDs to ensure idempotent evaluation identity.

---

## 4. Compliance and Verification
- **Test Coverage:** Full test suites for contracts, evaluator AST, consumer lease recovery, and REST API.
- **Acceptance Invariants:** Strict enforcement of `requires_human_review = True`, no mutations to core clinical/operational collections, and strict non-admin tenant isolation.
