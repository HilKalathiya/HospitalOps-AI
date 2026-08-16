"""
HospitalOps AI — NHSN HRD Ingestion Pipeline.

Parses, cleans, and normalises the NHSN Historical Hospital Capacity dataset.
"""

import csv
import logging
import uuid
from datetime import UTC, datetime

from app.data_ingestion.models import (
    DataIngestionRunDocument,
    DatasetName,
    HistoricalCapacityDocument,
    IngestionStatus,
)
from app.data_ingestion.pipelines.base import BaseIngestionPipeline, calculate_file_hash
from app.data_ingestion.repositories import (
    DataIngestionRunRepository,
    HistoricalHospitalCapacityRepository,
)

logger = logging.getLogger(__name__)


def parse_date(date_str: str) -> datetime | None:
    """Safely parse dates (expecting MM/DD/YYYY or YYYY-MM-DD)."""
    if not date_str or date_str.strip() in ("null", "na", "n/a", "none", "-"):
        return None
    val = date_str.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.strptime(val, fmt).replace(tzinfo=UTC)
        except ValueError:
            pass
    return None


def parse_int(val_str: str) -> int | None:
    """Safely parse integers."""
    if not val_str or val_str.strip() in ("null", "na", "n/a", "none", "-"):
        return None
    try:
        # replace commas if present
        return int(float(val_str.strip().replace(",", "")))
    except ValueError:
        return None


class NHSNHRDIngestionPipeline(BaseIngestionPipeline):
    """Pipeline for NHSN historical hospital capacity records."""

    def __init__(
        self,
        run_repo: DataIngestionRunRepository,
        capacity_repo: HistoricalHospitalCapacityRepository,
    ):
        super().__init__(run_repo)
        self.capacity_repo = capacity_repo

    @property
    def dataset_name(self) -> DatasetName:
        return DatasetName.NHSN_HISTORICAL_HOSPITAL_CAPACITY

    async def process_file(
        self, filepath: str, batch_size: int = 1000, dry_run: bool = False
    ) -> DataIngestionRunDocument:
        """Process the NHSN HRD dataset."""
        logger.info(f"Starting NHSN HRD ingestion: {filepath} (dry_run={dry_run})")

        source_hash = calculate_file_hash(filepath)

        if not dry_run:
            existing_run = await self.run_repo.get_run_by_hash(source_hash)
            if existing_run:
                logger.info("Dataset already successfully ingested. Skipping.")
                run = await self.initialize_run(filepath, source_hash)
                run.error_summary.append({"message": "Idempotency match. File skipped."})
                return await self.finalize_run(run, IngestionStatus.COMPLETED)

        if not dry_run:
            run = await self.initialize_run(filepath, source_hash)
        else:
            run = DataIngestionRunDocument(
                run_id=f"dryrun-{uuid.uuid4().hex[:8]}",
                dataset_name=self.dataset_name,
                source_filename=filepath,
                source_hash=source_hash,
                started_at=datetime.now(tz=UTC),
                status=IngestionStatus.RUNNING,
            )

        batch: list[HistoricalCapacityDocument] = []

        try:
            with open(filepath, encoding="utf-8-sig", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    run.rows_read += 1

                    week_ending_str = row.get("Week Ending Date", "").strip()
                    geo_agg = row.get("Geographic aggregation", "").strip()

                    if not week_ending_str or not geo_agg:
                        run.rows_invalid += 1
                        run.error_summary.append({
                            "row": run.rows_read,
                            "error": "Missing identifying fields (Week Ending Date or Geographic aggregation)"
                        })
                        continue

                    week_ending_date = parse_date(week_ending_str)
                    if not week_ending_date:
                        run.rows_invalid += 1
                        run.error_summary.append({
                            "row": run.rows_read,
                            "error": f"Invalid date format: {week_ending_str}"
                        })
                        continue

                    try:
                        doc = HistoricalCapacityDocument(
                            ingestion_run_id=run.run_id,
                            source_hash=source_hash,
                            week_ending_date=week_ending_date,
                            geographic_aggregation=geo_agg,
                            inpatient_beds=parse_int(row.get("Number of Inpatient Beds", "")),
                            inpatient_beds_occupied=parse_int(row.get("Number of Inpatient Beds Occupied", "")),
                            icu_beds=parse_int(row.get("Number of ICU Beds", "")),
                            icu_beds_occupied=parse_int(row.get("Number of ICU Beds Occupied", "")),
                            pediatric_inpatient_beds=parse_int(row.get("Number of Pediatric Inpatient beds", "")),
                            pediatric_inpatient_beds_occupied=parse_int(row.get("Number of Pediatric Inpatient Beds Occupied", "")),
                            adult_inpatient_beds=parse_int(row.get("Number of Adult Inpatient Beds", "")),
                            adult_inpatient_beds_occupied=parse_int(row.get("Number of Adult Inpatient Beds Occupied", "")),
                            adult_icu_beds=parse_int(row.get("Number of Adult ICU Beds", "")),
                            adult_icu_beds_occupied=parse_int(row.get("Number of Adult ICU Beds Occupied", "")),
                            pediatric_icu_beds=parse_int(row.get("Number of Pediatric ICU Beds", "")),
                            pediatric_icu_beds_occupied=parse_int(row.get("Number of Pediatric ICU Beds Occupied", "")),
                            total_covid_admissions=parse_int(row.get("Total Patients Hospitalized with COVID-19", "")),
                            total_influenza_admissions=parse_int(row.get("Total Patients Hospitalized with Influenza", "")),
                            total_rsv_admissions=parse_int(row.get("Total Patients Hospitalized with RSV", "")),
                        )
                        batch.append(doc)
                        run.rows_valid += 1
                    except Exception as e:
                        run.rows_invalid += 1
                        run.error_summary.append({
                            "row": run.rows_read,
                            "error": f"Validation failed: {str(e)}"
                        })

                    if len(batch) >= batch_size:
                        if not dry_run:
                            stats = await self.capacity_repo.bulk_upsert(batch)
                            run.rows_inserted += stats["inserted"]
                            run.rows_updated += stats["updated"]
                            run.rows_skipped += stats["skipped"]
                        else:
                            run.rows_inserted += len(batch)
                        batch.clear()

            if batch:
                if not dry_run:
                    stats = await self.capacity_repo.bulk_upsert(batch)
                    run.rows_inserted += stats["inserted"]
                    run.rows_updated += stats["updated"]
                    run.rows_skipped += stats["skipped"]
                else:
                    run.rows_inserted += len(batch)
                batch.clear()

            status = IngestionStatus.COMPLETED if run.rows_invalid == 0 else IngestionStatus.PARTIAL
            if run.rows_valid == 0 and run.rows_read > 0:
                status = IngestionStatus.FAILED

            if not dry_run:
                run = await self.finalize_run(run, status)
            else:
                run.status = status
                run.completed_at = datetime.now(tz=UTC)

        except Exception as e:
            logger.exception("Pipeline failed unexpectedly.")
            run.error_summary.append({"error": f"Pipeline exception: {str(e)}"})
            if not dry_run:
                run = await self.finalize_run(run, IngestionStatus.FAILED)
            else:
                run.status = IngestionStatus.FAILED
                run.completed_at = datetime.now(tz=UTC)

        return run
