"""
HospitalOps AI — Base Data Ingestion Pipeline.

Provides shared utilities for hashing files, creating ingestion runs,
and abstract methods for specific pipelines.
"""

import hashlib
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime

from app.data_ingestion.models import (
    DataIngestionRunDocument,
    DatasetName,
    IngestionStatus,
)
from app.data_ingestion.repositories import DataIngestionRunRepository

logger = logging.getLogger(__name__)


def calculate_file_hash(filepath: str) -> str:
    """Calculate SHA-256 hash of a file for idempotency checks."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        # Read in blocks to handle large files
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


class BaseIngestionPipeline(ABC):
    """Abstract base class for all dataset ingestion pipelines."""

    def __init__(self, run_repo: DataIngestionRunRepository):
        self.run_repo = run_repo

    @property
    @abstractmethod
    def dataset_name(self) -> DatasetName:
        """The DatasetName this pipeline handles."""
        pass

    async def initialize_run(self, filepath: str, source_hash: str) -> DataIngestionRunDocument:
        """Create a new RUNNING ingestion document."""
        run = DataIngestionRunDocument(
            run_id=f"run-{uuid.uuid4().hex[:8]}",
            dataset_name=self.dataset_name,
            source_filename=filepath,
            source_hash=source_hash,
            started_at=datetime.now(tz=UTC),
            status=IngestionStatus.RUNNING,
        )
        return await self.run_repo.create_run(run)

    async def finalize_run(self, run: DataIngestionRunDocument, status: IngestionStatus) -> DataIngestionRunDocument:
        """Mark the run as COMPLETED or FAILED."""
        run.status = status
        run.completed_at = datetime.now(tz=UTC)
        return await self.run_repo.update_run(run)

    @abstractmethod
    async def process_file(
        self,
        filepath: str,
        batch_size: int = 1000,
        dry_run: bool = False
    ) -> DataIngestionRunDocument:
        """
        Process the dataset.
        If dry_run is True, calculate stats but do not persist domain records.
        """
        pass
