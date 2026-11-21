"""
HospitalOps AI — Embedding Provider Factory.

Instantiates configured embedding provider based on application settings.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from app.core.config import get_settings
from app.knowledge.embedders.base import EmbeddingProvider
from app.knowledge.embedders.local import LocalDeterministicEmbedder
from app.knowledge.embedders.transformer import SentenceTransformerEmbedder

logger = logging.getLogger(__name__)


@lru_cache
def get_embedding_provider(provider_type: str | None = None) -> EmbeddingProvider:
    """
    Return cached embedding provider singleton.

    Defaults to settings.embedding_provider ('local_deterministic' or 'sentence_transformers').
    """
    settings = get_settings()
    ptype = provider_type or settings.embedding_provider

    if ptype == "sentence_transformers":
        try:
            return SentenceTransformerEmbedder(model_name=settings.embedding_model_name)
        except Exception as err:
            logger.warning("Could not initialize SentenceTransformerEmbedder (%s), falling back to LocalDeterministicEmbedder", err)
            return LocalDeterministicEmbedder(dimension=384)

    return LocalDeterministicEmbedder(dimension=384)
