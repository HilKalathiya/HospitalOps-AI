"""
HospitalOps AI — Abstract Embedding Provider.

Defines the contract for dense vector embedding generators.
All implementations must return L2-normalized float vectors and provide
explicit embedding space metadata to prevent incompatible cross-model querying.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod


class EmbeddingSpaceMismatchError(ValueError):
    """Raised when query embedding space does not match indexed vector space."""


class EmbeddingProvider(ABC):
    """Abstract interface for generating vector embeddings."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the embedding provider (e.g. 'local_deterministic', 'sentence_transformers')."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the specific embedding model (e.g. 'all-MiniLM-L6-v2')."""

    @property
    @abstractmethod
    def model_version(self) -> str:
        """Version string of the embedding model."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector embedding dimensionality (e.g. 384)."""

    @property
    def metric(self) -> str:
        """Default distance metric for this embedding space."""
        return "cosine"

    @property
    def is_normalized(self) -> bool:
        """Whether vectors produced by this provider are strictly L2 unit-normalized."""
        return True

    @property
    def embedding_space_id(self) -> str:
        """
        Unique deterministic identifier for this embedding space.
        Used to verify compatibility between query and indexed collection.
        """
        return f"{self.provider_name}:{self.model_name}:d{self.dimension}:{self.metric}"

    def validate_vector(self, vec: list[float]) -> bool:
        """Validate that a vector has correct dimension and contains finite numbers."""
        if not isinstance(vec, list) or len(vec) != self.dimension:
            return False
        for x in vec:
            if not isinstance(x, int | float) or math.isnan(x) or math.isinf(x):
                return False
        return True

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
