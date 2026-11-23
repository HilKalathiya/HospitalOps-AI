"""
HospitalOps AI — Operational Event Service (Milestone 6, Chunk 6.1).

Central domain service orchestrating event publishing, validation, idempotency,
and facility-scoped event querying across all analytical and operational components.
"""

from __future__ import annotations

import logging
from datetime import datetime

from app.events.contracts import (
    AdmissionRecordedPayload,
    AgentExecutionCompletedPayload,
    AgentExecutionFailedPayload,
    AgentExecutionRequiresReviewPayload,
    BedStatusChangedPayload,
    CapacityUpdatedPayload,
    DischargeRecordedPayload,
    EntityType,
    EventType,
    ForecastCompletedPayload,
    ForecastFailedPayload,
    OperationalEvent,
    OptimizationCompletedPayload,
    OptimizationFailedPayload,
    ResourceAvailabilityChangedPayload,
    SimulationCompletedPayload,
    SimulationFailedPayload,
    TransferRecordedPayload,
)
from app.events.publisher import EventPublisher, OperationalEventPublisher
from app.events.taxonomy import EVENT_TAXONOMY_CATALOG
from app.models.base import utc_now
from app.repositories.events import EventQueryFilter, OperationalEventRepository

logger = logging.getLogger(__name__)


