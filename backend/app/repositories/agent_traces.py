"""
HospitalOps AI — Agent Traces Repository (Milestone 5, Chunk 5.6.3).

Collection: agent_traces

Provides persistence, audit querying, and lifecycle tracking for
MultiAgentExecutionTrace documents with MongoDB storage and in-memory fallback.
"""

from __future__ import annotations

import logging
from typing import Any

import pymongo
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.agents.multi_agent.contracts import MultiAgentExecutionTrace
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class AgentTraceRepository(BaseRepository):
    """
    Data access layer for the agent_traces collection.
    Supports MongoDB persistence and in-memory fallback for offline/testing isolation.
    """

    COLLECTION = "agent_traces"

    def __init__(self, db: AsyncIOMotorDatabase | None = None) -> None:  # type: ignore[type-arg]
        if db is not None:
            super().__init__(db)
        else:
            self._db = None  # type: ignore[assignment]
        self._in_memory: dict[str, MultiAgentExecutionTrace] = {}

    async def ensure_indexes(self) -> None:
        """
        Documented indexes:
        - trace_id (unique)
        - parent_execution_id
        - compound (user_id, created_at DESC)
        """
        if self._db is not None:
            try:
                await self.collection.create_index("trace_id", unique=True)
                await self.collection.create_index("parent_execution_id")
                await self.collection.create_index([("user_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)])
            except Exception as exc:
                logger.debug("Could not ensure indexes for agent_traces: %s", exc)

    async def save_trace(self, trace: MultiAgentExecutionTrace) -> MultiAgentExecutionTrace:
        """
        Persist or update a MultiAgentExecutionTrace document.
        Uses trace_id as the primary lookup.
        """
        self._in_memory[trace.trace_id] = trace
        if self._db is not None:
            data = trace.model_dump(mode="json")
            await self.collection.replace_one(
                {"trace_id": trace.trace_id},
                data,
                upsert=True,
            )
        return trace

    async def get_by_trace_id(
        self, trace_id: str, user_id: str | None = None
    ) -> MultiAgentExecutionTrace | None:
        """
        Retrieve a multi-agent execution trace by unique trace_id.
        If user_id is provided, enforces authenticated ownership scoping.
        """
        trace: MultiAgentExecutionTrace | None = None
        if self._db is not None:
            query: dict[str, Any] = {"trace_id": trace_id}
            if user_id:
                query["user_id"] = user_id
            doc = await self.collection.find_one(query)
            if doc:
                doc.pop("_id", None)
                trace = MultiAgentExecutionTrace.model_validate(doc)
        if trace is None:
            mem_trace = self._in_memory.get(trace_id)
            if mem_trace is not None:
                if user_id is None or mem_trace.user_id == user_id:
                    trace = mem_trace

        return trace

    async def get_by_trace_id_and_user(
        self, trace_id: str, user_id: str
    ) -> MultiAgentExecutionTrace | None:
        """Retrieve a multi-agent execution trace enforcing strict user ownership."""
        return await self.get_by_trace_id(trace_id, user_id=user_id)

    async def get_by_parent_execution_id(
        self, parent_execution_id: str, user_id: str | None = None
    ) -> MultiAgentExecutionTrace | None:
        """
        Retrieve a multi-agent execution trace by parent_execution_id.
        If user_id is provided, enforces authenticated ownership scoping.
        """
        trace: MultiAgentExecutionTrace | None = None
        if self._db is not None:
            query: dict[str, Any] = {"parent_execution_id": parent_execution_id}
            if user_id:
                query["user_id"] = user_id
            doc = await self.collection.find_one(query)
            if doc:
                doc.pop("_id", None)
                trace = MultiAgentExecutionTrace.model_validate(doc)
        if trace is None:
            for mem_trace in self._in_memory.values():
                if mem_trace.parent_execution_id == parent_execution_id:
                    if user_id is None or mem_trace.user_id == user_id:
                        trace = mem_trace
                        break

        return trace

    async def get_by_parent_execution_id_and_user(
        self, parent_execution_id: str, user_id: str
    ) -> MultiAgentExecutionTrace | None:
        """Retrieve a trace by parent_execution_id enforcing strict user ownership."""
        return await self.get_by_parent_execution_id(parent_execution_id, user_id=user_id)

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
        if self._db is not None:
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

        user_traces = [t for t in self._in_memory.values() if t.user_id == user_id]
        user_traces.sort(key=lambda t: t.created_at, reverse=True)
        total = len(user_traces)
        return user_traces[skip : skip + limit], total
