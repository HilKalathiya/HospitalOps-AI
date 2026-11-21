"""
HospitalOps AI — Abstract Vector Store.

Defines persistence interface for indexing and querying knowledge chunks.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.models.knowledge import KnowledgeChunk


class VectorStore(ABC):
    """Abstract interface for knowledge vector persistence."""

    @abstractmethod
    def add_chunks(self, chunks: list[KnowledgeChunk]) -> int:
        """
        Index a batch of KnowledgeChunk items with their embeddings and metadata.

        Returns:
            Number of successfully indexed chunks.
        """

    @abstractmethod
    def delete_by_document(self, document_id: str, version: int | None = None) -> int:
        """
        Remove chunks associated with a document_id (and optional specific version).

        Returns:
            Number of removed entries or 1 on success.
        """

    @abstractmethod
    def get_chunks_by_document(
        self, document_id: str, version: int | None = None, limit: int = 200
    ) -> list[KnowledgeChunk]:
        """Retrieve indexed chunks and metadata for inspection."""

    @abstractmethod
    def count(self, filter_criteria: dict[str, Any] | None = None) -> int:
        """Return total indexed chunks matching optional criteria."""

    @abstractmethod
    def reset(self) -> None:
        """Purge and reset the vector collection (testing / administrative cleanup)."""
