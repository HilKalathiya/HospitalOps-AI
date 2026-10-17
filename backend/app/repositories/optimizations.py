"""
HospitalOps AI — Optimizations Repository.

Collection: optimization_runs

Data access layer for persisted Resource Optimization run documents.
"""

import pymongo
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.optimization import OptimizationRunDocument
from app.repositories.base import BaseRepository


class OptimizationsRepository(BaseRepository):
    """Data access for the optimization_runs collection."""

    COLLECTION = "optimization_runs"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        super().__init__(db)

    async def ensure_indexes(self) -> None:
        """Indexes for optimization_runs: run_id unique and created_at descending."""
        pass

    async def create_optimization_run(
        self, doc: OptimizationRunDocument
    ) -> OptimizationRunDocument:
        """Persists a new optimization plan document."""
        data = doc.model_dump(by_alias=True, exclude_none=True)
        result = await self.collection.insert_one(data)
        doc.id = str(result.inserted_id)
        return doc

    async def find_by_id(self, run_id: str) -> OptimizationRunDocument | None:
        """Retrieves an optimization run by unique run_id."""
        doc = await self.collection.find_one({"run_id": run_id})
        if not doc:
            return None
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return OptimizationRunDocument(**doc)

    async def list_optimization_runs(
        self, skip: int = 0, limit: int = 50
    ) -> tuple[list[OptimizationRunDocument], int]:
        """Lists historical optimization runs ordered by created_at DESC."""
        total = await self.collection.count_documents({})
        cursor = (
            self.collection.find({})
            .sort("created_at", pymongo.DESCENDING)
            .skip(skip)
            .limit(limit)
        )

        runs: list[OptimizationRunDocument] = []
        async for doc in cursor:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            runs.append(OptimizationRunDocument(**doc))
        return runs, total
