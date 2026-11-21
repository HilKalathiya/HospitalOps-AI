"""
HospitalOps AI — Abstract Vector Store.

Defines persistence interface for indexing and querying knowledge chunks.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.models.knowledge import KnowledgeChunk


class VectorStore(ABC):
    """Abstract interface for knowledge vector persistence and semantic retrieval."""

    @property
    @abstractmethod
    def collection_name(self) -> str:
        """Name of the vector collection."""

    @property
    @abstractmethod
    def embedding_space_id(self) -> str | None:
        """Identifier of the embedding space bound to this collection, if known."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """True if the underlying vector store is operational and reachable."""

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
    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[tuple[KnowledgeChunk, float]]:
        """
        Execute nearest-neighbor vector search.

        Returns:
            List of (KnowledgeChunk, distance) tuples sorted in ascending distance order.
        """

    @abstractmethod
    def reset(self) -> None:
        """Purge and reset the vector collection (testing / administrative cleanup)."""
