"""
HospitalOps AI — Abstract Embedding Provider.

Defines the contract for dense vector embedding generators.
All implementations must return L2-normalized float vectors.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Abstract interface for generating vector embeddings."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector embedding dimensionality (e.g. 384)."""

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Generate dense vector embeddings for a list of text strings.

        Returns:
            List of L2-normalized float lists of length self.dimension.
        """

    @abstractmethod
    def embed_query(self, query: str) -> list[float]:
        """
        Generate a single dense vector embedding for a query string.

        Returns:
            L2-normalized float list of length self.dimension.
        """
