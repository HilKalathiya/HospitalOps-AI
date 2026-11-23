"""
HospitalOps AI — Operational Event Taxonomy & Registry (Milestone 6, Chunk 6.1).

Defines the authoritative catalog of domain events, documenting:
- What happened
- Permitted source components
- Epistemic classification (fact vs derived calculation)
- Payload schemas
- Rule engine consumability (for future Chunk 6.2 integration)
"""

from __future__ import annotations

from pydantic import Field

from app.events.contracts import (
    EntityType,
    EventCategory,
    EventType,
)
from app.models.base import HospitalOpsBaseModel


class EventDefinition(HospitalOpsBaseModel):
    """Metadata specification for a registered event type."""

    event_type: EventType
    description: str
    category: EventCategory
    entity_type: EntityType
    allowed_sources: list[str]
    is_observed_fact: bool = Field(
        description="True if this event records an empirical hospital fact; False if analytical/synthetic"
    )
    payload_schema_name: str
    can_trigger_rules: bool = Field(
        default=True,
        description="Whether this event type is eligible for rule engine evaluation in Chunk 6.2",
    )
    data_classification: str = "INTERNAL_OPERATIONAL_TELEMETRY"


EVENT_TAXONOMY_CATALOG: dict[EventType, EventDefinition] = {
    # ── Operational Capacity ──────────────────────────────────────────────────
    EventType.OPERATIONS_CAPACITY_UPDATED: EventDefinition(
        event_type=EventType.OPERATIONS_CAPACITY_UPDATED,
        description="Departmental bed capacity, census, and occupancy rate updated from operational tracking.",
        category=EventCategory.OPERATIONAL_FACT,
        entity_type=EntityType.DEPARTMENT,
        allowed_sources=["hospitalops.beds_service", "hospitalops.capacity_monitor"],
        is_observed_fact=True,
        payload_schema_name="CapacityUpdatedPayload",
        can_trigger_rules=True,
    ),
    EventType.OPERATIONS_BED_STATUS_CHANGED: EventDefinition(
        event_type=EventType.OPERATIONS_BED_STATUS_CHANGED,
        description="Individual bed status transitioned (e.g. available, occupied, maintenance, blocked).",
        category=EventCategory.OPERATIONAL_FACT,
        entity_type=EntityType.BED,
        allowed_sources=["hospitalops.beds_service", "hospitalops.bed_manager"],
        is_observed_fact=True,
        payload_schema_name="BedStatusChangedPayload",
        can_trigger_rules=True,
    ),
    EventType.OPERATIONS_RESOURCE_AVAILABILITY_CHANGED: EventDefinition(
        event_type=EventType.OPERATIONS_RESOURCE_AVAILABILITY_CHANGED,
        description="Non-bed physical equipment or resource units availability adjusted.",
        category=EventCategory.OPERATIONAL_FACT,
        entity_type=EntityType.RESOURCE,
        allowed_sources=["hospitalops.resource_service"],
        is_observed_fact=True,
        payload_schema_name="ResourceAvailabilityChangedPayload",
        can_trigger_rules=True,
    ),
    # ── Admissions & Throughput ───────────────────────────────────────────────
    EventType.OPERATIONS_ADMISSION_RECORDED: EventDefinition(
        event_type=EventType.OPERATIONS_ADMISSION_RECORDED,
        description="New patient operational admission recorded in department.",
        category=EventCategory.OPERATIONAL_FACT,
        entity_type=EntityType.ADMISSION,
        allowed_sources=["hospitalops.admission_service"],
        is_observed_fact=True,
        payload_schema_name="AdmissionRecordedPayload",
        can_trigger_rules=True,
    ),
    EventType.OPERATIONS_DISCHARGE_RECORDED: EventDefinition(
        event_type=EventType.OPERATIONS_DISCHARGE_RECORDED,
        description="Patient operational discharge completed, freeing bed capacity.",
        category=EventCategory.OPERATIONAL_FACT,
        entity_type=EntityType.ADMISSION,
        allowed_sources=["hospitalops.admission_service"],
        is_observed_fact=True,
        payload_schema_name="DischargeRecordedPayload",
        can_trigger_rules=True,
    ),
    EventType.OPERATIONS_TRANSFER_RECORDED: EventDefinition(
        event_type=EventType.OPERATIONS_TRANSFER_RECORDED,
        description="Patient inter-department transfer executed (e.g. step-down to floor).",
        category=EventCategory.OPERATIONAL_FACT,
        entity_type=EntityType.ADMISSION,
        allowed_sources=["hospitalops.admission_service"],
        is_observed_fact=True,
        payload_schema_name="TransferRecordedPayload",
        can_trigger_rules=True,
    ),
    # ── Forecasting ───────────────────────────────────────────────────────────
    EventType.FORECAST_COMPLETED: EventDefinition(
        event_type=EventType.FORECAST_COMPLETED,
        description="Statistical or machine learning forecast model run generated predictions.",
        category=EventCategory.ANALYTICAL_OUTPUT,
        entity_type=EntityType.FORECAST,
        allowed_sources=["hospitalops.forecast_service"],
        is_observed_fact=False,
        payload_schema_name="ForecastCompletedPayload",
        can_trigger_rules=True,
    ),
    EventType.FORECAST_FAILED: EventDefinition(
        event_type=EventType.FORECAST_FAILED,
        description="Forecasting inference or pipeline failed to execute.",
        category=EventCategory.ANALYTICAL_OUTPUT,
        entity_type=EntityType.FORECAST,
        allowed_sources=["hospitalops.forecast_service"],
        is_observed_fact=False,
        payload_schema_name="ForecastFailedPayload",
        can_trigger_rules=True,
    ),
    # ── Simulation ────────────────────────────────────────────────────────────
    EventType.SIMULATION_COMPLETED: EventDefinition(
        event_type=EventType.SIMULATION_COMPLETED,
        description="Discrete-time what-if surge or capacity alteration simulation finished.",
        category=EventCategory.ANALYTICAL_OUTPUT,
        entity_type=EntityType.SIMULATION,
        allowed_sources=["hospitalops.simulation_service"],
        is_observed_fact=False,
        payload_schema_name="SimulationCompletedPayload",
        can_trigger_rules=True,
    ),
    EventType.SIMULATION_FAILED: EventDefinition(
        event_type=EventType.SIMULATION_FAILED,
        description="What-if simulation execution failed or aborted.",
        category=EventCategory.ANALYTICAL_OUTPUT,
        entity_type=EntityType.SIMULATION,
        allowed_sources=["hospitalops.simulation_service"],
        is_observed_fact=False,
        payload_schema_name="SimulationFailedPayload",
        can_trigger_rules=True,
    ),
    # ── Optimization ──────────────────────────────────────────────────────────
    EventType.OPTIMIZATION_COMPLETED: EventDefinition(
        event_type=EventType.OPTIMIZATION_COMPLETED,
        description="Constrained mixed-integer linear programming (MILP) solver found allocation plan.",
        category=EventCategory.ANALYTICAL_OUTPUT,
        entity_type=EntityType.OPTIMIZATION,
        allowed_sources=["hospitalops.optimization_service"],
        is_observed_fact=False,
        payload_schema_name="OptimizationCompletedPayload",
        can_trigger_rules=True,
    ),
    EventType.OPTIMIZATION_FAILED: EventDefinition(
        event_type=EventType.OPTIMIZATION_FAILED,
        description="Mathematical optimization solver encountered infeasibility or failure.",
        category=EventCategory.ANALYTICAL_OUTPUT,
        entity_type=EntityType.OPTIMIZATION,
        allowed_sources=["hospitalops.optimization_service"],
        is_observed_fact=False,
        payload_schema_name="OptimizationFailedPayload",
        can_trigger_rules=True,
    ),
    # ── Multi-Agent Platform Execution ────────────────────────────────────────
    EventType.AGENT_EXECUTION_COMPLETED: EventDefinition(
        event_type=EventType.AGENT_EXECUTION_COMPLETED,
        description="Supervisor-and-specialist multi-agent execution completed synthesis.",
        category=EventCategory.AGENT_DECISION_SUPPORT,
        entity_type=EntityType.AGENT_EXECUTION,
        allowed_sources=["hospitalops.agent_orchestrator", "hospitalops.multi_agent_coordinator"],
        is_observed_fact=False,
        payload_schema_name="AgentExecutionCompletedPayload",
        can_trigger_rules=False,
    ),
    EventType.AGENT_EXECUTION_FAILED: EventDefinition(
        event_type=EventType.AGENT_EXECUTION_FAILED,
        description="Multi-agent coordination run aborted or failed.",
        category=EventCategory.AGENT_DECISION_SUPPORT,
        entity_type=EntityType.AGENT_EXECUTION,
        allowed_sources=["hospitalops.agent_orchestrator", "hospitalops.multi_agent_coordinator"],
        is_observed_fact=False,
        payload_schema_name="AgentExecutionFailedPayload",
        can_trigger_rules=True,
    ),
    EventType.AGENT_EXECUTION_REQUIRES_REVIEW: EventDefinition(
        event_type=EventType.AGENT_EXECUTION_REQUIRES_REVIEW,
        description="Multi-agent synthesis requires human operational review before any action.",
        category=EventCategory.GOVERNANCE,
        entity_type=EntityType.AGENT_EXECUTION,
        allowed_sources=["hospitalops.agent_orchestrator", "hospitalops.multi_agent_coordinator"],
        is_observed_fact=False,
        payload_schema_name="AgentExecutionRequiresReviewPayload",
        can_trigger_rules=True,
    ),
}


def get_event_definition(event_type: EventType) -> EventDefinition | None:
    """Retrieve catalog metadata for a given event type."""
    return EVENT_TAXONOMY_CATALOG.get(event_type)


def get_all_event_definitions() -> list[EventDefinition]:
    """Retrieve all documented event definitions."""
    return list(EVENT_TAXONOMY_CATALOG.values())
