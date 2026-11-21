"""
HospitalOps AI — Knowledge & Document Ingestion Package.
"""

from app.knowledge.chunkers import StructureAwareChunker
from app.knowledge.cleaners import clean_text
from app.knowledge.embedders.base import EmbeddingProvider
from app.knowledge.embedders.factory import get_embedding_provider
from app.knowledge.extractors.factory import get_extractor
from app.knowledge.pipeline import KnowledgeIngestionPipeline, PipelineExecutionResult
from app.knowledge.privacy import scan_privacy_and_access
from app.knowledge.retrieval import (
    KnowledgeRetrievalRequest,
    KnowledgeRetrievalResponse,
    KnowledgeRetriever,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    RetrievalContextOrchestrator,
)
from app.knowledge.vectorstore.base import VectorStore
from app.knowledge.vectorstore.chroma import ChromaVectorStore

__all__ = [
    "clean_text",
    "scan_privacy_and_access",
    "get_extractor",
    "StructureAwareChunker",
    "EmbeddingProvider",
    "get_embedding_provider",
    "VectorStore",
    "ChromaVectorStore",
    "KnowledgeIngestionPipeline",
    "PipelineExecutionResult",
    "KnowledgeRetriever",
    "KnowledgeSearchRequest",
    "KnowledgeSearchResponse",
    "RetrievalContextOrchestrator",
    "KnowledgeRetrievalRequest",
    "KnowledgeRetrievalResponse",
]
