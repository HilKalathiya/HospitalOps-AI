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
    MIMIC_IV_CLINICAL = "MIMIC_IV_CLINICAL"


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


class HistoricalICUStayDocument(HospitalOpsBaseModel):
    """
    Normalized patient-level ICU stay record from MIMIC-IV v3.1.
    Stored in 'historical_icu_stays'.

    NOTE ON TEMPORAL VALIDITY & INDEPENDENT DATE SHIFTING:
    MIMIC-IV patient dates are shifted into future years (2100-2200)
    independently per subject_id to preserve privacy.
    Dates (intime, outtime) are patient-relative and MUST NOT be
    aggregated across patients to fabricate a calendar-wide hospital daily
    admissions or occupancy time series.
    The primary target for this dataset is patient-level or stay-level
    clinical prediction, such as ICU length of stay (los) or in-hospital mortality.
    """

    id: str | None = Field(default=None, alias="_id")
    ingestion_run_id: str = Field(description="Reference to data_ingestion_runs.run_id.")
    source_hash: str = Field(description="Source file hash for idempotency checking.")

    # Core Identifiers
    subject_id: int = Field(description="Patient identifier.")
    hadm_id: int | None = Field(default=None, description="Hospital admission identifier.")
    stay_id: int = Field(description="Unique ICU stay identifier (natural key).")

    # ICU Stay Details
    first_careunit: str | None = Field(default=None, description="Initial ICU unit type.")
    last_careunit: str | None = Field(default=None, description="Final ICU unit type.")
    intime: datetime | None = Field(default=None, description="Patient-shifted ICU admission datetime.")
    outtime: datetime | None = Field(default=None, description="Patient-shifted ICU discharge datetime.")
    los: float | None = Field(
        default=None, description="Length of stay in ICU in fractional days (ground truth target)."
    )

    # Demographics & Clinical Context (from admissions/patients tables)
    admission_type: str | None = Field(default=None, description="Admission acuity/type.")
    admission_location: str | None = Field(default=None, description="Admission origin location.")
    discharge_location: str | None = Field(default=None, description="Discharge destination location.")
    hospital_expire_flag: int | None = Field(
        default=None, description="In-hospital mortality flag (0 or 1)."
    )
    gender: str | None = Field(default=None, description="Patient gender (M/F).")
    anchor_age: int | None = Field(default=None, description="Patient age at anchor year.")

    # Audit timestamps
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
