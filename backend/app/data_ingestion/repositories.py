"""
HospitalOps AI — Data Ingestion Repositories.

Contains repositories for ingestion runs, historical admissions,
and historical hospital capacity.
"""

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import UpdateOne

from app.data_ingestion.models import (
    DataIngestionRunDocument,
    HistoricalAdmissionDocument,
    HistoricalCapacityDocument,
)
from app.repositories.base import BaseRepository


class DataIngestionRunRepository(BaseRepository):
    """Repository for managing data ingestion runs."""

    COLLECTION = "data_ingestion_runs"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        super().__init__(db)

    async def ensure_indexes(self) -> None:
        """Indexes are managed centrally in database/client.py."""
        pass

    async def create_run(self, run: DataIngestionRunDocument) -> DataIngestionRunDocument:
        """Insert a new ingestion run document."""
        await self.collection.insert_one(run.model_dump(by_alias=True, exclude_none=True))
        return run

    async def update_run(self, run: DataIngestionRunDocument) -> DataIngestionRunDocument:
        """Update an existing ingestion run."""
        await self.collection.update_one(
            {"run_id": run.run_id},
            {"$set": run.model_dump(by_alias=True, exclude_none=True)}
        )
        return run

    async def get_run_by_hash(self, source_hash: str) -> DataIngestionRunDocument | None:
        """Check if a run with this exact file hash already exists and was COMPLETED."""
        doc = await self.collection.find_one({"source_hash": source_hash, "status": "COMPLETED"})
        if doc:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            return DataIngestionRunDocument(**doc)
        return None


class HistoricalAdmissionsRepository(BaseRepository):
    """Repository for managing Hero DMC historical admissions."""

    COLLECTION = "historical_admissions"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        super().__init__(db)

    async def ensure_indexes(self) -> None:
        """Indexes are managed centrally in database/client.py."""
        pass

    async def bulk_upsert(self, docs: list[HistoricalAdmissionDocument]) -> dict[str, int]:
        """
        Upsert a batch of admission documents based on source_record_id.
        Returns the number of inserted vs updated documents.
        """
        if not docs:
            return {"inserted": 0, "updated": 0, "skipped": 0}

        operations = []
        for doc in docs:
            doc_dict = doc.model_dump(by_alias=True, exclude_none=True)
            if "_id" in doc_dict:
                del doc_dict["_id"]

            operations.append(
                UpdateOne(
                    {"source_record_id": doc.source_record_id},
                    {"$set": doc_dict},
                    upsert=True
                )
            )

        result = await self.collection.bulk_write(operations, ordered=False)
        return {
            "inserted": result.upserted_count,
            "updated": result.modified_count,
            "skipped": len(docs) - (result.upserted_count + result.modified_count)
        }


class HistoricalHospitalCapacityRepository(BaseRepository):
    """Repository for managing NHSN historical capacity records."""

    COLLECTION = "historical_hospital_capacity"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        super().__init__(db)

    async def ensure_indexes(self) -> None:
        """Indexes are managed centrally in database/client.py."""
        pass

    async def bulk_upsert(self, docs: list[HistoricalCapacityDocument]) -> dict[str, int]:
        """
        Upsert a batch of capacity documents based on week_ending_date + geographic_aggregation.
        Returns the number of inserted vs updated documents.
        """
        if not docs:
            return {"inserted": 0, "updated": 0, "skipped": 0}

        operations = []
        for doc in docs:
            doc_dict = doc.model_dump(by_alias=True, exclude_none=True)
            if "_id" in doc_dict:
                del doc_dict["_id"]

            operations.append(
                UpdateOne(
                    {
                        "week_ending_date": doc.week_ending_date,
                        "geographic_aggregation": doc.geographic_aggregation,
                    },
                    {"$set": doc_dict},
                    upsert=True
                )
            )

        result = await self.collection.bulk_write(operations, ordered=False)
        return {
            "inserted": result.upserted_count,
            "updated": result.modified_count,
            "skipped": len(docs) - (result.upserted_count + result.modified_count)
        }
