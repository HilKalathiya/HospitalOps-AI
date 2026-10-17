"""
HospitalOps AI — Simulation domain model.

Collection: simulation_runs

Persistence and API schemas for the What-if Simulation Engine (Milestone 3, Chunk 3.1).
Simulations are strictly read-only projections evaluated against current or baseline
operational state. They never mutate live beds, admissions, or resources.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from app.models.base import HospitalOpsBaseModel, TimestampedModel


class ScenarioType(str, Enum):
    """Supported simulation scenario archetypes."""

    ADMISSION_SURGE = "ADMISSION_SURGE"
    BED_CAPACITY_CHANGE = "BED_CAPACITY_CHANGE"
    RESOURCE_BOTTLENECK = "RESOURCE_BOTTLENECK"


class SimulationTimeseriesPoint(HospitalOpsBaseModel):
    """Day-by-day projected trajectory point in the simulation horizon."""

    step: int = Field(description="Step offset in the simulation horizon (1-indexed).")
    date: str = Field(description="Projected calendar date (YYYY-MM-DD).")
    projected_admissions: float = Field(description="Simulated daily incoming admissions.")
    projected_discharges: float = Field(description="Simulated daily discharges based on LOS.")
    projected_occupied_beds: float = Field(description="Simulated bed occupancy count.")
    projected_occupancy_pct: float = Field(description="Simulated occupancy percentage.")
    projected_bed_deficit: float = Field(
        description="Projected bed shortage count (0 if capacity >= occupied)."
    )
    projected_resource_demand: float | None = Field(
        default=None, description="Projected demand for specific equipment/staff."
    )
    projected_resource_deficit: float | None = Field(
        default=None, description="Projected equipment/staff shortage count."
    )


class ShortagePeriod(HospitalOpsBaseModel):
    """Contiguous timeframe where demand exceeds available capacity."""

    start_date: str
    end_date: str
    peak_deficit: float
    shortage_type: str = "BEDS"
    description: str


class SimulationParameters(HospitalOpsBaseModel):
    """Input parameters for a deterministic what-if scenario run."""

    scenario_type: ScenarioType = Field(
        default=ScenarioType.ADMISSION_SURGE,
        description="Scenario archetype to evaluate.",
    )
    horizon_days: int = Field(
        default=14,
        ge=1,
        le=90,
        description="Simulation horizon in days (1 to 90).",
    )
    department_id: str | None = Field(
        default=None,
        description="Target department filter, or None for hospital-wide simulation.",
    )
    admission_surge_pct: float = Field(
        default=0.0,
        ge=-100.0,
        le=500.0,
        description="Hypothetical percentage change in admissions (e.g. +20.0 for 20% surge).",
    )
    capacity_delta_beds: int = Field(
        default=0,
        description="Hypothetical bed capacity adjustment (+surge beds or converted beds).",
    )
    avg_los_days: float = Field(
        default=5.0,
        ge=0.5,
        le=60.0,
        description="Expected average length of stay in days for turnover modeling.",
    )
    resource_type: str | None = Field(
        default=None,
        description="Resource type evaluated in bottleneck scenarios (e.g. VENTILATOR, MONITOR).",
    )
    resource_ratio_per_bed: float | None = Field(
        default=None,
        ge=0.0,
        le=10.0,
        description="Required resource ratio per occupied bed (e.g. 0.8 ventilators per bed).",
    )
    resource_availability_delta: int = Field(
        default=0,
        description="Hypothetical change in operational resource inventory count.",
    )

    @field_validator("resource_ratio_per_bed")
    @classmethod
    def validate_resource_ratio(cls, v: float | None, info: Any) -> float | None:
        return v


class SimulationOutcome(HospitalOpsBaseModel):
    """Comprehensive projected outcomes from a simulation execution."""

    peak_occupancy_pct: float = Field(description="Maximum projected occupancy percentage.")
    peak_bed_deficit: float = Field(description="Maximum bed shortage at any step in horizon.")
    days_in_shortage: int = Field(description="Number of days where bed deficit > 0.")
    total_unmet_admissions: float = Field(
        description="Cumulative unmet patient admissions due to lack of beds."
    )
    bottleneck_resource: str | None = Field(
        default=None, description="Primary resource constraint identified."
    )
    peak_resource_deficit: float | None = Field(
        default=None, description="Maximum resource shortage count."
    )
    shortage_periods: list[ShortagePeriod] = Field(
        default_factory=list, description="Contiguous shortage spans identified."
    )
    projections: list[SimulationTimeseriesPoint] = Field(
        default_factory=list, description="Day-by-day projected simulation trajectory."
    )
    summary: str = Field(description="Executive plain-language summary of simulation outcome.")
    operational_implications: list[str] = Field(
        default_factory=list, description="Key operational insights and warnings."
    )


class SimulationRunDocument(TimestampedModel):
    """
    Internal MongoDB representation of a simulation run in the 'simulation_runs' collection.
    """

    id: str | None = Field(default=None, alias="_id", description="MongoDB document ID.")
    simulation_id: str = Field(description="Stable application UUID for the simulation run.")
    scenario_name: str = Field(max_length=200, description="Human-readable scenario title.")
    scenario_type: ScenarioType
    base_timestamp: datetime = Field(description="UTC timestamp representing the simulation origin.")
    parameters: SimulationParameters
    baseline_summary: dict = Field(
        default_factory=dict, description="Snapshot of operational baseline values at run time."
    )
    outcome: SimulationOutcome
    created_by: str = Field(description="User ID who executed the simulation.")


# ── API Schemas ───────────────────────────────────────────────────────────────


class SimulationRequest(HospitalOpsBaseModel):
    """Request payload to execute a new what-if simulation."""

    scenario_name: str = Field(min_length=3, max_length=200)
    parameters: SimulationParameters


class SimulationResponse(HospitalOpsBaseModel):
    """Public response envelope for simulation execution results."""

    simulation_id: str
    scenario_name: str
    scenario_type: ScenarioType
    base_timestamp: datetime
    parameters: SimulationParameters
    baseline_summary: dict
    outcome: SimulationOutcome
    created_by: str
    created_at: datetime
