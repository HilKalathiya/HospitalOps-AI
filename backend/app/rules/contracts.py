"""
HospitalOps AI — Operational Rule Engine Contracts & Schemas (Milestone 6, Chunk 6.2).

Defines strongly-typed, validated Pydantic v2 models for:
- Declarative rule definitions and condition trees (safe AST without eval/exec)
- Versioning and policy provenance
- Evaluation records with source event evidence traceability
- Event consumer processing status and lease tracking
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from app.events.contracts import EventCategory, EventType
from app.models.base import HospitalOpsBaseModel, utc_now
from app.rules.exceptions import RuleValidationError

# Maximum structural bounds to prevent resource exhaustion or unbounded recursion
MAX_CONDITION_DEPTH = 3
MAX_CONDITIONS_TOTAL = 10
MAX_WINDOW_SECONDS = 86400  # 24 hours
MIN_WINDOW_SECONDS = 10     # 10 seconds

# Prohibited attribute / clinical diagnostic patterns to prevent AST injection & enforce non-clinical boundary
PROHIBITED_FIELD_PATTERNS = re.compile(
    r"(?i)(__|\bclass\b|\bdict\b|\bglobals\b|\bbuiltins\b|diagnosis|diagnostic|prescription|medication|treatment_plan|clinical_note|lab_result|vitals)"
)


class RuleDomain(str, Enum):
    """Operational domains governed by declarative rules."""

    CAPACITY = "CAPACITY"
    RESOURCES = "RESOURCES"
    THROUGHPUT = "THROUGHPUT"
    STAFFING_AVAILABILITY = "STAFFING_AVAILABILITY"
    SYSTEM_HEALTH = "SYSTEM_HEALTH"


class RuleSeverity(str, Enum):
    """Urgency / operational priority assigned to matched findings."""

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RuleOperator(str, Enum):
    """
    Permitted comparison operators in declarative conditions.
    Executed safely via deterministic Python comparison functions (zero eval/exec).
    """

    EQUALS = "eq"
    NOT_EQUALS = "neq"
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    IN_SET = "in"
    NOT_IN_SET = "not_in"
    EXISTS = "exists"
    DOES_NOT_EXIST = "does_not_exist"


class LogicalOperator(str, Enum):
    """Boolean combination operators for composite conditions."""

    AND = "AND"
    OR = "OR"


class RuleEvaluationStatus(str, Enum):
    """Outcome status of evaluating an operational rule against event(s)."""

    MATCHED = "MATCHED"
    NOT_MATCHED = "NOT_MATCHED"
    SKIPPED = "SKIPPED"
    DATA_MISSING = "DATA_MISSING"
    ERROR = "ERROR"


class ProcessingStatus(str, Enum):
    """Durable lifecycle status of an event in the consumer processing pipeline."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    RETRY_PENDING = "RETRY_PENDING"
    QUARANTINED = "QUARANTINED"


# ── Condition Models (Safe AST) ───────────────────────────────────────────────


