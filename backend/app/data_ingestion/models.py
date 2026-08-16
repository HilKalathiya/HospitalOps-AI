"""
HospitalOps AI — Data Ingestion Models.

Contains the schema definitions for Historical Admissions (Hero DMC),
Historical Hospital Capacity (NHSN), and Ingestion Runs.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import Field

from app.models.base import HospitalOpsBaseModel, TimestampedModel


class IngestionStatus(str, Enum):
    """Status of an ingestion run."""

    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class DatasetName(str, Enum):
    """The supported historical datasets."""

    HERO_DMC_ADMISSIONS = "HERO_DMC_ADMISSIONS"
    NHSN_HISTORICAL_HOSPITAL_CAPACITY = "NHSN_HISTORICAL_HOSPITAL_CAPACITY"


class DataIngestionRunDocument(TimestampedModel):
    """
    Tracks a data ingestion run.
    Stored in 'data_ingestion_runs'.
    """
    id: str | None = Field(default=None, alias="_id", description="MongoDB document ID.")
    run_id: str = Field(description="Unique identifier for the run.")
    dataset_name: DatasetName = Field(description="Which dataset this run processed.")
    source_filename: str = Field(description="Filename of the source data.")
    source_hash: str = Field(description="SHA256 hash of the source file.")
    started_at: datetime = Field(description="When the run started.")
    completed_at: datetime | None = Field(default=None, description="When the run completed.")
    status: IngestionStatus = Field(default=IngestionStatus.RUNNING)

    rows_read: int = Field(default=0)
    rows_valid: int = Field(default=0)
    rows_invalid: int = Field(default=0)
    rows_inserted: int = Field(default=0)
    rows_updated: int = Field(default=0)
    rows_skipped: int = Field(default=0)
    duplicate_rows: int = Field(default=0)

    error_summary: list[dict[str, Any]] = Field(default_factory=list)


class HistoricalAdmissionDocument(HospitalOpsBaseModel):
    """
    Normalized historical admission record from Hero DMC.
    Stored in 'historical_admissions'.
    """
    id: str | None = Field(default=None, alias="_id")
    ingestion_run_id: str = Field(description="Reference to data_ingestion_runs.run_id.")
    source_record_id: str = Field(description="Stable identifier (e.g. MRD No + Date or SNO).")
    source_hash: str = Field(description="Source file hash for idempotency checking.")

    # Normalized fields
    admission_date: datetime | None = Field(default=None)
    discharge_date: datetime | None = Field(default=None)
    age: int | None = Field(default=None)
    gender: str | None = Field(default=None)
    rural: str | None = Field(default=None)
    admission_type: str | None = Field(default=None)
    outcome: str | None = Field(default=None)
    duration_of_stay: int | None = Field(default=None)
    duration_of_icu_stay: int | None = Field(default=None)

    # Optional clinical mappings
    diagnoses: list[str] = Field(default_factory=list)

    # Audit timestamps
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class HistoricalCapacityDocument(HospitalOpsBaseModel):
    """
    Normalized historical hospital capacity from NHSN.
    Stored in 'historical_hospital_capacity'.
    """
    id: str | None = Field(default=None, alias="_id")
    ingestion_run_id: str = Field(description="Reference to data_ingestion_runs.run_id.")
    source_hash: str = Field(description="Source file hash.")

    # Natural keys
    week_ending_date: datetime = Field(description="End date of the reporting week.")
    geographic_aggregation: str = Field(description="Jurisdiction / state.")

    # Normalized metrics (use None if missing or invalid)
    inpatient_beds: int | None = Field(default=None)
    inpatient_beds_occupied: int | None = Field(default=None)
    icu_beds: int | None = Field(default=None)
    icu_beds_occupied: int | None = Field(default=None)

    pediatric_inpatient_beds: int | None = Field(default=None)
    pediatric_inpatient_beds_occupied: int | None = Field(default=None)
    adult_inpatient_beds: int | None = Field(default=None)
    adult_inpatient_beds_occupied: int | None = Field(default=None)

    adult_icu_beds: int | None = Field(default=None)
    adult_icu_beds_occupied: int | None = Field(default=None)
    pediatric_icu_beds: int | None = Field(default=None)
    pediatric_icu_beds_occupied: int | None = Field(default=None)

    total_covid_admissions: int | None = Field(default=None)
    total_influenza_admissions: int | None = Field(default=None)
    total_rsv_admissions: int | None = Field(default=None)

    # Audit timestamps
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
