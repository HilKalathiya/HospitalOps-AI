"""
HospitalOps AI — MIMIC-IV Data Ingestion & Parser Tests.

Uses synthetic in-memory/temp fixtures to validate parsing, chunking,
validation rules, and idempotency without requiring access to protected raw data.
"""

import tempfile
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.data_ingestion.models import DataIngestionRunDocument, DatasetName, IngestionStatus
from app.data_ingestion.pipelines.mimic_iv import (
    MIMICIVIngestionPipeline,
    parse_datetime,
    parse_float,
    parse_int,
)


def test_mimic_parse_datetime():
    # Valid patient-shifted timestamps
    dt = parse_datetime("2180-07-23 23:50:47")
    assert dt == datetime(2180, 7, 23, 23, 50, 47, tzinfo=UTC)

    dt2 = parse_datetime("2150-11-06T17:03:17")
    assert dt2 == datetime(2150, 11, 6, 17, 3, 17, tzinfo=UTC)

    # Missing and null values
    assert parse_datetime("") is None
    assert parse_datetime("null") is None
    assert parse_datetime("NA") is None
    assert parse_datetime("None") is None
    assert parse_datetime(None) is None
    assert parse_datetime("invalid-date-string") is None


def test_mimic_parse_float():
    assert parse_float("0.410266") == pytest.approx(0.410266)
    assert parse_float(3.893252) == pytest.approx(3.893252)
    assert parse_float("0") == 0.0
    assert parse_float("") is None
    assert parse_float("null") is None
    assert parse_float("invalid") is None
    assert parse_float(None) is None


def test_mimic_parse_int():
    assert parse_int("10000032") == 10000032
    assert parse_int(29079034) == 29079034
    assert parse_int("42.0") == 42
    assert parse_int("") is None
    assert parse_int("null") is None
    assert parse_int(None) is None


@pytest.mark.asyncio
async def test_mimic_ingestion_pipeline_with_synthetic_fixtures():
    # Create synthetic icustays CSV
    icustays_csv = (
        "subject_id,hadm_id,stay_id,first_careunit,last_careunit,intime,outtime,los\n"
        "10000032,29079034,30000001,MICU,MICU,2180-07-23 23:50:47,2180-07-24 10:00:00,0.410266\n"
        "10000690,25860671,30000002,SICU,SICU,2150-11-06 17:03:17,2150-11-10 14:29:00,3.893252\n"
        "10000999,29999999,30000003,CCU,CCU,2160-01-01 00:00:00,2160-01-02 00:00:00,-1.5\n"  # Invalid negative LOS
        ",,30000004,MICU,MICU,2180-01-01 00:00:00,2180-01-02 00:00:00,1.0\n"  # Missing subject_id
    )

    admissions_csv = (
        "subject_id,hadm_id,admittime,dischtime,deathtime,admission_type,admit_provider_id,"
        "admission_location,discharge_location,insurance,language,marital_status,race,"
        "edregtime,edouttime,hospital_expire_flag\n"
        "10000032,29079034,2180-07-23 21:00:00,2180-07-24 15:00:00,,EMERGENCY,P01,EMERGENCY ROOM,HOME,Other,ENGL,SINGLE,WHITE,,0\n"
        "10000690,25860671,2150-11-06 12:00:00,2150-11-10 18:00:00,,URGENT,P02,TRANSFER,REHAB,Medicare,ENGL,MARRIED,BLACK,,1\n"
    )

    patients_csv = (
        "subject_id,gender,anchor_age,anchor_year,anchor_year_group,dod\n"
        "10000032,F,52,2180,2014 - 2016,\n"
        "10000690,M,68,2150,2017 - 2019,\n"
    )

    with tempfile.NamedTemporaryFile("w+", suffix=".csv", delete=False) as f_icu:
        f_icu.write(icustays_csv)
        f_icu.flush()
        icu_path = f_icu.name

    with tempfile.NamedTemporaryFile("w+", suffix=".csv", delete=False) as f_adm:
        f_adm.write(admissions_csv)
        f_adm.flush()
        adm_path = f_adm.name

    with tempfile.NamedTemporaryFile("w+", suffix=".csv", delete=False) as f_pat:
        f_pat.write(patients_csv)
        f_pat.flush()
        pat_path = f_pat.name

    # Mock repositories
    mock_run_repo = AsyncMock()
    mock_run_repo.get_run_by_hash.return_value = None

    async def fake_create_run(run):
        return run

    async def fake_update_run(run):
        return run

    mock_run_repo.create_run.side_effect = fake_create_run
    mock_run_repo.update_run.side_effect = fake_update_run

    mock_icu_repo = AsyncMock()
    mock_icu_repo.bulk_upsert.return_value = {"inserted": 2, "updated": 0, "skipped": 0}

    pipeline = MIMICIVIngestionPipeline(mock_run_repo, mock_icu_repo)
    result = await pipeline.process_file(
        icu_path,
        batch_size=2,
        dry_run=False,
        admissions_file=adm_path,
        patients_file=pat_path,
    )

    assert result.status == IngestionStatus.PARTIAL
    assert result.rows_read == 4
    assert result.rows_valid == 2
    assert result.rows_invalid == 2
    assert result.rows_inserted == 2
    assert len(result.error_summary) == 2

    # Verify idempotency check
    mock_run_repo.get_run_by_hash.return_value = DataIngestionRunDocument(
        run_id="run-cached",
        dataset_name=DatasetName.MIMIC_IV_CLINICAL,
        source_filename=icu_path,
        source_hash="already-hashed",
        started_at=datetime.now(tz=UTC),
        status=IngestionStatus.COMPLETED,
        rows_read=4,
        rows_valid=2,
    )

    cached_run = await pipeline.process_file(icu_path, dry_run=False)
    assert cached_run.run_id == "run-cached"
    assert cached_run.status == IngestionStatus.COMPLETED
