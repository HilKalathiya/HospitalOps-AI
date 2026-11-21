"""
HospitalOps AI — SentenceTransformer Embedding Provider.

Wraps sentence-transformers models (e.g. all-MiniLM-L6-v2) for high-accuracy
semantic representations.
Loads lazily to avoid startup penalties.
"""

from __future__ import annotations

import logging
from typing import Any

from app.knowledge.embedders.base import EmbeddingProvider

logger = logging.getLogger(__name__)


class SentenceTransformerEmbedder(EmbeddingProvider):
    """Generates embeddings using sentence-transformers pretrained models."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self._model: Any = None
        self._dim: int = 384

    def _get_model(self) -> Any:
        if self._model is None:
            logger.info("Loading SentenceTransformer model: %s", self.model_name)
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            self._dim = int(self._model.get_sentence_embedding_dimension())
        return self._model

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._get_model()
        embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [emb.tolist() for emb in embeddings]

    def embed_query(self, query: str) -> list[float]:
        model = self._get_model()
        emb = model.encode(query, normalize_embeddings=True, show_progress_bar=False)
        return emb.tolist()
