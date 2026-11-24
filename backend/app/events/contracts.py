"""
HospitalOps AI — Operational Event Contracts & Envelope (Milestone 6, Chunk 6.1).

Defines strongly-typed event schemas, domain categories, entity references,
and payload validation pipelines. Strictly separates:
- Observed operational reality
- Statistical forecast outputs
- What-if simulation trajectories
- Constrained optimization proposals
- Agent orchestration decisions
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import ConfigDict, Field, field_validator, model_validator

from app.events.exceptions import EventValidationError
from app.models.base import HospitalOpsBaseModel, utc_now

# Max payload and metadata sizes to prevent memory exhaustion and database bloat
MAX_PAYLOAD_BYTES = 65536  # 64 KB
MAX_METADATA_BYTES = 16384  # 16 KB
MAX_CLOCK_SKEW_SECONDS = 300  # 5 minutes future tolerance

# Disallowed sensitive patterns (PHI, credentials, secrets)
SENSITIVE_KEY_PATTERNS = re.compile(
    r"(?i)(password|secret|token|api_key|apikey|private_key|bearer|ssn|mrn|patient_name|first_name|last_name|full_name|dob|date_of_birth|phone|email|credit_card|national_id)"
)
SSN_REGEX = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
PHONE_REGEX = re.compile(r"\b(?:\+?1[-.]?)?\(?[2-9]\d{2}\)?[-.]?\d{3}[-.]?\d{4}\b")


# ── Event Types & Categories ──────────────────────────────────────────────────


class EventType(str, Enum):
    """
    Standardized, namespaced event types in HospitalOps AI.
    Follows dot-notation: domain.entity.action_or_state.
    """

    # Operational capacity & resources
    OPERATIONS_CAPACITY_UPDATED = "operations.capacity.updated"
    OPERATIONS_BED_STATUS_CHANGED = "operations.bed_status.changed"
    OPERATIONS_RESOURCE_AVAILABILITY_CHANGED = "operations.resource_availability.changed"

    # Patient throughput
    OPERATIONS_ADMISSION_RECORDED = "operations.admission.recorded"
    OPERATIONS_DISCHARGE_RECORDED = "operations.discharge.recorded"
    OPERATIONS_TRANSFER_RECORDED = "operations.transfer.recorded"

    # Forecasting lifecycle
    FORECAST_COMPLETED = "forecast.completed"
    FORECAST_FAILED = "forecast.failed"

    # Simulation lifecycle
    SIMULATION_COMPLETED = "simulation.completed"
    SIMULATION_FAILED = "simulation.failed"

    # Optimization lifecycle
    OPTIMIZATION_COMPLETED = "optimization.completed"
    OPTIMIZATION_FAILED = "optimization.failed"

    # Multi-Agent and execution tracking
    AGENT_EXECUTION_COMPLETED = "agent.execution.completed"
    AGENT_EXECUTION_FAILED = "agent.execution.failed"
    AGENT_EXECUTION_REQUIRES_REVIEW = "agent.execution.requires_review"


class EventCategory(str, Enum):
    """
    Epistemic classification of events to prevent category confusion.
    Strictly distinguishes observed reality from analytical projections and governance actions.
    """

    OBSERVED_OPERATIONAL = "OBSERVED_OPERATIONAL"
    DERIVED_OPERATIONAL = "DERIVED_OPERATIONAL"
    FORECAST_OUTPUT = "FORECAST_OUTPUT"
    SIMULATION_OUTPUT = "SIMULATION_OUTPUT"
    OPTIMIZATION_OUTPUT = "OPTIMIZATION_OUTPUT"
    AGENT_EXECUTION = "AGENT_EXECUTION"

    # Backward-compatible mappings for legacy references
    OPERATIONAL_FACT = "OPERATIONAL_FACT"
    ANALYTICAL_OUTPUT = "ANALYTICAL_OUTPUT"
    AGENT_DECISION_SUPPORT = "AGENT_DECISION_SUPPORT"
    GOVERNANCE = "GOVERNANCE"


class EntityType(str, Enum):
    """Operational entity types involved in events."""

    FACILITY = "facility"
    DEPARTMENT = "department"
    BED = "bed"
    RESOURCE = "resource"
    ADMISSION = "admission"
    PATIENT = "patient"
    FORECAST = "forecast"
    SIMULATION = "simulation"
    OPTIMIZATION = "optimization"
    AGENT_EXECUTION = "agent_execution"


# ── Helper Functions ──────────────────────────────────────────────────────────


def _enum_str(val: Any) -> str:
    """Return string representation of enum value or plain string."""
    return val.value if hasattr(val, "value") else str(val)


def compute_payload_hash(payload: dict[str, Any]) -> str:
    """
    Generate a deterministic SHA-256 payload integrity checksum for idempotency duplicate detection.
    Note: This is a content integrity checksum, not a cryptographic tamper-evident audit log.
    """
    try:
        serialized = json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
            default=str,
        )
    except Exception as exc:
        raise EventValidationError(f"Payload cannot be serialized for hashing: {exc}") from exc
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _scrub_and_validate_no_phi(data: Any, path: str = "root") -> None:
    """
    Recursively verify that no sensitive fields or regex patterns are present.
    Error messages NEVER echo the rejected sensitive values to prevent log leakage.
    """
    if isinstance(data, dict):
        for k, v in data.items():
            key_str = str(k)
            if SENSITIVE_KEY_PATTERNS.search(key_str):
                raise EventValidationError(
                    f"Sensitive field name '{key_str}' prohibited in event payload/metadata at '{path}'"
                )
            _scrub_and_validate_no_phi(v, f"{path}.{key_str}")
    elif isinstance(data, list | tuple | set):
        for idx, item in enumerate(data):
            _scrub_and_validate_no_phi(item, f"{path}[{idx}]")
    elif isinstance(data, str):
        if SSN_REGEX.search(data):
            raise EventValidationError(
                f"Prohibited sensitive pattern (SSN) detected at '{path}'"
            )
        if EMAIL_REGEX.search(data):
            raise EventValidationError(
                f"Prohibited sensitive pattern (email) detected at '{path}'"
            )
        if PHONE_REGEX.search(data):
            raise EventValidationError(
                f"Prohibited sensitive pattern (phone) detected at '{path}'"
            )


# ── Strongly Typed Payload Schemas ────────────────────────────────────────────


class BasePayload(HospitalOpsBaseModel):
    """Base payload model enforcing extra='forbid'."""

    model_config = ConfigDict(extra="forbid")


class CapacityUpdatedPayload(BasePayload):
    department_id: str
    total_beds: int = Field(ge=0)
    occupied_beds: int = Field(ge=0)
    operational_occupancy_rate: float = Field(ge=0.0, le=200.0)
    available_beds: int = Field(ge=0)


class BedStatusChangedPayload(BasePayload):
    bed_id: str
    department_id: str
    previous_status: str
    new_status: str
    reason: str | None = None


class ResourceAvailabilityChangedPayload(BasePayload):
    resource_id: str
    resource_type: str
    department_id: str
    total_units: int = Field(ge=0)
    available_units: int = Field(ge=0)


class AdmissionRecordedPayload(BasePayload):
    admission_id: str
    department_id: str
    admitted_at: datetime
    acuity_level: str | None = None
    bed_id: str | None = None


class DischargeRecordedPayload(BasePayload):
    admission_id: str
    department_id: str
    discharged_at: datetime
    length_of_stay_hours: float = Field(ge=0.0)


class TransferRecordedPayload(BasePayload):
    admission_id: str
    source_department_id: str
    target_department_id: str
    transferred_at: datetime
    reason: str | None = None


class ForecastCompletedPayload(BasePayload):
    forecast_id: str
    target_metric: str
    horizon_days: int = Field(ge=1)
    model_type: str
    peak_predicted_value: float
    model_version: str | None = None


class ForecastFailedPayload(BasePayload):
    forecast_id: str
    target_metric: str
    model_type: str
    error_code: str
    error_message: str


class SimulationCompletedPayload(BasePayload):
    scenario_id: str
    scenario_type: str
    peak_occupancy_percentage: float = Field(ge=0.0)
    shortage_days_count: int = Field(ge=0)
    bottleneck_resource: str | None = None


class SimulationFailedPayload(BasePayload):
    scenario_id: str
    scenario_type: str
    error_code: str
    error_message: str


class OptimizationCompletedPayload(BasePayload):
    optimization_id: str
    status: str
    reallocated_beds_count: int = Field(ge=0)
    binding_constraints_count: int = Field(ge=0)
    requires_human_review: bool = True


class OptimizationFailedPayload(BasePayload):
    optimization_id: str
    error_code: str
    error_message: str


class AgentExecutionCompletedPayload(BasePayload):
    run_id: str
    trace_id: str
    agent_id: str
    specialists_invoked: list[str] = Field(default_factory=list)
    is_partial_result: bool = False
    requires_human_review: bool = True
    duration_ms: float = Field(ge=0.0)


class AgentExecutionFailedPayload(BasePayload):
    run_id: str
    trace_id: str | None = None
    agent_id: str
    error_code: str
    error_message: str


class AgentExecutionRequiresReviewPayload(BasePayload):
    run_id: str
    trace_id: str
    agent_id: str
    review_reason: str
    recommendation_summary: str


# Mapping of EventType to its respective payload model and default category
EVENT_PAYLOAD_MAP: dict[EventType, type[BasePayload]] = {
    EventType.OPERATIONS_CAPACITY_UPDATED: CapacityUpdatedPayload,
    EventType.OPERATIONS_BED_STATUS_CHANGED: BedStatusChangedPayload,
    EventType.OPERATIONS_RESOURCE_AVAILABILITY_CHANGED: ResourceAvailabilityChangedPayload,
    EventType.OPERATIONS_ADMISSION_RECORDED: AdmissionRecordedPayload,
    EventType.OPERATIONS_DISCHARGE_RECORDED: DischargeRecordedPayload,
    EventType.OPERATIONS_TRANSFER_RECORDED: TransferRecordedPayload,
    EventType.FORECAST_COMPLETED: ForecastCompletedPayload,
    EventType.FORECAST_FAILED: ForecastFailedPayload,
    EventType.SIMULATION_COMPLETED: SimulationCompletedPayload,
    EventType.SIMULATION_FAILED: SimulationFailedPayload,
    EventType.OPTIMIZATION_COMPLETED: OptimizationCompletedPayload,
    EventType.OPTIMIZATION_FAILED: OptimizationFailedPayload,
    EventType.AGENT_EXECUTION_COMPLETED: AgentExecutionCompletedPayload,
    EventType.AGENT_EXECUTION_FAILED: AgentExecutionFailedPayload,
    EventType.AGENT_EXECUTION_REQUIRES_REVIEW: AgentExecutionRequiresReviewPayload,
}

EVENT_CATEGORY_MAP: dict[EventType, EventCategory] = {
    EventType.OPERATIONS_CAPACITY_UPDATED: EventCategory.OBSERVED_OPERATIONAL,
    EventType.OPERATIONS_BED_STATUS_CHANGED: EventCategory.OBSERVED_OPERATIONAL,
    EventType.OPERATIONS_RESOURCE_AVAILABILITY_CHANGED: EventCategory.OBSERVED_OPERATIONAL,
    EventType.OPERATIONS_ADMISSION_RECORDED: EventCategory.OBSERVED_OPERATIONAL,
    EventType.OPERATIONS_DISCHARGE_RECORDED: EventCategory.OBSERVED_OPERATIONAL,
    EventType.OPERATIONS_TRANSFER_RECORDED: EventCategory.OBSERVED_OPERATIONAL,
    EventType.FORECAST_COMPLETED: EventCategory.FORECAST_OUTPUT,
    EventType.FORECAST_FAILED: EventCategory.FORECAST_OUTPUT,
    EventType.SIMULATION_COMPLETED: EventCategory.SIMULATION_OUTPUT,
    EventType.SIMULATION_FAILED: EventCategory.SIMULATION_OUTPUT,
    EventType.OPTIMIZATION_COMPLETED: EventCategory.OPTIMIZATION_OUTPUT,
    EventType.OPTIMIZATION_FAILED: EventCategory.OPTIMIZATION_OUTPUT,
    EventType.AGENT_EXECUTION_COMPLETED: EventCategory.AGENT_EXECUTION,
    EventType.AGENT_EXECUTION_FAILED: EventCategory.AGENT_EXECUTION,
    EventType.AGENT_EXECUTION_REQUIRES_REVIEW: EventCategory.DERIVED_OPERATIONAL,
}

LEGACY_CATEGORY_COMPATIBILITY: dict[str, set[str]] = {
    "OBSERVED_OPERATIONAL": {"OBSERVED_OPERATIONAL", "OPERATIONAL_FACT"},
    "OPERATIONAL_FACT": {"OBSERVED_OPERATIONAL", "OPERATIONAL_FACT"},
    "FORECAST_OUTPUT": {"FORECAST_OUTPUT", "ANALYTICAL_OUTPUT"},
    "SIMULATION_OUTPUT": {"SIMULATION_OUTPUT", "ANALYTICAL_OUTPUT"},
    "OPTIMIZATION_OUTPUT": {"OPTIMIZATION_OUTPUT", "ANALYTICAL_OUTPUT"},
    "ANALYTICAL_OUTPUT": {"FORECAST_OUTPUT", "SIMULATION_OUTPUT", "OPTIMIZATION_OUTPUT", "ANALYTICAL_OUTPUT"},
    "AGENT_EXECUTION": {"AGENT_EXECUTION", "AGENT_DECISION_SUPPORT"},
    "AGENT_DECISION_SUPPORT": {"AGENT_EXECUTION", "AGENT_DECISION_SUPPORT"},
    "DERIVED_OPERATIONAL": {"DERIVED_OPERATIONAL", "GOVERNANCE"},
    "GOVERNANCE": {"DERIVED_OPERATIONAL", "GOVERNANCE"},
}


# ── Canonical Operational Event Envelope ──────────────────────────────────────


class OperationalEvent(HospitalOpsBaseModel):
    """
    Standardized, strongly-validated event envelope for HospitalOps AI.
    All system events must adhere to this contract.
    """

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        use_enum_values=False,
    )

    event_id: str = Field(
        default_factory=lambda: f"evt_{uuid.uuid4().hex}",
        description="Globally unique event identifier",
    )
    event_type: EventType = Field(description="Namespaced domain event type")
    event_version: str = Field(default="1.0.0", description="Semver schema version")
    category: EventCategory = Field(description="Epistemic domain classification")
    occurred_at: datetime = Field(
        default_factory=utc_now,
        description="UTC timestamp when the event actually occurred in the physical or digital domain",
    )
    recorded_at: datetime = Field(
        default_factory=utc_now,
        description="UTC timestamp when this event was ingested and recorded by HospitalOps AI",
    )
    source: str = Field(
        description="Component or service that generated the event (e.g. 'hospitalops.forecast_service')"
    )
    entity_type: EntityType = Field(description="Primary domain entity type involved")
    entity_id: str = Field(description="Non-sensitive identifier of the primary domain entity")
    facility_id: str = Field(
        default="default_facility",
        description="Authorized facility or organization tenant boundary",
    )
    correlation_id: str | None = Field(
        default=None,
        description="Execution tracing identifier spanning multi-step workflows",
    )
    causation_id: str | None = Field(
        default=None,
        description="Identifier of parent event or user action that triggered this event",
    )
    actor_id: str | None = Field(
        default=None,
        description="Authenticated user or system actor identifier that originated the event",
    )
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Event-specific typed data dictionary",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Non-sensitive contextual metadata (e.g. environment, user_id)",
    )
    payload_hash: str = Field(
        default="",
        description="Deterministic SHA-256 fingerprint of the payload for idempotency detection",
    )

    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, v: str) -> str:
        if not v or not isinstance(v, str) or len(v.strip()) < 5:
            raise EventValidationError("event_id must be a valid non-empty string")
        return v.strip()

    @field_validator("occurred_at", "recorded_at")
    @classmethod
    def validate_utc_timestamp(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            # Assume UTC if naive, but enforce UTC timezone
            v = v.replace(tzinfo=UTC)
        return v

    @model_validator(mode="after")
    def validate_envelope_and_payload(self) -> OperationalEvent:
        # 1. Enforce UTC timezone consistency
        now = datetime.now(UTC)
        if self.occurred_at > now + timedelta(seconds=MAX_CLOCK_SKEW_SECONDS):
            raise EventValidationError(
                f"occurred_at cannot be in the future beyond {MAX_CLOCK_SKEW_SECONDS}s clock skew"
            )

        # 2. Enforce category mapping consistency
        etype_str = _enum_str(self.event_type)
        cat_str = _enum_str(self.category)
        expected_cat = EVENT_CATEGORY_MAP.get(self.event_type) or (
            EVENT_CATEGORY_MAP.get(EventType(etype_str)) if etype_str in [e.value for e in EventType] else None
        )
        if expected_cat:
            exp_str = _enum_str(expected_cat)
            allowed = LEGACY_CATEGORY_COMPATIBILITY.get(exp_str, {exp_str})
            if cat_str not in allowed:
                if exp_str == "OBSERVED_OPERATIONAL":
                    cat_display = "'OPERATIONAL_FACT' (OBSERVED_OPERATIONAL)"
                elif exp_str == "FORECAST_OUTPUT":
                    cat_display = "'ANALYTICAL_OUTPUT' (FORECAST_OUTPUT)"
                elif exp_str == "AGENT_EXECUTION":
                    cat_display = "'AGENT_DECISION_SUPPORT' (AGENT_EXECUTION)"
                elif exp_str == "DERIVED_OPERATIONAL":
                    cat_display = "'GOVERNANCE' (DERIVED_OPERATIONAL)"
                else:
                    cat_display = f"'{exp_str}'"
                raise EventValidationError(
                    f"Event type '{etype_str}' must have category {cat_display}, "
                    f"got '{cat_str}'"
                )

        # 3. Payload size check
        payload_bytes = len(json.dumps(self.payload, default=str).encode("utf-8"))
        if payload_bytes > MAX_PAYLOAD_BYTES:
            raise EventValidationError(
                f"Payload size ({payload_bytes} bytes) exceeds maximum allowable limit of {MAX_PAYLOAD_BYTES} bytes"
            )

        # 4. Metadata size check
        metadata_bytes = len(json.dumps(self.metadata, default=str).encode("utf-8"))
        if metadata_bytes > MAX_METADATA_BYTES:
            raise EventValidationError(
                f"Metadata size ({metadata_bytes} bytes) exceeds maximum allowable limit of {MAX_METADATA_BYTES} bytes"
            )

        # 5. Scrub and validate no PHI in payload or metadata
        _scrub_and_validate_no_phi(self.payload, "payload")
        _scrub_and_validate_no_phi(self.metadata, "metadata")

        # 6. Validate payload against registered schema
        schema_cls = EVENT_PAYLOAD_MAP.get(self.event_type) or (
            EVENT_PAYLOAD_MAP.get(EventType(etype_str)) if etype_str in [e.value for e in EventType] else None
        )
        if schema_cls:
            try:
                schema_cls(**self.payload)
            except Exception as exc:
                raise EventValidationError(
                    f"Payload validation failed for event type '{etype_str}': {exc}"
                ) from exc

        # 7. Compute or verify payload hash server-side
        computed_hash = compute_payload_hash(self.payload)
        if self.payload_hash and self.payload_hash != computed_hash:
            raise EventValidationError(
                "Client-supplied payload_hash does not match server-computed payload integrity checksum"
            )
        if self.payload_hash != computed_hash:
            object.__setattr__(self, "payload_hash", computed_hash)

        return self
