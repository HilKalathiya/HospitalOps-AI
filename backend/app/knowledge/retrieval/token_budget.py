"""
HospitalOps AI — Token Budget Manager & Token Counter (Chunk 4.3).

Provides:
- Precise token counting via tiktoken (cl100k_base) with robust offline fallback
- Token-budget-aware selection of candidate chunks
- Tracking of citation and boundary formatting overhead
- Explicit recording of skipped chunks and exclusion reasons
"""

from __future__ import annotations

import logging
from typing import Any

from app.knowledge.retrieval.contracts import SkippedChunkInfo

logger = logging.getLogger(__name__)

# Initialize tiktoken cl100k_base tokenizer if available
_TIKTOKEN_ENCODER = None
_TOKEN_METHOD = "tiktoken_cl100k_base"

try:
    import tiktoken

    _TIKTOKEN_ENCODER = tiktoken.get_encoding("cl100k_base")
except Exception as e:
    logger.warning(
        "tiktoken cl100k_base unavailable, falling back to word-based approximation: %s", e
    )
    _TOKEN_METHOD = "approximate_words_1.33"


def count_tokens(text: str) -> tuple[int, str]:
    """
    Count the tokens in a string.

    Returns:
        (token_count, method_name)
    """
    if not text:
        return 0, _TOKEN_METHOD

    if _TIKTOKEN_ENCODER is not None:
        try:
            return len(_TIKTOKEN_ENCODER.encode(text)), "tiktoken_cl100k_base"
        except Exception:
            pass

    # Conservative word-based fallback: ~1.33 tokens per word, minimum 1 token per 4 chars
    words = len(text.split())
    approx = max(1, int(words * 1.33), int(len(text) / 4))
    return approx, "approximate_words_1.33"


def get_token_count(text: str) -> int:
    """Convenience token counter returning integer count."""
    tokens, _ = count_tokens(text)
    return tokens


class TokenBudgetManager:
    """Manages context token capacity, overhead allocation, and exclusion auditing."""

    def __init__(self, max_context_tokens: int = 3000) -> None:
        if max_context_tokens < 100:
            raise ValueError(
                f"max_context_tokens must be at least 100 (received {max_context_tokens})"
            )

        self.max_context_tokens = max_context_tokens
        self.assembled_content_tokens = 0
        self.overhead_tokens = 0
        self.skipped_chunks: list[SkippedChunkInfo] = []
        self._token_method = _TOKEN_METHOD

    @property
    def total_tokens(self) -> int:
        """Total assembled tokens including content and formatting overhead."""
        return self.assembled_content_tokens + self.overhead_tokens

    @property
    def remaining_tokens(self) -> int:
        """Remaining token allowance before hitting max_context_tokens."""
        return max(0, self.max_context_tokens - self.total_tokens)

    @property
    def token_count_method(self) -> str:
        """Name of the active token counting engine."""
        return self._token_method

    def can_fit(self, content_tokens: int, citation_overhead: int = 0) -> bool:
        """Check if adding content and overhead will remain within the token budget."""
        needed = content_tokens + citation_overhead
        return (self.total_tokens + needed) <= self.max_context_tokens

    def allocate(self, content_tokens: int, citation_overhead: int = 0) -> None:
        """
        Commit tokens to the budget.

        Raises:
            ValueError: If the allocation exceeds remaining tokens.
        """
        if not self.can_fit(content_tokens, citation_overhead):
            raise ValueError(
                f"Cannot allocate {content_tokens + citation_overhead} tokens; only {self.remaining_tokens} remaining."
            )
        self.assembled_content_tokens += content_tokens
        self.overhead_tokens += citation_overhead

    def record_skipped(
        self,
        chunk: Any,
        rank: int,
        content_tokens: int,
        reason: str,
    ) -> None:
        """Record details of a candidate chunk that was excluded from final context."""
        chunk_id = getattr(chunk, "chunk_id", str(chunk))
        doc_id = getattr(chunk, "document_id", "")
        doc_title = getattr(chunk, "document_title", "")
        sim_score = getattr(chunk, "similarity_score", 0.0)

        info = SkippedChunkInfo(
            chunk_id=chunk_id,
            document_id=doc_id,
            document_title=doc_title,
            rank=rank,
            token_count=content_tokens,
            similarity_score=sim_score,
            skip_reason=reason,
        )
        self.skipped_chunks.append(info)
