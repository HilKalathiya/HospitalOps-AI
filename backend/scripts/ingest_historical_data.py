"""
HospitalOps AI — Historical Data Ingestion CLI.

Provides command-line execution for the ingestion pipelines.
"""

import argparse
import asyncio
import logging

from app.core.config import get_settings
from app.data_ingestion.pipelines.hero_dmc import HeroDMCIngestionPipeline
from app.data_ingestion.pipelines.nhsn_hrd import NHSNHRDIngestionPipeline
from app.data_ingestion.repositories import (
    DataIngestionRunRepository,
    HistoricalAdmissionsRepository,
    HistoricalHospitalCapacityRepository,
)
from app.database.client import close_db, get_database, init_db, init_indexes

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


async def run_ingestion(dataset: str, filepath: str, batch_size: int, dry_run: bool) -> None:
    """Run the appropriate ingestion pipeline."""
    settings = get_settings()

    if not dry_run:
        await init_db(settings)
        await init_indexes()
        # Dependency injection
        db = await get_database()
    else:
        # For dry-run, we won't strictly need the DB connection if the pipeline skips it,
        # but the pipelines expect repositories. We can connect and ensure we don't save.
        await init_db(settings)
        db = await get_database()

    run_repo = DataIngestionRunRepository(db)

    try:
        if dataset == "hero_dmc":
            adm_repo = HistoricalAdmissionsRepository(db)
            pipeline = HeroDMCIngestionPipeline(run_repo, adm_repo)
        elif dataset == "nhsn_hrd":
            cap_repo = HistoricalHospitalCapacityRepository(db)
            pipeline = NHSNHRDIngestionPipeline(run_repo, cap_repo)
        else:
            logger.error(f"Unknown dataset: {dataset}")
            return

        run_doc = await pipeline.process_file(filepath, batch_size=batch_size, dry_run=dry_run)

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
        await close_db()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest historical datasets.")
    parser.add_argument(
        "--dataset",
        choices=["hero_dmc", "nhsn_hrd"],
        required=True,
        help="Which dataset to ingest.",
    )
    parser.add_argument("--file", required=True, help="Path to the source CSV file.")
    parser.add_argument(
        "--batch-size", type=int, default=1000, help="Batch size for MongoDB upserts."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Process data without modifying the database."
    )

    args = parser.parse_args()

    asyncio.run(run_ingestion(args.dataset, args.file, args.batch_size, args.dry_run))


if __name__ == "__main__":
    main()
