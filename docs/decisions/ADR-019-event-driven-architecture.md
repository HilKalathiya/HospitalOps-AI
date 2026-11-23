# ADR-019: Foundational Event-Driven Architecture & Event System

## Status
**Accepted & Implemented (Milestone 6, Chunk 6.1)**

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

---

## 2. Core Architectural Decisions

### 2.1 Separation of Concerns & Healthcare Safety Invariant
The event system adheres strictly to the HospitalOps AI Engineering Constitution:
- **Events represent past facts, never commands:** An event records that a state transition or analytical run has already completed (e.g., `operations.capacity.updated`, `forecasting.completed`). Events never order clinical actions or autonomously mutate clinical state.
- **Strictly Operational:** No clinical diagnostic or prescriptive clinical data is captured in event envelopes or payloads. All operational recommendations and alerts retain `requires_human_review = True`.
- **Append-Only Event Store:** The persistence layer (`operational_events` collection) is strictly immutable and append-only. No update or delete operations are exposed on the event repository or API.

### 2.2 Standardized Event Envelope (`OperationalEvent`)
Every operational event follows a uniform, strictly validated Pydantic v2 envelope:
```
OperationalEvent
├── event_id: str (UUIDv4 or prefixed, e.g. evt_...)
├── event_type: EventType (e.g. operations.capacity.updated)
├── category: EventCategory (operations | forecasting | simulation | optimization | agent)
├── occurred_at: datetime (UTC, max 5-minute future skew allowance)
├── recorded_at: datetime (UTC server ingestion timestamp)
├── facility_id: str (Authoritative multi-tenant boundary)
├── source: str (Subsystem identifier, e.g. hospitalops.capacity_service)
├── entity_type: EntityType (facility | department | ward | bed | forecast | ...)
├── entity_id: str (Identifier of affected operational entity)
├── correlation_id: str (Traceability across workflows/requests)
├── causation_id: str | None (Upstream event/message that triggered this event)
├── actor_id: str | None (Authenticated user or system actor)
├── payload_version: str (Semantic version of payload schema, e.g. "1.0")
├── payload_hash: str (Deterministic SHA-256 digest of canonical JSON payload)
├── payload: BasePayload (Type-checked against EVENT_PAYLOAD_MAP)
└── metadata: dict[str, Any] (Supplementary unindexed operational context)
```

Extra fields on either envelope or payload are strictly forbidden (`extra="forbid"`). Payloads are bounded to a maximum size of 64 KB, and automatic inspection detects and rejects potential PII/PHI (such as SSN patterns or sensitive patient keys).

### 2.3 Deterministic Payload Hashing & Idempotency
To prevent duplicate processing in distributed environments:
1. When an event is ingested, a deterministic SHA-256 fingerprint is calculated over the canonical JSON representation of its payload (`sort_keys=True`, normalized separators).
2. If an event is published with an `event_id` that already exists in MongoDB:
   - If `existing.payload_hash == incoming.payload_hash`: The event is recognized as an idempotent retransmission. The existing event is returned with `is_duplicate = True`, avoiding duplicate processing without raising an error.
   - If `existing.payload_hash != incoming.payload_hash`: A conflicting mutation with an identical ID is detected, and an `EventConflictError` (HTTP 409) is raised.

### 2.4 Event Taxonomy & Catalog
The event catalog registers 15 typed events across 5 functional domains:
- **Operations & Capacity (4):** `operations.capacity.updated`, `operations.occupancy.threshold_breached`, `operations.admissions.surge_detected`, `operations.bed.status_changed`.
- **Forecasting (2):** `forecasting.completed`, `forecasting.degraded`.
- **Simulation (3):** `simulation.scenario_run_completed`, `simulation.bottleneck_detected`, `simulation.capacity_exhaustion_projected`.
- **Optimization (3):** `optimization.plan_generated`, `optimization.constraint_violation_flagged`, `optimization.surge_protocol_recommended`.
- **Agent Execution (3):** `agent.investigation_started`, `agent.specialist_dispatched`, `agent.investigation_completed`.

Every event definition specifies its required payload schema, entity category, description, and whether human review is required.

### 2.5 Publishing Abstraction & Decoupled Service
Publishing is decoupled via the `EventPublisher` abstract interface and implemented by `OperationalEventPublisher`:
```
Caller (e.g. API / Service)
       │
       ▼
OperationalEventService (Domain helper methods, facility check, audit context)
       │
       ▼
OperationalEventPublisher (Validation, timestamp normalization, SHA-256 hashing)
       │
       ▼
OperationalEventRepository (MongoDB 'operational_events' / Offline test fallback)
```

### 2.6 Persistence & Multi-Tenant Query Isolation
MongoDB serves as the authoritative persistence engine via the `operational_events` collection:
- **Indexes:**
  - Unique index: `{"event_id": 1}`, `unique=True`.
  - Multi-tenant time index: `{"facility_id": 1, "occurred_at": -1}`.
  - Multi-tenant type index: `{"facility_id": 1, "event_type": 1, "occurred_at": -1}`.
  - Multi-tenant category index: `{"facility_id": 1, "category": 1, "occurred_at": -1}`.
  - Entity trace index: `{"entity_type": 1, "entity_id": 1, "occurred_at": -1}`.
  - Correlation index: `{"correlation_id": 1, "occurred_at": -1}`.
- **Offline Fallback:** If MongoDB is unavailable (e.g. during lightweight unit tests), the repository operates in an explicit, logged in-memory fallback mode while preserving idempotency and querying semantics.

### 2.7 Security & Anti-IDOR Enforcement
- Authenticated endpoints enforce permissions: `events.read` to query events, `events.publish` to publish events.
- Facility scoping prevents cross-tenant data leakage: Non-system-admin users are strictly confined to their assigned `facility_id`. Attempts to publish or query across unassigned facilities are rejected with HTTP 403 / 404.

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
- **Positive:** Complete backward compatibility with all Milestone 1–5 services and agent coordination runtimes.
- **Verification:** Verified by 30 comprehensive unit, integration, and security API tests covering contracts, future timestamp skew, payload hashing, duplicate idempotency, conflict detection, facility isolation, and pagination.