class SingleCondition(HospitalOpsBaseModel):
    """
    Represents an atomic, declarative condition evaluated against an event.
    Example: field="payload.occupancy_rate", operator=RuleOperator.GREATER_THAN, value=0.90
    """

    field: str = Field(
        ...,
        description="Dot-path field reference within the event (e.g., 'payload.occupancy_rate', 'facility_id')",
    )
    operator: RuleOperator = Field(..., description="Comparison operator")
    value: Any | None = Field(
        default=None,
        description="Target reference value for comparison (omitted for exists/does_not_exist)",
    )

    @field_validator("field")
    @classmethod
    def validate_field_path(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise RuleValidationError("Condition field path cannot be empty.")
        if PROHIBITED_FIELD_PATTERNS.search(trimmed):
            raise RuleValidationError(
                f"Condition field path '{trimmed}' references prohibited internal or clinical attributes."
            )
        # Permitted root scopes: payload, metadata, or top-level envelope fields
        valid_roots = (
            "payload",
            "metadata",
            "facility_id",
            "event_type",
            "category",
            "source",
            "entity_type",
            "entity_id",
            "actor_id",
        )
        root = trimmed.split(".")[0]
        if root not in valid_roots:
            raise RuleValidationError(
                f"Condition field '{trimmed}' must start with one of permitted root fields: {valid_roots}"
            )
        return trimmed

    @model_validator(mode="after")
    def validate_operator_value_consistency(self) -> SingleCondition:
        op_val = self.operator.value if hasattr(self.operator, "value") else str(self.operator)
        if op_val in ("exists", "does_not_exist"):
            # value is not required and ignored for existence checks
            return self

        if op_val in ("in", "not_in"):
            if not isinstance(self.value, list | tuple | set) or len(self.value) == 0:
                raise RuleValidationError(
                    f"Operator '{op_val}' requires a non-empty list/set value."
                )
        elif self.value is None:
            raise RuleValidationError(
                f"Operator '{op_val}' requires a non-null target comparison value."
            )
        return self


class CompositeCondition(HospitalOpsBaseModel):
    """
    Composite condition combining multiple child conditions with AND or OR.
    Recursion depth and condition count are strictly bounded.
    """

    operator: LogicalOperator = Field(
        default=LogicalOperator.AND,
        description="Logical combination operator",
    )
    conditions: list[SingleCondition | CompositeCondition] = Field(
        ...,
        min_length=1,
        max_length=MAX_CONDITIONS_TOTAL,
        description="Child conditions to combine",
    )

    @model_validator(mode="after")
    def validate_composite_depth(self) -> CompositeCondition:
        def _check_depth_and_count(
            node: SingleCondition | CompositeCondition, current_depth: int
        ) -> tuple[int, int]:
            if current_depth > MAX_CONDITION_DEPTH:
                raise RuleValidationError(
                    f"Condition tree exceeds maximum permitted nesting depth of {MAX_CONDITION_DEPTH}."
                )
            if isinstance(node, SingleCondition):
                return current_depth, 1

            total_count = 0
            max_child_depth = current_depth
            for child in node.conditions:
                child_depth, child_count = _check_depth_and_count(child, current_depth + 1)
                max_child_depth = max(max_child_depth, child_depth)
                total_count += child_count

            if total_count > MAX_CONDITIONS_TOTAL:
                raise RuleValidationError(
                    f"Condition tree exceeds maximum permitted condition count of {MAX_CONDITIONS_TOTAL} (found {total_count})."
                )
            return max_child_depth, total_count

        _check_depth_and_count(self, 1)
        return self


# ── Time Window Configuration ────────────────────────────────────────────────


class TimeWindowConfig(HospitalOpsBaseModel):
    """
    Optional time-window evaluation configuration for multi-event or trend rules.
    Evaluates events occurring within [now - window_seconds, now].
    """

    window_seconds: int = Field(
        ...,
        ge=MIN_WINDOW_SECONDS,
        le=MAX_WINDOW_SECONDS,
        description="Duration of the evaluation window in seconds",
    )
    aggregation_type: Literal["COUNT", "MAX", "MIN", "AVG", "LATEST"] = Field(
        default="LATEST",
        description="How windowed events are aggregated before condition evaluation",
    )
    aggregation_field: str | None = Field(
        default=None,
        description="Payload numeric field to aggregate (required for MAX, MIN, AVG)",
    )
    min_events: int = Field(
        default=1,
        ge=1,
        le=50,
        description="Minimum number of events required within window to satisfy condition",
    )

    @model_validator(mode="after")
    def validate_aggregation_field(self) -> TimeWindowConfig:
        if self.aggregation_type in ("MAX", "MIN", "AVG") and not self.aggregation_field:
            raise RuleValidationError(
                f"aggregation_field is required when aggregation_type is '{self.aggregation_type}'."
            )
        return self


# ── Operational Rule Definition ───────────────────────────────────────────────


class OperationalRule(HospitalOpsBaseModel):
    """
    Versioned, declarative operational rule definition.
    Persisted in 'operational_rules' collection.
    """

    rule_id: str = Field(..., description="Stable rule identifier, e.g. rule_cap_001")
    name: str = Field(..., min_length=3, max_length=120, description="Human-readable rule name")
    description: str = Field(..., min_length=5, max_length=500, description="Rule description")
    domain: RuleDomain = Field(..., description="Operational domain governed")
    version: int = Field(default=1, ge=1, description="Sequential rule version")
    is_active: bool = Field(default=True, description="Whether rule is active for evaluation")
    supported_event_types: list[EventType] = Field(
        ...,
        min_length=1,
        description="List of event types this rule evaluates against",
    )
    allowed_categories: list[EventCategory] = Field(
        ...,
        min_length=1,
        description="List of event categories this rule is allowed to consume (preserves epistemic boundaries)",
    )
    facility_id: str | None = Field(
        default=None,
        description="Facility scope (None = hospital-wide / all facilities)",
    )
    department_id: str | None = Field(
        default=None,
        description="Department scope (None = department-agnostic)",
    )
    severity: RuleSeverity = Field(
        default=RuleSeverity.MEDIUM,
        description="Severity level assigned to matched findings",
    )
    condition: SingleCondition | CompositeCondition = Field(
        ...,
        description="Declarative safe condition tree to evaluate",
    )
    time_window: TimeWindowConfig | None = Field(
        default=None,
        description="Optional time-window aggregation configuration",
    )
    owner: str | None = Field(
        default=None,
        description="Administrator or department owner responsible for rule maintenance",
    )
    provenance_policy_ref: str | None = Field(
        default=None,
        description="Reference to approved operational policy or administrative guideline",
    )
    is_illustrative: bool = Field(
        default=False,
        description="Marks demonstration/test rules so they are never mistaken for clinical or hospital policy",
    )
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("rule_id")
    @classmethod
    def validate_rule_id(cls, v: str) -> str:
        trimmed = v.strip()
        if not re.match(r"^[a-zA-Z0-9_\-\.]{3,64}$", trimmed):
            raise RuleValidationError(
                f"Rule ID '{trimmed}' must be 3-64 alphanumeric characters, underscores, hyphens, or dots."
            )
        return trimmed

    @field_validator("allowed_categories")
    @classmethod
    def validate_allowed_categories(cls, v: list[EventCategory]) -> list[EventCategory]:
        if not v:
            raise RuleValidationError("Rule must explicitly specify at least one allowed EventCategory.")
        return list(set(v))


# ── Rule Evaluation Record ────────────────────────────────────────────────────


def compute_evaluation_id(rule_id: str, rule_version: int, source_event_ids: list[str]) -> str:
    """
    Generate deterministic evaluation identity to prevent duplicate evaluation records.
    SHA-256 digest over rule_id + rule_version + sorted(source_event_ids).
    """
    sorted_ids = sorted(source_event_ids)
    key_str = f"{rule_id}:{rule_version}:{':'.join(sorted_ids)}"
    digest = hashlib.sha256(key_str.encode("utf-8")).hexdigest()[:24]
    return f"eval_{digest}"


class RuleEvaluationRecord(HospitalOpsBaseModel):
    """
    Immutable, audited record of an operational rule evaluation.
    Persisted in 'rule_evaluations' collection.
    """

    evaluation_id: str = Field(..., description="Deterministic unique evaluation identity")
    rule_id: str = Field(..., description="ID of the evaluated rule")
    rule_version: int = Field(..., ge=1, description="Exact version of the rule at evaluation time")
    rule_name: str = Field(..., description="Rule name at evaluation time")
    domain: RuleDomain = Field(..., description="Operational domain")
    severity: RuleSeverity = Field(..., description="Rule severity")
    facility_id: str = Field(..., description="Facility boundary of the evaluation")
    department_id: str | None = Field(default=None, description="Department boundary if applicable")
    source_event_ids: list[str] = Field(
        ...,
        min_length=1,
        description="Authoritative list of source event IDs that formed the evaluation evidence",
    )
    status: RuleEvaluationStatus = Field(..., description="Evaluation outcome status")
    matched: bool = Field(..., description="True if condition matched, False otherwise")
    evaluated_at: datetime = Field(default_factory=utc_now)
    source_occurred_at: datetime = Field(
        ...,
        description="Occurrence timestamp of the latest source event evaluated",
    )
    evidence_references: dict[str, Any] = Field(
        default_factory=dict,
        description="Observed field values and comparison thresholds used in evaluation",
    )
    condition_explanation: str = Field(
        ...,
        description="Human-readable explanation of why the rule matched or did not match",
    )
    requires_human_review: bool = Field(
        default=True,
        description="Healthcare safety invariant: operational evaluations require human confirmation",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Supplementary execution metadata (e.g., worker_id, latency_ms)",
    )


# ── Consumer Processing Record ────────────────────────────────────────────────


class EventProcessingRecord(HospitalOpsBaseModel):
    """
    Durable tracking of event consumption and worker lease state.
    Persisted in 'event_processing_records' collection.
    """

    event_id: str = Field(..., description="ID of the operational event being processed")
    facility_id: str = Field(..., description="Facility ID for tenant-aware processing")
    event_type: str = Field(..., description="Type of event")
    category: str = Field(..., description="Category of event")
    status: ProcessingStatus = Field(
        default=ProcessingStatus.PENDING,
        description="Current processing lifecycle status",
    )
    attempts: int = Field(default=0, ge=0, description="Number of processing attempts")
    max_attempts: int = Field(default=3, ge=1, description="Maximum retry attempts before quarantine")
    worker_id: str | None = Field(
        default=None,
        description="Identity of worker holding active lease",
    )
    lease_expires_at: datetime | None = Field(
        default=None,
        description="Lease expiration timestamp to recover stuck/crashed worker claims",
    )
    first_attempted_at: datetime | None = Field(default=None)
    last_attempted_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    error_message: str | None = Field(default=None)
    rules_evaluated_count: int = Field(default=0, ge=0)
    rules_matched_count: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
