# HospitalOps AI — Integration Contracts

> **Document status:** Chunk 0.2 — Architecture & API Contract
> **Last updated:** August 2026

This document defines the **conceptual interface contracts** for all future HospitalOps AI
integration layers: ML, simulation, optimization, RAG, agents, human-in-the-loop, and events.

> ⚠️ **None of these interfaces are implemented yet.** This document defines what they
> will look like when built, so future chunks have a clear contract to implement against.

---

## ML / Forecasting Interface

The ML layer produces forecasts consumed by the `predictions` domain service.

### Conceptual Interface

```python
class ForecastModel(Protocol):
    """Interface that all HospitalOps AI forecast models must satisfy."""

    @property
    def model_name(self) -> str: ...

    @property
    def model_version(self) -> str: ...

    def train(self, features: ForecastFeatures) -> TrainingResult: ...

    def evaluate(self, features: ForecastFeatures) -> EvaluationResult: ...

    def predict(self, request: ForecastRequest) -> ForecastResult: ...
```

### ForecastRequest

```python
class ForecastRequest:
    forecast_type: ForecastType    # ICU_DEMAND | BED_OCCUPANCY | ADMISSION_VOLUME
    department_id: str | None      # None = hospital-wide
    horizon_hours: int             # how far ahead to forecast (e.g. 24, 48, 72)
    generated_at: datetime         # UTC — when the forecast is requested
```

### ForecastResult

```python
class ForecastResult:
    forecast_type: ForecastType
    department_id: str | None
    model_name: str
    model_version: str
    horizon_hours: int
    generated_at: datetime          # UTC
    predictions: list[ForecastPoint]

class ForecastPoint:
    timestamp: datetime             # UTC — the point in time being forecast
    predicted_value: float
    lower_bound: float              # confidence interval lower
    upper_bound: float              # confidence interval upper
    confidence: float               # 0.0–1.0
```

**Rules:**
- ML models predict; they do not recommend actions.
- Confidence intervals must always be provided.
- Models are independently versioned and can be swapped without touching the service layer.

---

## Simulation Interface

The simulation engine computes projected outcomes for what-if scenarios.

### ScenarioRequest

```python
class ScenarioRequest:
    scenario_name: str
    base_timestamp: datetime        # UTC — the point in time to simulate from
    horizon_hours: int
    parameters: ScenarioParameters

class ScenarioParameters:
    admission_rate_change_pct: float | None   # e.g. +20% admission surge
    discharge_rate_change_pct: float | None
    capacity_change_beds: int | None          # e.g. +10 surge beds
    resource_availability_change: dict | None # resource_id → available count
    staff_level_change_pct: float | None
```

### ScenarioResult

```python
class ScenarioResult:
    scenario_id: str
    scenario_name: str
    base_timestamp: datetime        # UTC
    horizon_hours: int
    parameters: ScenarioParameters
    computed_at: datetime           # UTC
    outcome: ScenarioOutcome

class ScenarioOutcome:
    projected_occupancy_pct: list[TimeseriesPoint]
    projected_icu_utilization_pct: list[TimeseriesPoint]
    projected_bed_shortage_events: list[ShortagePeriod]
    projected_resource_shortages: list[ResourceShortage]
    summary: str                    # plain-language outcome description
```

**Rules:**
- Simulation is **deterministic** — same inputs always produce same outputs.
- Simulations are labeled as projections, never as predictions.
- Simulation results are stored in `simulation_runs` collection for audit purposes.

---

## Optimization Interface

The optimization engine produces resource allocation recommendations.

### OptimizationRequest

```python
class OptimizationRequest:
    objective: OptimizationObjective   # MINIMIZE_SHORTAGE | MAXIMIZE_UTILIZATION
    constraints: OptimizationConstraints
    context: OptimizationContext

class OptimizationConstraints:
    max_bed_occupancy_pct: float       # e.g. 0.90
    min_staff_ratio: float
    locked_resources: list[str]        # resource IDs that cannot be reallocated
    time_horizon_hours: int

class OptimizationContext:
    current_occupancy: dict            # department_id → current_count
    current_resources: dict            # resource_id → available_count
    forecast: ForecastResult           # from ML layer
```

