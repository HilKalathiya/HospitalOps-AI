"""
HospitalOps AI — MIMIC-IV ML Adapter Tests.

Validates that MIMICIVAdapter formats stay-level clinical records correctly
and protects against misusing independently shifted patient dates for cross-patient time series.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ml.adapters.mimic_iv import MIMICIVAdapter


@pytest.mark.asyncio
async def test_mimic_adapter_with_data():
    mock_repo = MagicMock()
    mock_cursor = MagicMock()

    sample_docs = [
        {
            "stay_id": 30000001,
            "subject_id": 10000032,
            "hadm_id": 29079034,
            "first_careunit": "MICU",
            "last_careunit": "MICU",
            "intime": datetime(2180, 7, 23, 23, 50, 47),
            "outtime": datetime(2180, 7, 24, 10, 0, 0),
            "los": 0.410266,
            "admission_type": "EMERGENCY",
            "admission_location": "EMERGENCY ROOM",
            "discharge_location": "HOME",
            "hospital_expire_flag": 0,
            "gender": "F",
            "anchor_age": 52,
        },
        {
            "stay_id": 30000002,
            "subject_id": 10000690,
            "hadm_id": 25860671,
            "first_careunit": "SICU",
            "last_careunit": "SICU",
            "intime": datetime(2150, 11, 6, 17, 3, 17),
            "outtime": datetime(2150, 11, 10, 14, 29, 0),
            "los": 3.893252,
            "admission_type": "URGENT",
            "admission_location": "TRANSFER",
            "discharge_location": "REHAB",
            "hospital_expire_flag": 1,
            "gender": "M",
            "anchor_age": 68,
        },
    ]

    mock_cursor.to_list = AsyncMock(return_value=sample_docs)
    mock_repo.collection.find.return_value = mock_cursor

    adapter = MIMICIVAdapter(mock_repo, target_column="los")
    dataset = await adapter.fetch_dataset()

    assert dataset.dataset_name == "mimic_iv"
    assert dataset.source_collection == "historical_icu_stays"
    assert dataset.target_column == "los"
    assert dataset.row_count == 2
    assert dataset.df["los"].tolist() == pytest.approx([0.410266, 3.893252])
    assert dataset.df["first_careunit"].tolist() == ["MICU", "SICU"]

    # Verify architectural non-misuse flags
    assert dataset.metadata["date_shifted"] is True
    assert dataset.metadata["patient_level"] is True
    assert dataset.metadata["hospital_wide_time_series"] is False


@pytest.mark.asyncio
async def test_mimic_adapter_empty():
    mock_repo = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(return_value=[])
    mock_repo.collection.find.return_value = mock_cursor

    adapter = MIMICIVAdapter(mock_repo, target_column="los")
    dataset = await adapter.fetch_dataset()

    assert dataset.dataset_name == "mimic_iv"
    assert dataset.row_count == 0
    assert dataset.metadata["total_source_records"] == 0
    assert dataset.metadata["hospital_wide_time_series"] is False
    assert "los" in dataset.df.columns
