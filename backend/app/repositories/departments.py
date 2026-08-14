"""
HospitalOps AI — Departments repository.

Collection: departments

Provides the data access layer for the departments collection.
Full CRUD methods are not yet implemented — that belongs in Chunk 1.2 (Domain APIs).
This file establishes the repository pattern and declares required indexes.
"""

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base import BaseRepository


class DepartmentsRepository(BaseRepository):
    """
    Data access for the departments collection.

    Indexes declared (created by app/database/client.py at startup):
      departments_code_unique : unique index on code — department codes are business keys
      departments_name        : index on name — name-based lookups
      departments_is_active   : index on is_active — filter active departments in lists

    CRUD methods will be added in Chunk 1.2 when the domain API endpoints are implemented.
    """

    COLLECTION = "departments"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        super().__init__(db)

    async def ensure_indexes(self) -> None:
        """
        Indexes for the departments collection.
        Created centrally by app/database/client.py — this method documents them.

        Unique index on 'code':
          Department codes (e.g. 'ICU', 'ER') are unique business identifiers.
          Prevents duplicate department entries with the same code.

        Index on 'name':
          Supports name-based searches and lookups.

        Index on 'is_active':
          List endpoints filter to active departments by default.
        """
