"""
HospitalOps AI — Hero DMC Ingestion Pipeline.

Parses, cleans, and normalises the Hero DMC Hospital Admissions historical dataset.
"""

import csv
import logging
import uuid
from datetime import UTC, datetime

from app.data_ingestion.models import (
    DataIngestionRunDocument,
    DatasetName,
    HistoricalAdmissionDocument,
    IngestionStatus,
)
from app.data_ingestion.pipelines.base import BaseIngestionPipeline, calculate_file_hash
from app.data_ingestion.repositories import (
    DataIngestionRunRepository,
    HistoricalAdmissionsRepository,
)

logger = logging.getLogger(__name__)


def parse_date(date_str: str) -> datetime | None:
    """Safely parse dates (expecting YYYY-MM-DD)."""
    if not date_str or date_str.strip() in ("null", "na", "n/a", "none", "-"):
        return None
    try:
        # Assuming format from profile is YYYY-MM-DD
        dt = datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return dt.replace(tzinfo=UTC)
    except ValueError:
        return None


def parse_int(val_str: str) -> int | None:
    """Safely parse integers."""
    if not val_str or val_str.strip() in ("null", "na", "n/a", "none", "-"):
        return None
    try:
        return int(float(val_str.strip()))
    except ValueError:
        return None


class HeroDMCIngestionPipeline(BaseIngestionPipeline):
    """Pipeline for Hero DMC historical patient admissions."""

    def __init__(
        self,
        run_repo: DataIngestionRunRepository,
        admissions_repo: HistoricalAdmissionsRepository,
    ):
        super().__init__(run_repo)
        self.admissions_repo = admissions_repo

    @property
    def dataset_name(self) -> DatasetName:
        return DatasetName.HERO_DMC_ADMISSIONS

    async def process_file(
        self, filepath: str, batch_size: int = 1000, dry_run: bool = False
    ) -> DataIngestionRunDocument:
        """Process the Hero DMC dataset."""
        logger.info(f"Starting Hero DMC ingestion: {filepath} (dry_run={dry_run})")

        source_hash = calculate_file_hash(filepath)

        # Check idempotency: if not dry_run and we have a successful run with this hash, we skip.
        if not dry_run:
            existing_run = await self.run_repo.get_run_by_hash(source_hash)
            if existing_run:
                logger.info("Dataset already successfully ingested. Skipping.")
                # We can just return a new run marked as skipped/duplicate, or return the old one.
                # Here we create a new run explicitly stating 0 inserted.
                run = await self.initialize_run(filepath, source_hash)
                run.error_summary.append({"message": "Idempotency match. File skipped."})
                return await self.finalize_run(run, IngestionStatus.COMPLETED)

        # Initialize run tracking
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

        batch: list[HistoricalAdmissionDocument] = []

        try:
            with open(filepath, encoding="utf-8-sig", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    run.rows_read += 1

                    # Generate a stable identifier
                    mrd = row.get("MRD No.", "").strip()
                    doa = row.get("D.O.A", "").strip()
                    sno = row.get("SNO", "").strip()

                    if not mrd and not doa:
                        run.rows_invalid += 1
                        run.error_summary.append(
                            {
                                "row": run.rows_read,
                                "error": "Missing identifying fields (MRD No. or D.O.A)",
                            }
                        )
                        continue

                    # Composite fingerprint
                    source_record_id = f"HERO-{mrd}-{doa}-{sno}"

                    try:
                        doc = HistoricalAdmissionDocument(
                            ingestion_run_id=run.run_id,
                            source_record_id=source_record_id,
                            source_hash=source_hash,
                            admission_date=parse_date(doa),
                            discharge_date=parse_date(row.get("D.O.D", "")),
                            age=parse_int(row.get("AGE", "")),
                            gender=row.get("GENDER", "").strip() or None,
                            rural=row.get("RURAL", "").strip() or None,
                            admission_type=row.get("TYPE OF ADMISSION-EMERGENCY/OPD", "").strip()
                            or None,
                            outcome=row.get("OUTCOME", "").strip() or None,
                            duration_of_stay=parse_int(row.get("DURATION OF STAY", "")),
                            duration_of_icu_stay=parse_int(
                                row.get("duration of intensive unit stay", "")
                            ),
                        )
                        batch.append(doc)
                        run.rows_valid += 1
                    except Exception as e:
                        run.rows_invalid += 1
                        run.error_summary.append(
                            {"row": run.rows_read, "error": f"Validation failed: {str(e)}"}
                        )

                    # Write batch
                    if len(batch) >= batch_size:
                        if not dry_run:
                            stats = await self.admissions_repo.bulk_upsert(batch)
                            run.rows_inserted += stats["inserted"]
                            run.rows_updated += stats["updated"]
                            run.rows_skipped += stats["skipped"]
                        else:
                            # In dry run, we just assume they would be inserted
                            run.rows_inserted += len(batch)
                        batch.clear()

            # Final batch
            if batch:
                if not dry_run:
                    stats = await self.admissions_repo.bulk_upsert(batch)
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
