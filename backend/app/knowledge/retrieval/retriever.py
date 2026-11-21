"""
HospitalOps AI — Semantic Knowledge Retriever.

Coordinates:
- Query input validation and encoding
- Embedding space compatibility verification
- RBAC metadata filter derivation
- Vector nearest-neighbor search
- Post-retrieval operational status & active-version verification against MongoDB
- Provenance ranking and telemetry recording
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from app.knowledge.embedders.base import EmbeddingProvider, EmbeddingSpaceMismatchError
from app.knowledge.embedders.factory import get_embedding_provider
from app.knowledge.retrieval.contracts import (
    EmbeddingSpaceInfo,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    RetrievalHealthResponse,
    SearchFilters,
)
from app.knowledge.retrieval.filters import SearchFilterBuilder
from app.knowledge.retrieval.query_encoder import QueryEncoder
from app.knowledge.retrieval.ranking import ResultRanker
from app.knowledge.vectorstore.base import VectorStore
from app.knowledge.vectorstore.chroma import ChromaVectorStore
from app.models.knowledge import IngestionStatus
from app.models.user import UserDocument
from app.repositories.knowledge import KnowledgeRepository

logger = logging.getLogger(__name__)


class KnowledgeRetriever:
    """Orchestrates secure semantic vector search over approved hospital knowledge."""

    def __init__(
        self,
        vector_store: VectorStore | None = None,
        embedding_provider: EmbeddingProvider | None = None,
        knowledge_repo: KnowledgeRepository | None = None,
    ) -> None:
        self.embedding_provider = embedding_provider or get_embedding_provider()
        self.vector_store = vector_store or ChromaVectorStore(
            embedding_space_id=self.embedding_provider.embedding_space_id
        )
        self.knowledge_repo = knowledge_repo
        self.query_encoder = QueryEncoder(self.embedding_provider)

    async def search(
        self,
        request: KnowledgeSearchRequest,
        current_user: UserDocument | None = None,
    ) -> KnowledgeSearchResponse:
        """
        Execute semantic vector search with strict RBAC access boundaries and source provenance.
        """
        start_time = time.perf_counter()
        query_id = f"qry_{uuid.uuid4().hex[:12]}"

        # 1. Embedding space compatibility check
        col_space = self.vector_store.embedding_space_id
        prov_space = self.embedding_provider.embedding_space_id

        if col_space and col_space != prov_space:
            logger.error(
                "Embedding space mismatch: collection is '%s' but query provider is '%s'",
                col_space,
                prov_space,
            )
            raise EmbeddingSpaceMismatchError(
                f"Embedding space mismatch: indexed collection uses '{col_space}', but query provider generates '{prov_space}'. "
                "Cross-model vector distances are not mathematically compatible."
            )

        # 2. Query validation and embedding generation
        query_vec = self.query_encoder.encode(request.query)

        # 3. Server-side RBAC and metadata filter construction
        filters = request.filters or SearchFilters()
        where_clause, applied_filters, is_authorized = SearchFilterBuilder.build_where_clause(
            filters=filters,
            user=current_user,
        )

        space_info = EmbeddingSpaceInfo(
            provider=self.embedding_provider.provider_name,
            model=self.embedding_provider.model_name,
            version=self.embedding_provider.model_version,
            dimension=self.embedding_provider.dimension,
            metric=self.embedding_provider.metric,
            space_id=self.embedding_provider.embedding_space_id,
        )

        # If user requested filters outside their permitted access scope, return empty result
        if not is_authorized:
            duration = (time.perf_counter() - start_time) * 1000
            return KnowledgeSearchResponse(
                query_id=query_id,
                query=request.query,
                result_count=0,
                embedding_space=space_info,
                search_duration_ms=round(duration, 2),
                filters_applied=applied_filters,
                results=[],
            )

        # 4. Execute Chroma vector search (fetch 2x top_k to allow post-filtering)
        candidate_count = min(request.top_k * 2, 50)
        raw_hits = self.vector_store.search(
            query_embedding=query_vec,
            top_k=candidate_count,
            filters=where_clause,
        )

        # 5. Post-retrieval verification against MongoDB repository
        # Guarantees that quarantined, inactive, or superseded versions never appear
        verified_hits: list[tuple[Any, float]] = []
        if self.knowledge_repo is not None:
            doc_cache: dict[str, Any] = {}
            for chunk, dist in raw_hits:
                doc_id = chunk.metadata.document_id
                if doc_id not in doc_cache:
                    doc = await self.knowledge_repo.find_document_by_id(doc_id)
                    doc_cache[doc_id] = doc
                else:
                    doc = doc_cache[doc_id]

                # Drop if document does not exist in repo, is quarantined, or is failed
                if not doc:
                    continue
                if doc.is_quarantined or doc.status == IngestionStatus.QUARANTINED:
                    continue
                if doc.status == IngestionStatus.FAILED:
                    continue

                # If user did not specify an exact version filter, only surface the ACTIVE version
                if filters.version is None and chunk.metadata.version != doc.active_version:
                    continue

                verified_hits.append((chunk, dist))
        else:
            verified_hits = raw_hits

        # 6. Rank, deduplicate, score, and format excerpts
        final_results = ResultRanker.rank_and_format(
            raw_hits=verified_hits,
            filters=filters,
            top_k=request.top_k,
        )

        duration = (time.perf_counter() - start_time) * 1000

        # Safe logging (do NOT log raw query content to protect clinical inquiry privacy)
        logger.info(
            "Semantic retrieval completed | qid=%s results=%d duration=%.2fms",
            query_id,
            len(final_results),
            duration,
        )

        return KnowledgeSearchResponse(
            query_id=query_id,
            query=request.query,
            result_count=len(final_results),
            embedding_space=space_info,
            search_duration_ms=round(duration, 2),
            filters_applied=applied_filters,
            results=final_results,
        )

    async def check_health(self) -> RetrievalHealthResponse:
        """Inspect and return retrieval readiness diagnostics."""
        connected = self.vector_store.is_connected
        chunk_count = self.vector_store.count() if connected else 0

        space_info = EmbeddingSpaceInfo(
            provider=self.embedding_provider.provider_name,
            model=self.embedding_provider.model_name,
            version=self.embedding_provider.model_version,
            dimension=self.embedding_provider.dimension,
            metric=self.embedding_provider.metric,
            space_id=self.embedding_provider.embedding_space_id,
        )

        is_ready = connected and (self.embedding_provider.dimension > 0)
        status = "ready" if is_ready else "unhealthy"

        return RetrievalHealthResponse(
            status=status,
            chroma_connected=connected,
            collection_name=self.vector_store.collection_name,
            total_chunks=chunk_count,
            embedding_space=space_info,
            is_ready=is_ready,
        )
