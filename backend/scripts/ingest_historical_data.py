"""
HospitalOps AI — Historical Data Ingestion CLI.

Provides command-line execution for the ingestion pipelines.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings
from app.data_ingestion.pipelines.hero_dmc import HeroDMCIngestionPipeline
from app.data_ingestion.pipelines.mimic_iv import MIMICIVIngestionPipeline
from app.data_ingestion.pipelines.nhsn_hrd import NHSNHRDIngestionPipeline
from app.data_ingestion.repositories import (
    DataIngestionRunRepository,
    HistoricalAdmissionsRepository,
    HistoricalHospitalCapacityRepository,
    HistoricalICUStaysRepository,
)
from app.database.client import close_db, get_database, init_db, init_indexes

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


class StandaloneRunRepository:
    """In-memory run repository for dry-run when MongoDB is offline."""

    async def get_run_by_hash(self, source_hash: str) -> None:
        return None

    async def create_run(self, run: Any) -> Any:
        return run

    async def update_run(self, run: Any) -> Any:
        return run


class StandaloneDomainRepository:
    """In-memory domain repository for dry-run simulation."""

    async def bulk_upsert(self, docs: list[Any]) -> dict[str, int]:
        return {"inserted": len(docs), "updated": 0, "skipped": 0}


async def run_ingestion(
    dataset: str,
    filepath: str,
    batch_size: int,
    dry_run: bool,
    admissions_file: str | None = None,
    patients_file: str | None = None,
) -> None:
    """Run the appropriate ingestion pipeline."""
    settings = get_settings()
    db = None

    if not dry_run:
        await init_db(settings)
        await init_indexes()
        db = await get_database()
        run_repo = DataIngestionRunRepository(db)
    else:
        try:
            await init_db(settings)
            db = await get_database()
            run_repo = DataIngestionRunRepository(db)
        except Exception:
            logger.info("MongoDB offline: operating in standalone dry-run validation mode.")
            run_repo = StandaloneRunRepository()  # type: ignore[assignment]

    try:
        if dataset == "hero_dmc":
            adm_repo = HistoricalAdmissionsRepository(db) if db else StandaloneDomainRepository()  # type: ignore[assignment]
            pipeline = HeroDMCIngestionPipeline(run_repo, adm_repo)
            run_doc = await pipeline.process_file(filepath, batch_size=batch_size, dry_run=dry_run)
        elif dataset == "nhsn_hrd":
            cap_repo = HistoricalHospitalCapacityRepository(db) if db else StandaloneDomainRepository()  # type: ignore[assignment]
            pipeline = NHSNHRDIngestionPipeline(run_repo, cap_repo)
            run_doc = await pipeline.process_file(filepath, batch_size=batch_size, dry_run=dry_run)
        elif dataset == "mimic_iv":
            icu_repo = HistoricalICUStaysRepository(db) if db else StandaloneDomainRepository()  # type: ignore[assignment]
            pipeline = MIMICIVIngestionPipeline(run_repo, icu_repo)
            run_doc = await pipeline.process_file(
                filepath,
                batch_size=batch_size,
                dry_run=dry_run,
                admissions_file=admissions_file,
                patients_file=patients_file,
            )
        else:
            logger.error(f"Unknown dataset: {dataset}")
            return

        logger.info("\n=== Ingestion Report ===")
        logger.info(f"Run ID:         {run_doc.run_id}")
        logger.info(f"Dataset:        {run_doc.dataset_name}")
        logger.info(f"Status:         {run_doc.status}")
        logger.info(f"Rows Read:      {run_doc.rows_read}")
        logger.info(f"Rows Valid:     {run_doc.rows_valid}")
        logger.info(f"Rows Invalid:   {run_doc.rows_invalid}")

        if dry_run:
            logger.info(f"Rows Simulated: {run_doc.rows_inserted} (would have been sent to upsert)")
        else:
            logger.info(f"Rows Inserted:  {run_doc.rows_inserted}")
            logger.info(f"Rows Updated:   {run_doc.rows_updated}")
            logger.info(f"Rows Skipped:   {run_doc.rows_skipped}")

        if run_doc.error_summary:
            logger.warning(f"Error Summary ({len(run_doc.error_summary)} errors):")
            # print first 5 errors to avoid spamming
            for err in run_doc.error_summary[:5]:
                print(err)
            if len(run_doc.error_summary) > 5:
                logger.warning("... and more errors (truncated).")

    finally:
        if db is not None:
            await close_db()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest historical datasets.")
    parser.add_argument(
        "--dataset",
        choices=["hero_dmc", "nhsn_hrd", "mimic_iv"],
        required=True,
        help="Which dataset to ingest.",
    )
    parser.add_argument("--file", required=True, help="Path to the primary source CSV file.")
    parser.add_argument(
        "--batch-size", type=int, default=1000, help="Batch size for MongoDB upserts."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Process data without modifying the database."
    )
    parser.add_argument(
        "--admissions-file",
        default=None,
        help="Optional path to admissions.csv for MIMIC-IV enrichment.",
    )
    parser.add_argument(
        "--patients-file",
        default=None,
        help="Optional path to patients.csv for MIMIC-IV demographic enrichment.",
    )

    args = parser.parse_args()

    asyncio.run(
        run_ingestion(
            args.dataset,
            args.file,
            args.batch_size,
            args.dry_run,
            admissions_file=args.admissions_file,
            patients_file=args.patients_file,
        )
    )


if __name__ == "__main__":
    main()