class OperationalEventService:
    """
    High-level domain service providing strongly-typed helpers for publishing
    operational events, and query methods with facility tenant isolation.
    """

    def __init__(
        self,
        repository: OperationalEventRepository,
        publisher: EventPublisher | None = None,
    ) -> None:
        self.repository = repository
        self.publisher = publisher or OperationalEventPublisher(repository)

    # ── Generic Publishing ────────────────────────────────────────────────────

    async def publish_event(self, event: OperationalEvent) -> tuple[OperationalEvent, bool]:
        """Publish a pre-constructed OperationalEvent envelope."""
        return await self.publisher.publish(event)

    # ── Operational Capacity Helpers ──────────────────────────────────────────

    async def publish_capacity_updated(
        self,
        department_id: str,
        total_beds: int,
        occupied_beds: int,
        operational_occupancy_rate: float,
        available_beds: int,
        facility_id: str = "default_facility",
        correlation_id: str | None = None,
        source: str = "hospitalops.beds_service",
        occurred_at: datetime | None = None,
    ) -> tuple[OperationalEvent, bool]:
        payload = CapacityUpdatedPayload(
            department_id=department_id,
            total_beds=total_beds,
            occupied_beds=occupied_beds,
            operational_occupancy_rate=operational_occupancy_rate,
            available_beds=available_beds,
        )
        def_meta = EVENT_TAXONOMY_CATALOG[EventType.OPERATIONS_CAPACITY_UPDATED]
        event = OperationalEvent(
            event_type=EventType.OPERATIONS_CAPACITY_UPDATED,
            category=def_meta.category,
            source=source,
            entity_type=EntityType.DEPARTMENT,
            entity_id=department_id,
            facility_id=facility_id,
            correlation_id=correlation_id,
            occurred_at=occurred_at or utc_now(),
            payload=payload.model_dump(mode="json"),
        )
        return await self.publisher.publish(event)

    async def publish_bed_status_changed(
        self,
        bed_id: str,
        department_id: str,
        previous_status: str,
        new_status: str,
        reason: str | None = None,
        facility_id: str = "default_facility",
        correlation_id: str | None = None,
        source: str = "hospitalops.beds_service",
        occurred_at: datetime | None = None,
    ) -> tuple[OperationalEvent, bool]:
        payload = BedStatusChangedPayload(
            bed_id=bed_id,
            department_id=department_id,
            previous_status=previous_status,
            new_status=new_status,
            reason=reason,
        )
        def_meta = EVENT_TAXONOMY_CATALOG[EventType.OPERATIONS_BED_STATUS_CHANGED]
        event = OperationalEvent(
            event_type=EventType.OPERATIONS_BED_STATUS_CHANGED,
            category=def_meta.category,
            source=source,
            entity_type=EntityType.BED,
            entity_id=bed_id,
            facility_id=facility_id,
            correlation_id=correlation_id,
            occurred_at=occurred_at or utc_now(),
            payload=payload.model_dump(mode="json"),
        )
        return await self.publisher.publish(event)

    async def publish_resource_availability_changed(
        self,
        resource_id: str,
        resource_type: str,
        department_id: str,
        total_units: int,
        available_units: int,
        facility_id: str = "default_facility",
        correlation_id: str | None = None,
        source: str = "hospitalops.resource_service",
        occurred_at: datetime | None = None,
    ) -> tuple[OperationalEvent, bool]:
        payload = ResourceAvailabilityChangedPayload(
            resource_id=resource_id,
            resource_type=resource_type,
            department_id=department_id,
            total_units=total_units,
            available_units=available_units,
        )
        def_meta = EVENT_TAXONOMY_CATALOG[EventType.OPERATIONS_RESOURCE_AVAILABILITY_CHANGED]
        event = OperationalEvent(
            event_type=EventType.OPERATIONS_RESOURCE_AVAILABILITY_CHANGED,
            category=def_meta.category,
            source=source,
            entity_type=EntityType.RESOURCE,
            entity_id=resource_id,
            facility_id=facility_id,
            correlation_id=correlation_id,
            occurred_at=occurred_at or utc_now(),
            payload=payload.model_dump(mode="json"),
        )
        return await self.publisher.publish(event)

    # ── Admissions & Throughput Helpers ───────────────────────────────────────

    async def publish_admission_recorded(
        self,
        admission_id: str,
        department_id: str,
        admitted_at: datetime,
        acuity_level: str | None = None,
        bed_id: str | None = None,
        facility_id: str = "default_facility",
        correlation_id: str | None = None,
        source: str = "hospitalops.admission_service",
    ) -> tuple[OperationalEvent, bool]:
        payload = AdmissionRecordedPayload(
            admission_id=admission_id,
            department_id=department_id,
            admitted_at=admitted_at,
            acuity_level=acuity_level,
            bed_id=bed_id,
        )
        def_meta = EVENT_TAXONOMY_CATALOG[EventType.OPERATIONS_ADMISSION_RECORDED]
        event = OperationalEvent(
            event_type=EventType.OPERATIONS_ADMISSION_RECORDED,
            category=def_meta.category,
            source=source,
            entity_type=EntityType.ADMISSION,
            entity_id=admission_id,
            facility_id=facility_id,
            correlation_id=correlation_id,
            occurred_at=admitted_at,
            payload=payload.model_dump(mode="json"),
        )
        return await self.publisher.publish(event)

    async def publish_discharge_recorded(
        self,
        admission_id: str,
        department_id: str,
        discharged_at: datetime,
        length_of_stay_hours: float,
        facility_id: str = "default_facility",
        correlation_id: str | None = None,
        source: str = "hospitalops.admission_service",
    ) -> tuple[OperationalEvent, bool]:
        payload = DischargeRecordedPayload(
            admission_id=admission_id,
            department_id=department_id,
            discharged_at=discharged_at,
            length_of_stay_hours=length_of_stay_hours,
        )
        def_meta = EVENT_TAXONOMY_CATALOG[EventType.OPERATIONS_DISCHARGE_RECORDED]
        event = OperationalEvent(
            event_type=EventType.OPERATIONS_DISCHARGE_RECORDED,
            category=def_meta.category,
            source=source,
            entity_type=EntityType.ADMISSION,
            entity_id=admission_id,
            facility_id=facility_id,
            correlation_id=correlation_id,
            occurred_at=discharged_at,
            payload=payload.model_dump(mode="json"),
        )
        return await self.publisher.publish(event)

    async def publish_transfer_recorded(
        self,
        admission_id: str,
        source_department_id: str,
        target_department_id: str,
        transferred_at: datetime,
        reason: str | None = None,
        facility_id: str = "default_facility",
        correlation_id: str | None = None,
        source: str = "hospitalops.admission_service",
    ) -> tuple[OperationalEvent, bool]:
        payload = TransferRecordedPayload(
            admission_id=admission_id,
            source_department_id=source_department_id,
            target_department_id=target_department_id,
            transferred_at=transferred_at,
            reason=reason,
        )
        def_meta = EVENT_TAXONOMY_CATALOG[EventType.OPERATIONS_TRANSFER_RECORDED]
        event = OperationalEvent(
            event_type=EventType.OPERATIONS_TRANSFER_RECORDED,
            category=def_meta.category,
            source=source,
            entity_type=EntityType.ADMISSION,
            entity_id=admission_id,
            facility_id=facility_id,
            correlation_id=correlation_id,
            occurred_at=transferred_at,
            payload=payload.model_dump(mode="json"),
        )
        return await self.publisher.publish(event)

    # ── Forecasting Helpers ───────────────────────────────────────────────────

    async def publish_forecast_completed(
        self,
        forecast_id: str,
        target_metric: str,
        horizon_days: int,
        model_type: str,
        peak_predicted_value: float,
        model_version: str | None = None,
        facility_id: str = "default_facility",
        correlation_id: str | None = None,
        source: str = "hospitalops.forecast_service",
        occurred_at: datetime | None = None,
    ) -> tuple[OperationalEvent, bool]:
        payload = ForecastCompletedPayload(
            forecast_id=forecast_id,
            target_metric=target_metric,
            horizon_days=horizon_days,
            model_type=model_type,
            peak_predicted_value=peak_predicted_value,
            model_version=model_version,
        )
        def_meta = EVENT_TAXONOMY_CATALOG[EventType.FORECAST_COMPLETED]
        event = OperationalEvent(
            event_type=EventType.FORECAST_COMPLETED,
            category=def_meta.category,
            source=source,
            entity_type=EntityType.FORECAST,
            entity_id=forecast_id,
            facility_id=facility_id,
            correlation_id=correlation_id,
            occurred_at=occurred_at or utc_now(),
            payload=payload.model_dump(mode="json"),
        )
        return await self.publisher.publish(event)

    async def publish_forecast_failed(
        self,
        forecast_id: str,
        target_metric: str,
        model_type: str,
        error_code: str,
        error_message: str,
        facility_id: str = "default_facility",
        correlation_id: str | None = None,
        source: str = "hospitalops.forecast_service",
        occurred_at: datetime | None = None,
    ) -> tuple[OperationalEvent, bool]:
        payload = ForecastFailedPayload(
            forecast_id=forecast_id,
            target_metric=target_metric,
            model_type=model_type,
            error_code=error_code,
            error_message=error_message,
        )
        def_meta = EVENT_TAXONOMY_CATALOG[EventType.FORECAST_FAILED]
        event = OperationalEvent(
            event_type=EventType.FORECAST_FAILED,
            category=def_meta.category,
            source=source,
            entity_type=EntityType.FORECAST,
            entity_id=forecast_id,
            facility_id=facility_id,
            correlation_id=correlation_id,
            occurred_at=occurred_at or utc_now(),
            payload=payload.model_dump(mode="json"),
        )
        return await self.publisher.publish(event)

    # ── Simulation Helpers ────────────────────────────────────────────────────

    async def publish_simulation_completed(
        self,
        scenario_id: str,
        scenario_type: str,
        peak_occupancy_percentage: float,
        shortage_days_count: int,
        bottleneck_resource: str | None = None,
        facility_id: str = "default_facility",
        correlation_id: str | None = None,
        source: str = "hospitalops.simulation_service",
        occurred_at: datetime | None = None,
    ) -> tuple[OperationalEvent, bool]:
        payload = SimulationCompletedPayload(
            scenario_id=scenario_id,
            scenario_type=scenario_type,
            peak_occupancy_percentage=peak_occupancy_percentage,
            shortage_days_count=shortage_days_count,
            bottleneck_resource=bottleneck_resource,
        )
        def_meta = EVENT_TAXONOMY_CATALOG[EventType.SIMULATION_COMPLETED]
        event = OperationalEvent(
            event_type=EventType.SIMULATION_COMPLETED,
            category=def_meta.category,
            source=source,
            entity_type=EntityType.SIMULATION,
            entity_id=scenario_id,
            facility_id=facility_id,
            correlation_id=correlation_id,
            occurred_at=occurred_at or utc_now(),
            payload=payload.model_dump(mode="json"),
        )
        return await self.publisher.publish(event)

    async def publish_simulation_failed(
        self,
        scenario_id: str,
        scenario_type: str,
        error_code: str,
        error_message: str,
        facility_id: str = "default_facility",
        correlation_id: str | None = None,
        source: str = "hospitalops.simulation_service",
        occurred_at: datetime | None = None,
    ) -> tuple[OperationalEvent, bool]:
        payload = SimulationFailedPayload(
            scenario_id=scenario_id,
            scenario_type=scenario_type,
            error_code=error_code,
            error_message=error_message,
        )
        def_meta = EVENT_TAXONOMY_CATALOG[EventType.SIMULATION_FAILED]
        event = OperationalEvent(
            event_type=EventType.SIMULATION_FAILED,
            category=def_meta.category,
            source=source,
            entity_type=EntityType.SIMULATION,
            entity_id=scenario_id,
            facility_id=facility_id,
            correlation_id=correlation_id,
            occurred_at=occurred_at or utc_now(),
            payload=payload.model_dump(mode="json"),
        )
        return await self.publisher.publish(event)

    # ── Optimization Helpers ──────────────────────────────────────────────────

    async def publish_optimization_completed(
        self,
        optimization_id: str,
        status: str,
        reallocated_beds_count: int,
        binding_constraints_count: int,
        requires_human_review: bool = True,
        facility_id: str = "default_facility",
        correlation_id: str | None = None,
        source: str = "hospitalops.optimization_service",
        occurred_at: datetime | None = None,
    ) -> tuple[OperationalEvent, bool]:
        payload = OptimizationCompletedPayload(
            optimization_id=optimization_id,
            status=status,
            reallocated_beds_count=reallocated_beds_count,
            binding_constraints_count=binding_constraints_count,
            requires_human_review=requires_human_review,
        )
        def_meta = EVENT_TAXONOMY_CATALOG[EventType.OPTIMIZATION_COMPLETED]
        event = OperationalEvent(
            event_type=EventType.OPTIMIZATION_COMPLETED,
            category=def_meta.category,
            source=source,
            entity_type=EntityType.OPTIMIZATION,
            entity_id=optimization_id,
            facility_id=facility_id,
            correlation_id=correlation_id,
            occurred_at=occurred_at or utc_now(),
            payload=payload.model_dump(mode="json"),
        )
        return await self.publisher.publish(event)

    async def publish_optimization_failed(
        self,
        optimization_id: str,
        error_code: str,
        error_message: str,
        facility_id: str = "default_facility",
        correlation_id: str | None = None,
        source: str = "hospitalops.optimization_service",
        occurred_at: datetime | None = None,
    ) -> tuple[OperationalEvent, bool]:
        payload = OptimizationFailedPayload(
            optimization_id=optimization_id,
            error_code=error_code,
            error_message=error_message,
        )
        def_meta = EVENT_TAXONOMY_CATALOG[EventType.OPTIMIZATION_FAILED]
        event = OperationalEvent(
            event_type=EventType.OPTIMIZATION_FAILED,
            category=def_meta.category,
            source=source,
            entity_type=EntityType.OPTIMIZATION,
            entity_id=optimization_id,
            facility_id=facility_id,
            correlation_id=correlation_id,
            occurred_at=occurred_at or utc_now(),
            payload=payload.model_dump(mode="json"),
        )
        return await self.publisher.publish(event)

    # ── Platform & Multi-Agent Helpers ────────────────────────────────────────

    async def publish_agent_execution_completed(
        self,
        run_id: str,
        trace_id: str,
        agent_id: str,
        specialists_invoked: list[str],
        is_partial_result: bool = False,
        requires_human_review: bool = True,
        duration_ms: float = 0.0,
        facility_id: str = "default_facility",
        correlation_id: str | None = None,
        source: str = "hospitalops.agent_orchestrator",
        occurred_at: datetime | None = None,
    ) -> tuple[OperationalEvent, bool]:
        payload = AgentExecutionCompletedPayload(
            run_id=run_id,
            trace_id=trace_id,
            agent_id=agent_id,
            specialists_invoked=specialists_invoked,
            is_partial_result=is_partial_result,
            requires_human_review=requires_human_review,
            duration_ms=duration_ms,
        )
        def_meta = EVENT_TAXONOMY_CATALOG[EventType.AGENT_EXECUTION_COMPLETED]
        event = OperationalEvent(
            event_type=EventType.AGENT_EXECUTION_COMPLETED,
            category=def_meta.category,
            source=source,
            entity_type=EntityType.AGENT_EXECUTION,
            entity_id=run_id,
            facility_id=facility_id,
            correlation_id=correlation_id,
            occurred_at=occurred_at or utc_now(),
            payload=payload.model_dump(mode="json"),
        )
        return await self.publisher.publish(event)

    async def publish_agent_execution_failed(
        self,
        run_id: str,
        agent_id: str,
        error_code: str,
        error_message: str,
        trace_id: str | None = None,
        facility_id: str = "default_facility",
        correlation_id: str | None = None,
        source: str = "hospitalops.agent_orchestrator",
        occurred_at: datetime | None = None,
    ) -> tuple[OperationalEvent, bool]:
        payload = AgentExecutionFailedPayload(
            run_id=run_id,
            trace_id=trace_id,
            agent_id=agent_id,
            error_code=error_code,
            error_message=error_message,
        )
        def_meta = EVENT_TAXONOMY_CATALOG[EventType.AGENT_EXECUTION_FAILED]
        event = OperationalEvent(
            event_type=EventType.AGENT_EXECUTION_FAILED,
            category=def_meta.category,
            source=source,
            entity_type=EntityType.AGENT_EXECUTION,
            entity_id=run_id,
            facility_id=facility_id,
            correlation_id=correlation_id,
            occurred_at=occurred_at or utc_now(),
            payload=payload.model_dump(mode="json"),
        )
        return await self.publisher.publish(event)

    async def publish_agent_execution_requires_review(
        self,
        run_id: str,
        trace_id: str,
        agent_id: str,
        review_reason: str,
        recommendation_summary: str,
        facility_id: str = "default_facility",
        correlation_id: str | None = None,
        source: str = "hospitalops.agent_orchestrator",
        occurred_at: datetime | None = None,
    ) -> tuple[OperationalEvent, bool]:
        payload = AgentExecutionRequiresReviewPayload(
            run_id=run_id,
            trace_id=trace_id,
            agent_id=agent_id,
            review_reason=review_reason,
            recommendation_summary=recommendation_summary,
        )
        def_meta = EVENT_TAXONOMY_CATALOG[EventType.AGENT_EXECUTION_REQUIRES_REVIEW]
        event = OperationalEvent(
            event_type=EventType.AGENT_EXECUTION_REQUIRES_REVIEW,
            category=def_meta.category,
            source=source,
            entity_type=EntityType.AGENT_EXECUTION,
            entity_id=run_id,
            facility_id=facility_id,
            correlation_id=correlation_id,
            occurred_at=occurred_at or utc_now(),
            payload=payload.model_dump(mode="json"),
        )
        return await self.publisher.publish(event)

    # ── Read & Query Operations ───────────────────────────────────────────────

    async def get_event(
        self,
        event_id: str,
        facility_id: str | None = None,
    ) -> OperationalEvent | None:
        """Retrieve an operational event by ID with optional facility scoping."""
        return await self.repository.get_by_id(event_id=event_id, facility_id=facility_id)

    async def query_events(
        self,
        filters: EventQueryFilter,
    ) -> tuple[list[OperationalEvent], int]:
        """Query operational events with strict pagination and server-side filtering."""
        return await self.repository.query_events(filters)
