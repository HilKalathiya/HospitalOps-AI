"""
HospitalOps AI — Semantic Query Encoder.

Validates and encodes natural-language queries into unit-normalized dense vectors
using the configured EmbeddingProvider. Enforces dimensional and numerical bounds.
"""

from __future__ import annotations

import logging
import math
import re

from app.knowledge.embedders.base import EmbeddingProvider

logger = logging.getLogger(__name__)

MAX_QUERY_LENGTH = 500
MIN_QUERY_LENGTH = 1


class QueryEncoder:
    """Validates natural-language input and generates dense query embeddings."""

    def __init__(
        self,
        provider: EmbeddingProvider | None = None,
        embedder: EmbeddingProvider | None = None,
    ) -> None:
        resolved = provider or embedder
        if resolved is None:
            raise ValueError("QueryEncoder requires an EmbeddingProvider instance.")
        self.provider = resolved

    @property
    def dimension(self) -> int:
        return self.provider.dimension

    @property
    def embedding_space_id(self) -> str:
        return self.provider.embedding_space_id

    def validate_query(self, raw_query: str) -> str:
        """
        Validate and sanitize search query input.

        Raises:
            ValueError: If query is empty, whitespace-only, exceeds length, or contains control characters.
        """
        if not raw_query or not raw_query.strip():
            raise ValueError("Search query cannot be empty or whitespace-only.")

        cleaned = raw_query.strip()

        if len(cleaned) < MIN_QUERY_LENGTH:
            raise ValueError(f"Search query must be at least {MIN_QUERY_LENGTH} character(s).")

        if len(cleaned) > MAX_QUERY_LENGTH:
            raise ValueError(
                f"Search query exceeds maximum length of {MAX_QUERY_LENGTH} characters (received {len(cleaned)})."
            )

        # Collapse excess whitespace
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned

    def encode(self, query: str) -> list[float]:
        """
        Generate a validated, normalized dense vector for the search query.

        Returns:
            L2-normalized float list of dimension self.provider.dimension.
        """
        cleaned_query = self.validate_query(query)
        embedding = self.provider.embed_query(cleaned_query)

        # Validate vector integrity
        if not isinstance(embedding, list) or len(embedding) != self.provider.dimension:
            raise ValueError(
                f"Embedding provider produced vector of dimension {len(embedding) if isinstance(embedding, list) else 'invalid'}, expected {self.provider.dimension}."
            )

        for i, val in enumerate(embedding):
            if not isinstance(val, int | float) or math.isnan(val) or math.isinf(val):
                raise ValueError(f"Embedding vector contains non-finite numerical value at index {i}: {val}")

        return embedding
