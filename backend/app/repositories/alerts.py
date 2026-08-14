"""
HospitalOps AI — Alerts repository.

Collection: alerts
"""

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base import BaseRepository


class AlertsRepository(BaseRepository):
    """
    Data access for the alerts collection.

    Indexes declared (created by app/database/client.py at startup):
      alerts_severity_status  : compound (severity, status)
                                — open alerts by severity (primary dashboard query)
      alerts_triggered_at     : descending index on triggered_at
                                — chronological alert history
      alerts_department_id    : sparse index on department_id
                                — department-scoped alert views
    """

    COLLECTION = "alerts"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        super().__init__(db)

    async def ensure_indexes(self) -> None:
        """
        Indexes for the alerts collection.
        Created centrally by app/database/client.py — this method documents them.

        Compound index on (severity, status):
          Dashboard query: show all OPEN alerts ordered by severity.
          Compound because both fields are always queried together for triage.

        Descending index on triggered_at:
          Chronological alert history — most recent alerts first.

        Sparse index on department_id:
          Department-specific alert views. Sparse because hospital-wide
          alerts have no department_id.
        """
