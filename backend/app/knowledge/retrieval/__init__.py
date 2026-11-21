"""
HospitalOps AI — Semantic Vector Search & Knowledge Retrieval Package (Chunk 4.2).
"""

from app.knowledge.retrieval.contracts import (
    EmbeddingSpaceInfo,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeSearchResult,
    RetrievalHealthResponse,
    SearchFilters,
)
from app.knowledge.retrieval.filters import SearchFilterBuilder
from app.knowledge.retrieval.query_encoder import QueryEncoder
from app.knowledge.retrieval.ranking import ResultRanker
from app.knowledge.retrieval.retriever import KnowledgeRetriever

__all__ = [
    "SearchFilters",
    "KnowledgeSearchRequest",
    "EmbeddingSpaceInfo",
    "KnowledgeSearchResult",
    "KnowledgeSearchResponse",
    "RetrievalHealthResponse",
    "QueryEncoder",
    "SearchFilterBuilder",
    "ResultRanker",
    "KnowledgeRetriever",
]
