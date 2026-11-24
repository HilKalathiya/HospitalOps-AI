# ADR-019: Foundational Event-Driven Architecture & Event System

## Status
**Accepted & Hardened (Milestone 6.1.1 Hardening & Reliability Audit Complete)**

---

## 1. Context and Problem Statement

HospitalOps AI is an operational decision-support platform designed to assist hospital administrators with capacity planning, occupancy forecasting, scenario simulation, resource allocation, and policy retrieval. Through Milestones 1–5, the platform implemented:
- Deterministic backend services (admissions, beds, resources).
- Statistical and deep-learning forecasting models (ARIMA, Prophet, LSTM).
- Mixed-integer programming optimization and Monte Carlo simulation.
- ChromaDB vector search and retrieval-augmented generation (RAG).
- Multi-agent coordination runtime with domain specialists (Chunk 5.6).

However, communication between subsystems remained predominantly synchronous and request-driven. When bed capacity changes, forecasts complete, or multi-agent investigations finish, downstream components lack an authoritative, decoupled notification stream. 

Milestone 6 initiates real-time operational event intelligence. Before rule evaluation, threshold alerts, or automated workflows can be built, the platform requires a **reliable, auditable, extensible foundational event system**.

Milestone 6.1.1 conducted a comprehensive architecture, security, and reliability hardening audit of the foundational event system to ensure zero silent data loss, deterministic idempotency under concurrency, multi-layer PHI scrubbing, authenticated actor binding, and strict non-admin facility isolation.

---

## 2. Core Architectural Decisions

### 2.1 Separation of Concerns & Healthcare Safety Invariant
The event system adheres strictly to the HospitalOps AI Engineering Constitution:
- **Events represent past facts, never commands:** An event records that a state transition or analytical run has already completed (e.g., `operations.capacity.updated`, `forecasting.completed`). Events never order clinical actions or autonomously mutate clinical state.
- **Strictly Operational:** No clinical diagnostic or prescriptive clinical data is captured in event envelopes or payloads. All operational recommendations and alerts retain `requires_human_review = True`.
- **Append-Only Event Store:** The persistence layer (`operational_events` collection) is strictly immutable and append-only. No update or delete operations are exposed on the event repository or API.
- **No Downstream Execution Side-Effects in Foundation:** In Milestones 6.1 and 6.1.1, the event system is strictly an ingest, persistence, and audit query pipeline. It triggers no autonomous downstream agent runs, rule engines, or database mutations.

### 2.2 Standardized Event Envelope (`OperationalEvent`)
Every operational event follows a uniform, strictly validated Pydantic v2 envelope:
```
OperationalEvent
├── event_id: str (UUIDv4 or prefixed, e.g. evt_...)
├── event_type: EventType (e.g. operations.capacity.updated)
├── category: EventCategory (6 canonical categories)
├── occurred_at: datetime (UTC, max 5-minute future skew allowance)
├── recorded_at: datetime (UTC server ingestion timestamp)
├── facility_id: str (Authoritative multi-tenant boundary)
├── source: str (Subsystem identifier, e.g. hospitalops.capacity_service)
├── entity_type: EntityType (facility | department | ward | bed | forecast | ...)
├── entity_id: str (Identifier of affected operational entity)
├── correlation_id: str (Traceability across workflows/requests)
├── causation_id: str | None (Upstream event/message that triggered this event)
├── actor_id: str | None (Authenticated user or system actor, bound from JWT)
├── payload_version: str (Semantic version of payload schema, e.g. "1.0")
├── payload_hash: str (Deterministic SHA-256 digest of canonical JSON payload)
├── payload: BasePayload (Type-checked against EVENT_PAYLOAD_MAP)
└── metadata: dict[str, Any] (Supplementary unindexed operational context)
```

Extra fields on either envelope or payload are strictly forbidden (`extra="forbid"`). Payloads are bounded to a maximum size of 64 KB, and automatic inspection detects and rejects potential PII/PHI (such as SSN patterns, emails, phones, or sensitive patient keys).

### 2.3 Event Classification & Epistemic Boundaries
The platform defines **6 canonical event categories** with strict epistemic boundaries:
1. `OBSERVED_OPERATIONAL`: Directly observed real-world telemetry and operations facts (e.g. bed status changes, capacity metrics).
2. `DERIVED_OPERATIONAL`: Deterministically computed calculations from raw observations (e.g. occupancy rate threshold crossings, admissions surges).
3. `FORECAST_OUTPUT`: Probabilistic model forecasts and inferences (ARIMA, Prophet, LSTM) with confidence intervals.
4. `SIMULATION_OUTPUT`: Hypothetical what-if discrete-event simulation projections.
5. `OPTIMIZATION_OUTPUT`: Algorithmic resource allocation recommendations and surge protocol plans.
6. `AGENT_EXECUTION`: Multi-agent operational investigation and coordination execution traces.

For backward compatibility, legacy categories (`OPERATIONAL_FACT`, `ANALYTIC_PROJECTION`, `SYSTEM_RECOMMENDATION`) are mapped transparently to their canonical counterparts.

