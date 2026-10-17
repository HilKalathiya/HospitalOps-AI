"""
HospitalOps AI — MIMIC-IV ML Data Adapter.

Adapter for MIMIC-IV patient-level ICU stay records.
Extracts clinical stay records, lengths of stay (los), and clinical covariates
for patient-level trajectory and ICU stay prediction.

CRITICAL ARCHITECTURAL CONSTRAINTS:
MIMIC-IV patient dates are shifted independently per patient.
This adapter provides patient/stay-level records and explicitly flags
metadata with date_shifted=True and hospital_wide_time_series=False
to ensure dates are NEVER misused for cross-patient calendar aggregation.
"""

import logging
from typing import Any

import pandas as pd

from app.data_ingestion.repositories import HistoricalICUStaysRepository
from app.ml.adapters.base import BaseAdapter
from app.ml.contracts.dataset import MLDataset

logger = logging.getLogger(__name__)


class MIMICIVAdapter(BaseAdapter):
    """
    Adapter for MIMIC-IV Clinical ICU Stays.
    Produces a patient/stay-level tabular MLDataset targeting clinical prediction
    (e.g., ICU length of stay 'los' or mortality).
    """

    def __init__(
        self,
        repository: HistoricalICUStaysRepository,
        target_column: str = "los",
    ):
        self.repository = repository
        self.target_column = target_column

    async def fetch_dataset(self) -> MLDataset:
        # Fetch documents having the target column populated
        query: dict[str, Any] = {self.target_column: {"$ne": None}}
        cursor = self.repository.collection.find(query)
        docs = await cursor.to_list(length=None)

        base_columns = [
            "stay_id",
            "subject_id",
            "intime",
            "outtime",
            self.target_column,
            "first_careunit",
            "anchor_age",
            "gender",
            "hospital_expire_flag",
            "admission_type",
        ]

        if not docs:
            df_empty = pd.DataFrame(columns=base_columns)
            return MLDataset(
                dataset_name="mimic_iv",
                source_collection="historical_icu_stays",
                df=df_empty,
                target_column=self.target_column,
                time_column="intime",
                frequency="STAY",
                metadata={
                    "total_source_records": 0,
                    "date_shifted": True,
                    "patient_level": True,
                    "hospital_wide_time_series": False,
                    "warning": "MIMIC-IV dates are shifted independently per patient. Do not aggregate into calendar daily time series.",
                },
            )

        df_raw = pd.DataFrame(docs)

        # Ensure datetime parsing for patient-relative timestamps
        if "intime" in df_raw.columns:
            df_raw["intime"] = pd.to_datetime(df_raw["intime"]).dt.tz_localize(None)
        if "outtime" in df_raw.columns:
            df_raw["outtime"] = pd.to_datetime(df_raw["outtime"]).dt.tz_localize(None)

        # Select relevant columns that exist
        available_cols = [c for c in base_columns if c in df_raw.columns]
        df_clean = df_raw[available_cols].copy()

        # Sort by stay_id for deterministic order
        df_clean = df_clean.sort_values("stay_id").reset_index(drop=True)

        return MLDataset(
            dataset_name="mimic_iv",
            source_collection="historical_icu_stays",
            df=df_clean,
            target_column=self.target_column,
            time_column="intime",
            frequency="STAY",
            metadata={
                "total_source_records": len(docs),
                "date_shifted": True,
                "patient_level": True,
                "hospital_wide_time_series": False,
                "description": "MIMIC-IV patient-level ICU stays dataset. Dates are shifted independently per patient and must not be aggregated into cross-patient calendar time series.",
            },
        )