### OptimizationResult

```python
class OptimizationResult:
    optimization_id: str
    objective: OptimizationObjective
    status: OptimizationStatus        # FEASIBLE | INFEASIBLE | TIMEOUT
    computed_at: datetime             # UTC
    recommendations: list[Recommendation]
    expected_effect: ExpectedEffect
    warnings: list[str]

class Recommendation:
    action: str                        # human-readable action description
    resource_type: str
    resource_id: str | None
    from_location: str | None
    to_location: str | None
    quantity: int | None
    rationale: str                     # why this recommendation was made
    priority: int                      # 1 = highest

class ExpectedEffect:
    projected_occupancy_pct: float
    shortage_risk_reduction_pct: float
    explanation: str
```

**Rules:**
- Optimization produces **recommendations**, not executed actions.
- Every recommendation includes a `rationale` field for explainability.
- Results require human approval before any action is taken.
- `INFEASIBLE` results must explain why no feasible solution was found.

---

## RAG / Knowledge Interface

The RAG layer provides grounded context from hospital operational documents.

### KnowledgeSearchRequest

```python
class KnowledgeSearchRequest:
    query: str                         # natural language query
    department_ids: list[str] | None   # filter to specific departments
    document_types: list[str] | None   # filter to specific document types
    max_results: int = 5               # number of chunks to retrieve
```

### KnowledgeSearchResult

```python
class KnowledgeSearchResult:
    query: str
    results: list[KnowledgeChunk]
    retrieved_at: datetime             # UTC

class KnowledgeChunk:
    chunk_id: str
    document_id: str
    document_title: str
    document_type: str                 # POLICY | PROCEDURE | PROTOCOL | GUIDELINE
    section: str | None
    content: str                       # retrieved text chunk
    relevance_score: float             # 0.0–1.0
    source_url: str | None
    last_updated: datetime             # UTC — when the source document was last updated
```

**Rules:**
- RAG retrieves from **real documents only**; it never fabricates content.
- Every retrieved chunk must be attributed to its source document.
- Agents using RAG results must include source references in their outputs.
- Relevance scores below a configurable threshold should be excluded.

---

## Agent Interface

### AgentRunRequest

```python
class AgentRunRequest:
    task: str                          # natural language task description
    context: AgentContext | None
    tools_allowed: list[str] | None    # None = all allowed tools
    max_steps: int = 10
    require_human_approval: bool = False

class AgentContext:
    department_id: str | None
    time_window_hours: int | None
    additional_data: dict | None
```

### AgentRunResult

```python
class AgentRunResult:
    run_id: str
    status: AgentRunStatus            # COMPLETED | FAILED | PENDING_APPROVAL | CANCELLED
    task: str
    started_at: datetime              # UTC
    completed_at: datetime | None     # UTC
    steps: list[AgentStep]
    result: str | None                # final natural language output
    recommendations: list[Recommendation] | None
    tool_calls_made: int
    tokens_used: int | None

class AgentStep:
    step_index: int
    step_type: str                    # REASONING | TOOL_CALL | OBSERVATION | CONCLUSION
    content: str
    tool_name: str | None
    tool_input: dict | None
    tool_output: dict | None
    timestamp: datetime               # UTC
```

### AgentTool Contract

Every agent tool must define:

```python
class AgentTool(Protocol):
    name: str                         # snake_case identifier used in LLM tool calling
    description: str                  # what the tool does (used in LLM system prompt)
    input_schema: type[BaseModel]     # Pydantic schema for tool inputs
    output_schema: type[BaseModel]    # Pydantic schema for tool outputs
    permissions: list[str]            # roles that may use this tool
```