### 2.4 Deterministic Payload Hashing & Checksum Integrity
- **Payload Content Integrity Checksum:** The `payload_hash` field is computed using deterministic JSON normalization (`sort_keys=True`, `separators=(",", ":")`, `ensure_ascii=True`, `default=str`) and SHA-256.
- **Application-Level Checksum vs. Cryptographic WORM:** The payload hash serves as an application-level duplicate detection and content integrity checksum. It is validated server-side; if a client attempts to supply a tampered or mismatched `payload_hash`, the event is rejected with `EventValidationError`. It does not claim database-level cryptographic WORM or hardware tamper-resistance.
- **Concurrent Idempotency & Conflict Detection:**
  1. If an event arrives with an existing `event_id` and an identical `payload_hash`, it is recognized as an idempotent retransmission. The existing event is returned with `is_duplicate = True`.
  2. If an event arrives with an existing `event_id` and a differing `payload_hash`, an `EventConflictError` (HTTP 409) is raised.
  3. Under concurrent race conditions (`duplicate key error` on MongoDB unique index `event_id`), the repository recovers gracefully by re-reading the stored document and determining whether it was identical (idempotent) or conflicting.
  4. Cross-tenant ID collisions: If an incoming event has the same `event_id` as an existing event belonging to a different `facility_id`, an `EventConflictError` is raised without leaking tenant hash details.

### 2.5 Authoritative Persistence vs. Explicit In-Memory Test Mode
- **Zero Silent Fallback in Production:** Production environments require an authoritative MongoDB database. Silent in-memory fallback is strictly prohibited (`allow_in_memory: bool = False` by default). Instantiating `OperationalEventRepository(db=None)` raises `EventPersistenceError` fast at startup.
- **Dedicated Test Repository:** An explicit `InMemoryOperationalEventRepository` subclass (with `allow_in_memory=True` and thread/asyncio lock synchronization) is provided exclusively for unit and integration testing.
- **Durability Health Endpoint:** A dedicated `GET /api/v1/events/health` endpoint exposes durability status (`is_durable: true/false`), storage mode (`MONGODB` vs `IN_MEMORY_TEST`), and catalog type counts to operations monitoring.

### 2.6 Authentication, RBAC & Facility Isolation
- **Actor Identity Binding:** In `POST /api/v1/events/publish`, the `actor_id` field is bound server-side from the authenticated JWT token (`current_user.user_id`). Client attempts to spoof an arbitrary `actor_id` are overwritten with the verified token identity.
- **Non-Admin Facility Pinning:** Non-system-admin users are pinned to their assigned `facility_id`. If a non-admin client attempts to publish an event under an unassigned `facility_id`, the request is rejected with HTTP 403 Forbidden.
- **Anti-IDOR Query Isolation:** Event queries and retrieval enforce facility boundaries. Requests for events outside the user's facility return HTTP 404 Not Found (information concealment).
- **Query Parameter Validation:** Range validation enforces `start_time <= end_time`, rejecting inverted query windows with HTTP 422 Unprocessable Entity. Maximum page size is strictly bounded to 100 items with deterministic secondary sorting by `event_id`.

### 2.7 Privacy & Multi-Layer PHI Scrubbing
Event payloads and metadata undergo recursive multi-layer inspection before ingestion:
- **Key Inspection:** Rejects prohibited sensitive key names (e.g. `ssn`, `mrn`, `patient_name`, `dob`, `credit_card`, `phone`, `password`, `secret`).
- **Value Pattern Scanning:** Scans all string values for SSN regex (`\d{3}-\d{2}-\d{4}`), email patterns, and phone patterns.
- **Information Concealment in Errors:** Validation errors identify the violating field path and pattern without echoing the sensitive field values into logs or HTTP response bodies.

---

## 3. Scope Boundaries & Future Chunks

The foundational event system explicitly scopes out the following capabilities, which are scheduled for subsequent Milestone 6 chunks:
- **Chunk 6.2 (Operational Rule Engine):** Declarative rule definitions, threshold condition evaluators, and composite triggers listening to events.
- **Chunk 6.3 (Real-Time Notification Center):** User notification models, WebSocket/SSE push streaming, alert state lifecycle (unread/read/dismissed).
- **Chunk 6.4 (Automated Multi-Agent Triggers):** Event-triggered reactive agent investigations and background operational assessments.
- **Chunk 6.5 (Operational Action Execution & Review):** Human-in-the-loop review workflow, action staging, and audited operational dispatch.

---

## 4. Consequences and Verification

- **Positive:** System components can now emit typed, tamper-evident operational events without coupling to downstream listeners or alert dispatchers.
- **Positive:** Zero silent data loss: MongoDB unavailability fails fast and loud in production.
- **Positive:** Complete backward compatibility with all Milestone 1–5 services and agent coordination runtimes.
- **Verification:** Verified by 44 comprehensive unit, integration, security API, and hardening tests covering contracts, future timestamp skew, payload hashing, duplicate idempotency under concurrency, conflict detection, facility isolation, PHI scrubbing, query stability, and health telemetry.
