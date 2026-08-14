"""
HospitalOps AI — Audit Logs repository.

Collection: audit_logs

Audit log entries are APPEND-ONLY. This repository provides no update
or delete methods — that is intentional and must not be added.
"""

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.audit_log import AuditLogDocument
from app.repositories.base import BaseRepository


class AuditLogsRepository(BaseRepository):
    """
    Data access for the audit_logs collection.

    IMPORTANT: This repository is append-only by design.
    No update or delete methods will ever be added here.

    Indexes declared (created by app/database/client.py at startup):
      audit_logs_entity     : compound (entity_type, entity_id, timestamp desc)
                              — full audit trail for any entity
      audit_logs_actor      : compound (actor_type, actor_id)
                              — all actions by a specific actor
      audit_logs_request_id : index on request_id
                              — correlate audit entries with API requests
      audit_logs_timestamp  : descending index on timestamp
                              — chronological audit log view
    """

    COLLECTION = "audit_logs"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        super().__init__(db)

    async def ensure_indexes(self) -> None:
        """
        Indexes for the audit_logs collection.
        Created centrally by app/database/client.py — this method documents them.

        Compound index on (entity_type, entity_id, timestamp desc):
          The primary query pattern for audit: show all actions on admission
          'ADM-001', ordered newest first. This is essential for human-in-the-loop
          approval workflows and compliance reporting.

        Compound index on (actor_type, actor_id):
          All actions by a specific agent run or user account.
          Used for agent accountability and audit reviews.

        Index on request_id:
          Correlate all audit entries with a single API request — useful
          for debugging multi-step operations and regulatory investigations.

        Descending index on timestamp:
          Chronological audit log view — most recent entries first.
          Used for the system-wide audit log dashboard.
        """

    async def create_audit_log(self, document: "AuditLogDocument") -> str:
        """
        Append a new audit log entry.
        Returns the inserted document's ObjectId string.
        """
        result = await self.collection.insert_one(
            document.model_dump(by_alias=True, exclude_none=True)
        )
        return str(result.inserted_id)
