# ADR-016: Persistent Agent State Management, Session Scoping, and Multi-Turn Conversation Continuity

## Context and Problem Statement

In Milestone 5, Chunk 5.1 established the first Hospital Operations Analyst Agent, Chunk 5.2 introduced standardized machine-readable tool schemas and permission-based discovery, and Chunk 5.3 established the bounded Agent Orchestration Engine with formal state transitions and evidence grounding.

However, executions remained isolated, single-turn interactions. When an administrator asked:
1. *"Show me the latest available ICU forecast."*
2. *"Now compare it with the previous forecast."*
3. *"What happens if admissions increase by 15%?"*
4. *"Summarize the operational implications."*

The agent could not understand references to the previous forecast, track the hypothetical surge scenario from the preceding turn, or synthesize multi-turn conclusions.

Simply concatenating raw chat transcripts into an LLM prompt is dangerous in healthcare operations:
1. **Context Explosion:** Unbounded history quickly exceeds token budgets or dilutes LLM reasoning attention.
2. **Epistemic Confusion:** Stale hypothetical simulations from prior turns could be hallucinated as empirical observations or current clinical reality.
3. **Security & RBAC Breaches:** An unprivileged user could inherit access to sensitive domain evidence generated in an earlier turn or from a different session.
4. **Data Isolation:** Sessions and messages must be securely scoped to authenticated users with atomic concurrency control and clear lifecycle status management (ACTIVE, ARCHIVED, EXPIRED).

---

## Decision Drivers

1. **Persistent Session Scoping:** Store conversational threads and messages in authoritative MongoDB collections (`agent_sessions` and `agent_messages`) with strict ownership enforcement (`user_id == current_user.user_id`).
2. **Bounded Context Reconstruction:** Reconstruct context working backwards from the most recent turn, respecting a configurable character/token budget (`max_context_chars`), and truncating older turns cleanly.
3. **Epistemic Qualification & Freshness:** Explicitly tag prior turns and evidence with domain classifications (`[Observed]`, `[Forecast]`, `[Simulation]`, `[Optimization]`). Explicitly warn planners that historical statements do not override live operational reality.
4. **Dynamic RBAC Revalidation:** Revalidate caller permissions when reconstructing context; unprivileged callers cannot inherit historical evidence requiring permissions they do not possess.
5. **Preserved Execution Engine:** The Chunk 5.3 `AgentOrchestrator` remains the sole execution engine; `AgentStateManager` supplies reconstructed context and persists user/assistant turns.
6. **Zero Write Mutations & Non-Clinical Safety:** All tools remain strictly read-only; clinical diagnostic or prescription requests remain strictly rejected.

---

## Decision Outcome

We implemented a secure, persistent, session-scoped agent state management system comprising:

### 1. Persistence Layer (`agent_sessions` & `agent_messages`)
- **`AgentSessionDocument`:** Tracks `session_id`, `user_id`, `agent_id`, `title`, `status` (`ACTIVE`, `ARCHIVED`, `EXPIRED`), `message_count`, `last_activity_at`, `latest_execution_id`, and optimistic concurrency `version`.
- **`AgentMessageDocument`:** Chronological message records capturing `message_id`, `session_id`, `user_id`, `role` (`USER`, `ASSISTANT`, `SYSTEM`), `content`, `status`, `execution_id`, and structured operational metadata (`task_plan`, `evidence_summaries`, `forecast_references`, `simulation_references`, `optimization_references`).
- **Compound Indexes:** Registered in MongoDB client for high-performance scoped queries: `(user_id, status, last_activity_at DESC)`, `(session_id, created_at ASC)`.

### 2. Context Reconstruction Engine (`AgentContextBuilder`)
- Formulates `AgentConversationContext` containing recent turns (`AgentConversationTurn`).
- Clamps total conversational history to a strict character budget (default 4,000 chars), safely flagging `is_truncated = True` if older turns are omitted.
- Revalidates granular permissions against cached evidence references (`predictions.read`, `simulation.read`, `optimization.read`, `knowledge.read`), filtering out unauthorized items.
- Formats untrusted context blocks with epistemic headers and disclaimer notes.

### 3. State Management Coordinator (`AgentStateManager`)
- Coordinates session creation, retrieval, updates, status transitions, and deletion.
- Enforces active status guards: rejects execution attempts on archived sessions with HTTP 400 Bad Request.
- Implements maximum message guardrails (`MAX_MESSAGES_PER_SESSION = 100`).
- Manages atomic message increments and timestamp updates via `update_activity(...)`.

### 4. REST Endpoints (`/api/v1/agents/sessions`)
- `POST /sessions`: Create persistent conversational thread.
- `GET /sessions`: List caller's sessions with lifecycle status filtering and pagination.
- `GET /sessions/{id}`: Inspect session metadata.
- `PATCH /sessions/{id}`: Modify title or custom tags.
- `POST /sessions/{id}/archive` & `POST /sessions/{id}/restore`: Lifecycle transitions.
- `DELETE /sessions/{id}`: Purge conversational messages while preserving execution audit logs.
- `GET /sessions/{id}/messages`: List chronological message history.
- `POST /sessions/{id}/messages`: Submit follow-up inquiry and execute conversational turn.
- `POST /execute` & `POST /run`: Updated with optional `session_id` to route execution seamlessly through state management.

### 5. Frontend Multi-Turn Workbench Integration
- **`AgentSessionSidebar`:** Interactive sidebar displaying user sessions, status filter tabs (Active, Archived, All), message counts, relative timestamps, and thread action controls (Archive, Restore, Delete, New Thread).
- **`AgentConversationStream`:** Chronological dialogue stream rendering user message bubbles, assistant cards with epistemic badges, formatted markdown answers, and expandable provenance accordions.
- **Suggested Canonical Workflow:** One-click quick-start buttons guiding users through the 4-turn operational scenario (Forecast -> Trend Comparison -> Surge Sensitivity -> Implications Summary).
- **Collapsible Diagnostics:** Preserved full execution timeline and provenance card inspection for the latest turn.

---

## Status

**Accepted and Complete (Milestone 5, Chunk 5.4).**
- Verified with 10 unit and API tests in `backend/tests/test_agent_sessions.py`.
- 100% pass across all 58 agent tests and 287 backend regression tests.
- 100% clean production build and zero linter warnings on frontend.
