"""
HospitalOps AI — Semantic Vector Search & RAG Context Retrieval Package (Chunks 4.2 & 4.3).
"""

from app.knowledge.retrieval.citation_builder import CitationBuilder
from app.knowledge.retrieval.context_builder import ContextBuilder
from app.knowledge.retrieval.contracts import (
    ContextBlock,
    ContextOrdering,
    EmbeddingSpaceInfo,
    KnowledgeRetrievalRequest,
    KnowledgeRetrievalResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeSearchResult,
    RetrievalHealthResponse,
    RetrievalMetadata,
    RetrievalStatus,
    SearchFilters,
    SkippedChunkInfo,
    SourceCitation,
)
from app.knowledge.retrieval.filters import SearchFilterBuilder
from app.knowledge.retrieval.orchestrator import RetrievalContextOrchestrator
from app.knowledge.retrieval.query_encoder import QueryEncoder
from app.knowledge.retrieval.ranking import ResultRanker
from app.knowledge.retrieval.retriever import KnowledgeRetriever
from app.knowledge.retrieval.token_budget import (
    TokenBudgetManager,
    count_tokens,
    get_token_count,
)

__all__ = [
    "SearchFilters",
    "KnowledgeSearchRequest",
    "EmbeddingSpaceInfo",
    "KnowledgeSearchResult",
    "KnowledgeSearchResponse",
    "RetrievalHealthResponse",
    "ContextOrdering",
    "RetrievalStatus",
    "KnowledgeRetrievalRequest",
    "SourceCitation",
    "ContextBlock",
    "SkippedChunkInfo",
    "RetrievalMetadata",
    "KnowledgeRetrievalResponse",
    "QueryEncoder",
    "SearchFilterBuilder",
    "ResultRanker",
    "KnowledgeRetriever",
    "CitationBuilder",
    "ContextBuilder",
    "TokenBudgetManager",
    "count_tokens",
    "get_token_count",
    "RetrievalContextOrchestrator",
]
