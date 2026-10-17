"""
HospitalOps AI — Simulations repository.

Collection: simulation_runs

Data access layer for persisted what-if simulation run results.
"""

import pymongo
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.simulation import SimulationRunDocument
from app.repositories.base import BaseRepository


class SimulationsRepository(BaseRepository):
    """
    Data access for the simulation_runs collection.
    """

    COLLECTION = "simulation_runs"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        super().__init__(db)

    async def ensure_indexes(self) -> None:
        """
        Documented indexes:
        - simulation_id (unique)
        - compound (scenario_type, created_at desc)
        """
        pass

    async def create_simulation_run(self, doc: SimulationRunDocument) -> SimulationRunDocument:
        """Persists a new simulation run document."""
        data = doc.model_dump(by_alias=True, exclude_none=True)
        result = await self.collection.insert_one(data)
        doc.id = str(result.inserted_id)
        return doc

    async def find_by_id(self, simulation_id: str) -> SimulationRunDocument | None:
        """Retrieves a simulation run by its unique simulation_id."""
        doc = await self.collection.find_one({"simulation_id": simulation_id})
        if not doc:
            return None
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return SimulationRunDocument(**doc)

    async def list_simulation_runs(
        self,
        skip: int = 0,
        limit: int = 50,
        scenario_type: str | None = None,
    ) -> tuple[list[SimulationRunDocument], int]:
        """Lists historical simulation runs, ordered by created_at DESC."""
        query: dict = {}
        if scenario_type:
            query["scenario_type"] = scenario_type

        total = await self.collection.count_documents(query)
        cursor = (
            self.collection.find(query)
            .sort("created_at", pymongo.DESCENDING)
            .skip(skip)
            .limit(limit)
        )

        runs: list[SimulationRunDocument] = []
        async for doc in cursor:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            runs.append(SimulationRunDocument(**doc))
        return runs, total
