"""
HospitalOps AI — Beds repository.

Collection: beds

Provides the data access layer for the beds collection.
Full CRUD methods are not yet implemented — that belongs in Chunk 1.2 (Domain APIs).
This file establishes the repository pattern and declares required indexes.
"""

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base import BaseRepository


class BedsRepository(BaseRepository):
    """
    Data access for the beds collection.

    Indexes declared (created by app/database/client.py at startup):
      beds_dept_status  : compound (department_id, status)
                          — find available beds in a department (most common query)
      beds_is_icu       : index on is_icu
                          — ICU capacity queries
      beds_patient_id   : sparse index on patient_id
                          — find which bed a patient is in (occupied beds only)

    CRUD methods will be added in Chunk 1.2 when the domain API endpoints are implemented.
    """

    COLLECTION = "beds"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        super().__init__(db)

    async def ensure_indexes(self) -> None:
        """
        Indexes for the beds collection.
        Created centrally by app/database/client.py — this method documents them.

        Compound index on (department_id, status):
          The single most common operational query: how many AVAILABLE beds
          are in department X? This compound index makes the query O(log n)
          rather than a full collection scan.

        Index on is_icu:
          ICU capacity is tracked separately because ICU availability is
          a critical operational signal. This index avoids scanning all beds
          when only ICU-capable beds are needed.

        Sparse index on patient_id:
          Find which bed a patient is currently occupying. Sparse because
          only OCCUPIED beds have a patient_id — this keeps the index small.
        """
