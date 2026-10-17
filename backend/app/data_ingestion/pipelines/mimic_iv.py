"""
HospitalOps AI — MIMIC-IV v3.1 Ingestion Pipeline.

Parses, cleans, validates, and normalizes the MIMIC-IV clinical ICU dataset
(icustays, with optional admissions and patients auxiliary demographic joins).

CRITICAL ARCHITECTURAL CONSTRAINTS:
1. DATE SHIFTING: MIMIC-IV patient dates are shifted independently per patient.
   Dates MUST NOT be aggregated across patients to fabricate a calendar-wide
   hospital daily admissions or occupancy time series.
2. PATIENT-LEVEL ROLE: Used exclusively for patient-level and ICU-stay-level
   clinical prediction (such as ICU length of stay 'los' or in-hospital mortality).
3. PRIVACY: Data must remain strictly local; do not transmit to external services.
4. CHUNKED STREAMING: Large files are processed in streaming batches to avoid high memory.
"""

import logging
from datetime import UTC, datetime
from typing import Any

import pandas as pd

from app.data_ingestion.models import (
    DataIngestionRunDocument,
    DatasetName,
    HistoricalICUStayDocument,
    IngestionStatus,
)
from app.data_ingestion.pipelines.base import BaseIngestionPipeline, calculate_file_hash
from app.data_ingestion.repositories import (
    DataIngestionRunRepository,
    HistoricalICUStaysRepository,
)

logger = logging.getLogger(__name__)


def parse_datetime(val: Any) -> datetime | None:
    """Safely parse datetime strings into UTC-aware datetime."""
    if val is None or pd.isna(val):
        return None
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ("null", "na", "n/a", "none", "-"):
        return None
    try:
        dt = pd.to_datetime(val_str)
        if dt.tzinfo is None:
            return dt.tz_localize(UTC).to_pydatetime()
        return dt.tz_convert(UTC).to_pydatetime()
    except Exception:
        return None


def parse_float(val: Any) -> float | None:
    """Safely parse floats (e.g. for length of stay 'los')."""
    if val is None or pd.isna(val):
        return None
    try:
        parsed = float(val)
        return parsed if not pd.isna(parsed) else None
    except (ValueError, TypeError):
        return None


def parse_int(val: Any) -> int | None:
    """Safely parse integers (e.g. identifiers)."""
    if val is None or pd.isna(val):
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


