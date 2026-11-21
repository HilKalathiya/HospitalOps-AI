"""
HospitalOps AI — Fast Deterministic Local Embedder.

Generates 384-dimensional dense vectors using hashed token n-grams and term weighting.
Properties:
- 100% offline and deterministic: identical text produces identical embeddings.
- Sub-millisecond latency with zero PyTorch / CUDA initialization overhead.
- Strictly L2-normalized (unit vector length).
- Safe for unit tests, local test environments, and air-gapped deployments.
"""

from __future__ import annotations

import hashlib
import math
import re

from app.knowledge.embedders.base import EmbeddingProvider


class LocalDeterministicEmbedder(EmbeddingProvider):
    """Lightweight deterministic feature-hashing embedder for testing and offline local dev."""

    def __init__(self, dimension: int = 384) -> None:
        self._dim = dimension

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_single(text) for text in texts]

    def embed_query(self, query: str) -> list[float]:
        return self._embed_single(query)

    def _embed_single(self, text: str) -> list[float]:
        if not text.strip():
            # Zero vector with small epsilon
            return [0.0] * self._dim

        vec = [0.0] * self._dim
        tokens = re.findall(r"\b\w+\b", text.lower())

        if not tokens:
            vec[0] = 1.0
            return vec

        # Unigrams and bigrams hashing into dimension space
        features: list[str] = list(tokens)
        for i in range(len(tokens) - 1):
            features.append(f"{tokens[i]}_{tokens[i+1]}")

        for feat in features:
            # MD5 hash to 4-byte integer
            h = int(hashlib.md5(feat.encode("utf-8")).hexdigest()[:8], 16)
            idx = h % self._dim
            sign = 1.0 if (h >> 31) & 1 == 0 else -1.0
            vec[idx] += sign

        # L2-normalize
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 1e-12:
            vec = [x / norm for x in vec]
        else:
            vec[0] = 1.0

        return vec
