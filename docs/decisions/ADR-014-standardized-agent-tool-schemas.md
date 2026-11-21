# ADR-014: Standardized Agent Tool Contracts, Machine-Readable Schemas, and Permission-Filtered Discovery

## Context and Problem Statement

In Milestone 5, Chunk 5.1, HospitalOps AI introduced its first autonomous agent (`hospital_operations_analyst`) and an initial bounded runtime. The runtime allowed the agent to invoke domain services across hospital knowledge retrieval, occupancy forecasting, what-if simulations, and resource optimizations.

However, as the system evolves toward a multi-agent operational ecosystem (e.g., dedicated capacity forecasters, bed allocation optimizers, simulation auditors), several architectural requirements emerge:

1. **Deterministic Pre-Execution Validation:** Tool inputs must be strictly validated before entering domain execution loops. Malformed or out-of-boundary parameters must fail immediately with clear, typed error codes rather than propagating unexpected runtime crashes into analytical algorithms.
2. **Deterministic Post-Execution Validation:** Tool outputs must conform strictly to typed response contracts (`output_schema`). Raw service outputs must be verified and sanitized before being handed to LLM context assemblers or caller response payloads.
3. **Machine-Readable Schemas & Model Interoperability:** LLM providers (including OpenAI function calling and local compatible models) require standard JSON Schemas (Draft 2020-12) defining parameter types, properties, and required keys. These schemas must be generated deterministically from Pydantic models.
4. **Strict RBAC & Discovery Boundary:** In a healthcare enterprise environment, users and agents must not be able to discover or execute tools for which they lack authorization. Tool discovery and inspection endpoints must filter out tools based on caller permissions and deny unauthorized detail queries with HTTP 403 Forbidden.
5. **Contract Versioning & Semver Compatibility:** As tools evolve, contract compatibility must be verifiable (semver major/minor/patch) to prevent agent hallucinations or version mismatch regressions.
6. **Strict Read-Only Healthcare Safety Boundary:** In alignment with `AGENTS.md`, every operational tool in the current platform must strictly enforce `ExecutionType.READ_ONLY`. Zero live data mutations, discharges, or clinical decisions are permitted.

---

## Decision Drivers

1. **Strong Typing with Pydantic v2:** Dual typing for every tool (`input_schema: type[BaseModel]`, `output_schema: type[BaseModel]`).
2. **Format Agnostic Schema Generation:** Automatic conversion to standard JSON Schema and OpenAI function calling formats (`{"type": "function", "function": {...}}`).
3. **Standardized Error Taxonomy:** Formal `ToolErrorCode` enum (`UNKNOWN_TOOL`, `INVALID_INPUT`, `UNSUPPORTED_SCHEMA_VERSION`, `PERMISSION_DENIED`, `TOOL_DISABLED`, `APPROVAL_REQUIRED`, `OUTPUT_VALIDATION_FAILED`, `EXECUTION_TIMEOUT`, `EXECUTION_FAILED`, `OUTPUT_LIMIT_EXCEEDED`).
4. **Permission-Aware Registry & Discovery:** `ToolRegistry.discover_tools(user_permissions)` guarantees that callers cannot see or inspect tools they cannot use.
5. **Interactive Schema Explorer in Frontend:** Dedicated UI inspector (`AgentToolsModal`) on the `/agents` workbench enabling administrators to review input/output schemas, RBAC constraints, and contract metadata.

---

## Considered Options

1. **Option 1: Informal Python Function Call Signatures with Docstring Parsing**
   - *Rejected:* Fragile, error-prone, lacks JSON Schema generation, cannot enforce post-execution output validation, and leaves agents vulnerable to silent schema drift.

2. **Option 2: Heavy Third-Party Agent Framework Tool Wrappers (e.g., LangChain `@tool`)**
   - *Rejected:* Couples HospitalOps AI to large third-party dependencies, breaks Pydantic v2 strict typing, lacks enterprise RBAC filtering on discovery, and risks violating project dependency discipline.