class MIMICIVIngestionPipeline(BaseIngestionPipeline):
    """
    Ingestion pipeline for MIMIC-IV v3.1 ICU stay and clinical patient records.
    Processes icustays.csv with chunked streaming and optional auxiliary demographic joins.
    """

    def __init__(
        self,
        run_repo: DataIngestionRunRepository,
        icu_repo: HistoricalICUStaysRepository,
    ):
        super().__init__(run_repo)
        self.icu_repo = icu_repo

    @property
    def dataset_name(self) -> DatasetName:
        return DatasetName.MIMIC_IV_CLINICAL

    async def process_file(
        self,
        filepath: str,
        batch_size: int = 1000,
        dry_run: bool = False,
        admissions_file: str | None = None,
        patients_file: str | None = None,
    ) -> DataIngestionRunDocument:
        """
        Stream, clean, validate, and persist MIMIC-IV ICU stays.
        """
        source_hash = calculate_file_hash(filepath)

        # Idempotency check: abort early if identical file hash was already ingested
        existing_run = await self.run_repo.get_run_by_hash(source_hash)
        if existing_run:
            logger.info(
                "Idempotency match: MIMIC-IV file hash %s already processed in run %s. Skipping.",
                source_hash,
                existing_run.run_id,
            )
            return existing_run

        run_doc = await self.initialize_run(filepath, source_hash)

        # Optional demographic and admission lookups for enrichment
        admissions_lookup: dict[int, dict[str, Any]] = {}
        if admissions_file:
            try:
                logger.info("Loading admissions auxiliary lookup from %s", admissions_file)
                # Read only necessary columns in chunks
                use_cols = [
                    "hadm_id",
                    "admission_type",
                    "admission_location",
                    "discharge_location",
                    "hospital_expire_flag",
                ]
                for chunk in pd.read_csv(admissions_file, usecols=use_cols, chunksize=10000):
                    for _, row in chunk.iterrows():
                        hadm_id = parse_int(row.get("hadm_id"))
                        if hadm_id is not None:
                            admissions_lookup[hadm_id] = {
                                "admission_type": (
                                    str(row["admission_type"])
                                    if pd.notna(row.get("admission_type"))
                                    else None
                                ),
                                "admission_location": (
                                    str(row["admission_location"])
                                    if pd.notna(row.get("admission_location"))
                                    else None
                                ),
                                "discharge_location": (
                                    str(row["discharge_location"])
                                    if pd.notna(row.get("discharge_location"))
                                    else None
                                ),
                                "hospital_expire_flag": parse_int(row.get("hospital_expire_flag")),
                            }
            except Exception as e:
                logger.warning("Could not load admissions lookup: %s", e)

        patients_lookup: dict[int, dict[str, Any]] = {}
        if patients_file:
            try:
                logger.info("Loading patients auxiliary lookup from %s", patients_file)
                use_cols = ["subject_id", "gender", "anchor_age"]
                for chunk in pd.read_csv(patients_file, usecols=use_cols, chunksize=10000):
                    for _, row in chunk.iterrows():
                        sub_id = parse_int(row.get("subject_id"))
                        if sub_id is not None:
                            patients_lookup[sub_id] = {
                                "gender": (
                                    str(row["gender"])
                                    if pd.notna(row.get("gender"))
                                    else None
                                ),
                                "anchor_age": parse_int(row.get("anchor_age")),
                            }
            except Exception as e:
                logger.warning("Could not load patients lookup: %s", e)

        try:
            # Stream icustays in chunks to preserve memory efficiency
            for chunk in pd.read_csv(filepath, chunksize=batch_size):
                batch_docs: list[HistoricalICUStayDocument] = []

                for _, row in chunk.iterrows():
                    run_doc.rows_read += 1
                    stay_id = parse_int(row.get("stay_id"))
                    subject_id = parse_int(row.get("subject_id"))
                    hadm_id = parse_int(row.get("hadm_id"))
                    los = parse_float(row.get("los"))

                    # Validation: stay_id and subject_id must be valid positive integers
                    if stay_id is None or stay_id <= 0 or subject_id is None or subject_id <= 0:
                        run_doc.rows_invalid += 1
                        if len(run_doc.error_summary) < 50:
                            run_doc.error_summary.append(
                                {
                                    "row_index": run_doc.rows_read,
                                    "reason": "Missing or invalid stay_id or subject_id",
                                }
                            )
                        continue

                    # Validation: los if present must be non-negative
                    if los is not None and los < 0:
                        run_doc.rows_invalid += 1
                        if len(run_doc.error_summary) < 50:
                            run_doc.error_summary.append(
                                {
                                    "row_index": run_doc.rows_read,
                                    "reason": f"Negative length of stay: {los}",
                                }
                            )
                        continue

                    intime = parse_datetime(row.get("intime"))
                    outtime = parse_datetime(row.get("outtime"))

                    # Retrieve auxiliary lookups if available
                    adm_meta = admissions_lookup.get(hadm_id, {}) if hadm_id else {}
                    pat_meta = patients_lookup.get(subject_id, {})

                    doc = HistoricalICUStayDocument(
                        ingestion_run_id=run_doc.run_id,
                        source_hash=source_hash,
                        subject_id=subject_id,
                        hadm_id=hadm_id,
                        stay_id=stay_id,
                        first_careunit=(
                            str(row["first_careunit"])
                            if pd.notna(row.get("first_careunit"))
                            else None
                        ),
                        last_careunit=(
                            str(row["last_careunit"])
                            if pd.notna(row.get("last_careunit"))
                            else None
                        ),
                        intime=intime,
                        outtime=outtime,
                        los=los,
                        admission_type=adm_meta.get("admission_type"),
                        admission_location=adm_meta.get("admission_location"),
                        discharge_location=adm_meta.get("discharge_location"),
                        hospital_expire_flag=adm_meta.get("hospital_expire_flag"),
                        gender=pat_meta.get("gender"),
                        anchor_age=pat_meta.get("anchor_age"),
                    )

                    batch_docs.append(doc)
                    run_doc.rows_valid += 1

                # Persist batch if not dry run
                if batch_docs and not dry_run:
                    result = await self.icu_repo.bulk_upsert(batch_docs)
                    run_doc.rows_inserted += result["inserted"]
                    run_doc.rows_updated += result["updated"]
                    run_doc.rows_skipped += result["skipped"]
                elif dry_run:
                    run_doc.rows_inserted += len(batch_docs)

            # Finalize run
            status = IngestionStatus.COMPLETED
            if run_doc.rows_valid == 0 and run_doc.rows_read > 0:
                status = IngestionStatus.FAILED
            elif run_doc.rows_invalid > 0:
                status = IngestionStatus.PARTIAL

            return await self.finalize_run(run_doc, status)

        except Exception as e:
            logger.exception("Failed processing MIMIC-IV file %s: %s", filepath, e)
            run_doc.error_summary.append({"fatal_error": str(e)})
            return await self.finalize_run(run_doc, IngestionStatus.FAILED)
