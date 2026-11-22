"""
HospitalOps AI — Agent Traces Repository (Milestone 5, Chunk 5.6.3).

Collection: agent_traces

Provides persistence, audit querying, and lifecycle tracking for
MultiAgentExecutionTrace documents.
"""

from __future__ import annotations

from typing import Any

import pymongo
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.agents.multi_agent.contracts import MultiAgentExecutionTrace
from app.repositories.base import BaseRepository


class AgentTraceRepository(BaseRepository):
    """
    Data access layer for the agent_traces collection.
    """

    COLLECTION = "agent_traces"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        super().__init__(db)

    async def ensure_indexes(self) -> None:
        """
        Documented indexes:
        - trace_id (unique)
        - parent_execution_id
        - compound (user_id, created_at DESC)
        """
        pass

    async def save_trace(self, trace: MultiAgentExecutionTrace) -> MultiAgentExecutionTrace:
        """
        Persist or update a MultiAgentExecutionTrace document.
        Uses trace_id as the primary lookup.
        """
        data = trace.model_dump(mode="json")
        await self.collection.replace_one(
            {"trace_id": trace.trace_id},
            data,
            upsert=True,
        )
        return trace

    async def get_by_trace_id(self, trace_id: str) -> MultiAgentExecutionTrace | None:
        """Retrieve a multi-agent execution trace by unique trace_id."""
        doc = await self.collection.find_one({"trace_id": trace_id})
        if not doc:
            return None
        doc.pop("_id", None)
        return MultiAgentExecutionTrace.model_validate(doc)

    async def get_by_parent_execution_id(
        self, parent_execution_id: str
    ) -> MultiAgentExecutionTrace | None:
        """Retrieve a multi-agent execution trace by parent_execution_id."""
        doc = await self.collection.find_one({"parent_execution_id": parent_execution_id})
        if not doc:
            return None
        doc.pop("_id", None)
        return MultiAgentExecutionTrace.model_validate(doc)

    async def list_user_traces(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[MultiAgentExecutionTrace], int]:
        """
        Retrieve paginated list of execution traces for a given user.
        Ordered by created_at DESC.
        """
        query: dict[str, Any] = {"user_id": user_id}
        total = await self.collection.count_documents(query)
        cursor = (
            self.collection.find(query)
            .sort("created_at", pymongo.DESCENDING)
            .skip(skip)
            .limit(limit)
        )
        traces: list[MultiAgentExecutionTrace] = []
        async for doc in cursor:
            doc.pop("_id", None)
            traces.append(MultiAgentExecutionTrace.model_validate(doc))
        return traces, total