3. **Option 3: Native Standardized Tool Schema Architecture (`AgentTool` + Pydantic v2)**
   - *Selected:* Overhauls `AgentTool` abstract base class to mandate dual Pydantic schemas, standard JSON Schema draft 2020-12 generation, pre/post execution validation, semver tracking, and permission-filtered discovery.

---

## Decision Outcome

Adopted **Option 3**:

### 1. Unified Tool Contract Specification
Every tool subclassing `AgentTool` must define:
- `tool_id: str`: Unique machine-readable identifier.
- `display_name: str`: Human-readable label.
- `category: ToolCategory`: Domain category (`KNOWLEDGE`, `FORECASTING`, `SIMULATION`, `OPTIMIZATION`, `OPERATIONS`, `SYSTEM`).
- `execution_type: ExecutionType`: Set strictly to `READ_ONLY`.
- `schema_version: str`: Semver string (default `1.0.0`).
- `required_permission: str`: RBAC permission (e.g. `knowledge.read`, `predictions.read`, `simulation.read`, `optimization.read`).
- `input_schema: type[BaseModel]`: Pydantic input model.
- `output_schema: type[BaseModel]`: Pydantic output model.
- `tags: list[str]`: Capability tags for registry filtering.

### 2. Dual Validation Pipeline (`execute_with_validation`)
Tools execute inside a three-stage pipeline:
1. `validate_input(arguments)`: Validates raw arguments against `input_schema`. If validation fails, raises `ToolExecutionError(ToolErrorCode.INVALID_INPUT)`.
2. `execute(validated_input, context)`: Invokes underlying deterministic domain services under execution timeout.
3. `validate_output(raw_output)`: Validates service return against `output_schema`. If validation fails, raises `ToolExecutionError(ToolErrorCode.OUTPUT_VALIDATION_FAILED)`.

### 3. Permission-Filtered Discovery
The `ToolRegistry.discover_tools()` method takes `user_permissions: list[str]` and strictly excludes any tool whose `required_permission` is not present in the caller's role. Unprivileged callers cannot observe or inspect unauthorized tools.

### 4. REST Discovery Endpoints
- `GET /api/v1/agents/tools`: Returns authorized tool definitions with optional category and tag filtering.
- `GET /api/v1/agents/tools/{tool_id}`: Returns complete tool metadata and input/output JSON schemas; returns HTTP 403 Forbidden if the caller lacks the required RBAC permission.

### 5. Frontend Tool Schemas & Contracts Inspector
The `/agents` page features an interactive schema viewer (`AgentToolsModal`) enabling operational administrators to inspect tool categories, permissions, capability tags, input arguments, output contracts, and raw JSON Schemas.

---

## Registered Tool Inventory (Chunk 5.2)

| Tool ID | Category | Version | Required Permission | Execution Type | Input Schema | Output Schema |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `search_hospital_knowledge` | `KNOWLEDGE` | `1.0.0` | `knowledge.read` | `READ_ONLY` | `SearchHospitalKnowledgeInput` | `SearchHospitalKnowledgeOutput` |
| `answer_from_hospital_knowledge` | `KNOWLEDGE` | `1.0.0` | `knowledge.read` | `READ_ONLY` | `AnswerFromHospitalKnowledgeInput` | `AnswerFromHospitalKnowledgeOutput` |
| `get_existing_forecast` | `FORECASTING` | `1.0.0` | `predictions.read` | `READ_ONLY` | `GetExistingForecastInput` | `GetExistingForecastOutput` |
| `get_simulation_result` | `SIMULATION` | `1.0.0` | `simulation.read` | `READ_ONLY` | `GetSimulationResultInput` | `GetSimulationResultOutput` |
| `get_optimization_explanation` | `OPTIMIZATION` | `1.0.0` | `optimization.read` | `READ_ONLY` | `GetOptimizationExplanationInput` | `GetOptimizationExplanationOutput` |

---

## Healthcare Safety Boundary

In strict accordance with `AGENTS.md`:
- All agent tools are strictly `READ_ONLY`.
- Zero database write mutations or live resource reservations are permitted via agent tools.
- All consequential recommendations require human administrative review before real-world operational execution.
- No clinical diagnosis, medical treatment, or patient prescription capabilities exist in any tool schema.
