"""
HospitalOps AI — Predictions repository.

Collection: predictions

Provides the data access layer for the predictions collection.
Full read methods are not yet implemented — that belongs in Chunk 1.2.
The ML layer (future chunk) will use the write methods of this repository.
"""

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base import BaseRepository


class PredictionsRepository(BaseRepository):
    """
    Data access for the predictions collection.

    Indexes declared (created by app/database/client.py at startup):
      predictions_type_generated_at : compound (prediction_type, generated_at desc)
                                      — latest forecast of each type
      predictions_model_version     : index on model_version
                                      — query predictions from a specific model version
    """

    COLLECTION = "predictions"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        super().__init__(db)

    async def ensure_indexes(self) -> None:
        """
        Indexes for the predictions collection.
        Created centrally by app/database/client.py — this method documents them.

        Compound index on (prediction_type, generated_at desc):
          The primary read pattern for predictions: get the latest ICU_DEMAND
          prediction. DESC on generated_at returns the most recent first.

        Index on model_version:
          Allows querying predictions from a specific model version —
          useful for model comparison and rollback scenarios.
        """