**Planned tools (not yet implemented):**

| Tool Name | Description | Calls |
|---|---|---|
| `get_hospital_status` | Current overall occupancy summary | `BedsService`, `AdmissionsService` |
| `get_icu_status` | ICU-specific bed and resource state | `BedsService`, `ResourcesService` |
| `get_bed_availability` | Available beds by department | `BedsService` |
| `get_current_forecast` | Latest ML forecast | `PredictionsService` |
| `run_simulation` | Execute a what-if scenario | `SimulationService` |
| `optimize_resources` | Generate resource allocation recommendation | `OptimizationService` |
| `search_hospital_policy` | Retrieve relevant policy/procedure | `KnowledgeService` (RAG) |
| `get_resource_inventory` | Current resource availability | `ResourcesService` |
| `get_admission_trends` | Recent admission rate analysis | `AdmissionsService` |

---

## Human-in-the-Loop Recommendation Lifecycle

```
1. Agent generates recommendation (OptimizationResult or ad-hoc)
        ↓
2. Recommendation stored in MongoDB
   status: PENDING_REVIEW
   created_at: <UTC>
   created_by: <agent_run_id>
        ↓
3. Dashboard surfaces recommendation to authorized approver
        ↓
4. Human decision (one of):
   ├── APPROVED  → action_taken_at, approved_by, rationale (optional)
   ├── REJECTED  → rejected_at, rejected_by, rationale (required)
   └── MODIFIED  → modified_at, modified_by, modified_parameters, rationale (required)
        ↓
5. Audit log entry written (immutable)
   { entity_type: "recommendation", entity_id: ..., action: "APPROVED",
     actor: ..., timestamp: ..., payload: ... }
        ↓
6. If APPROVED or MODIFIED+APPROVED:
   Service layer executes the action
        ↓
7. Audit log entry written: action executed
```

**Rules:**
- No autonomous resource changes. Human approval is always required for consequential actions.
- The recommendation status is an immutable state machine: `PENDING_REVIEW → APPROVED | REJECTED | MODIFIED`.
- Audit entries are append-only and never deleted.

---

## Event Catalog *(Planned)*

Domain events will be published to a Redis Stream and consumed by downstream services.

### Event Envelope

```python
class DomainEvent:
    event_id: str                     # UUID
    event_type: str                   # e.g. "PATIENT_ADMITTED"
    entity_type: str                  # e.g. "admission"
    entity_id: str
    payload: dict
    published_at: datetime            # UTC
    correlation_id: str               # request_id of the originating request
```

### Planned Event Types

| Event | Trigger |
|---|---|
| `PATIENT_ADMITTED` | Admission record created |
| `PATIENT_DISCHARGED` | Discharge event recorded |
| `PATIENT_TRANSFERRED` | Patient moves between wards |
| `BED_STATUS_CHANGED` | Bed becomes available or occupied |
| `RESOURCE_STATUS_CHANGED` | Resource availability changes |
| `FORECAST_UPDATED` | New ML forecast generated |
| `SURGE_RISK_DETECTED` | Forecast exceeds surge threshold |
| `RECOMMENDATION_CREATED` | Agent or system creates a recommendation |
| `RECOMMENDATION_APPROVED` | Human approves a recommendation |
| `RECOMMENDATION_REJECTED` | Human rejects a recommendation |
| `ALERT_TRIGGERED` | Alert condition met |
| `ALERT_ACKNOWLEDGED` | Alert acknowledged by administrator |

### Event Consumers *(Planned)*

| Consumer | Subscribes To |
|---|---|
| Alert Service | `SURGE_RISK_DETECTED`, `BED_STATUS_CHANGED` |
| Agent Trigger | `SURGE_RISK_DETECTED`, `FORECAST_UPDATED` |
| Audit Service | All events |
| Dashboard WebSocket relay | `BED_STATUS_CHANGED`, `RESOURCE_STATUS_CHANGED` |
