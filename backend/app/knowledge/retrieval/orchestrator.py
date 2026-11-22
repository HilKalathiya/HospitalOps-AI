"""
HospitalOps AI — RAG Retrieval & Context Assembly Orchestrator (Chunk 4.3).

Coordinates:
1. Request validation and candidate search expansion (candidate_k)
2. Reuse of Chunk 4.2 KnowledgeRetriever semantic search and RBAC scoping
3. Relevance thresholding and sufficiency evaluation
4. Token-budget-aware chunk selection with boundary protection
5. Source citation generation ([S1], [S2]...)
6. Context ordering (relevance, document order, grouped by doc)
7. Prompt-safe formatted context assembly
8. Telemetry and retrieval status assignment (SUCCESS, NO_RESULTS, INSUFFICIENT_CONTEXT, PARTIAL_CONTEXT, FAILED)
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import UTC, datetime

from app.knowledge.retrieval.citation_builder import CitationBuilder
from app.knowledge.retrieval.context_builder import ContextBuilder
from app.knowledge.retrieval.contracts import (
    KnowledgeRetrievalRequest,
    KnowledgeRetrievalResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResult,
    RetrievalMetadata,
    RetrievalStatus,
)
from app.knowledge.retrieval.retriever import KnowledgeRetriever
from app.knowledge.retrieval.token_budget import TokenBudgetManager, get_token_count
from app.models.user import UserDocument

logger = logging.getLogger(__name__)

# Minimum semantic similarity below which results are deemed noise / ungrounded
MINIMUM_GROUNDING_SIMILARITY = 0.10


class RetrievalContextOrchestrator:
    """Orchestrates semantic search, token budgeting, citation generation, and context assembly."""

    def __init__(self, retriever: KnowledgeRetriever) -> None:
        self.retriever = retriever

    async def retrieve_context(
        self,
        request: KnowledgeRetrievalRequest,
        current_user: UserDocument | None = None,
    ) -> KnowledgeRetrievalResponse:
        """
        Execute RAG context retrieval and assembly within the specified token budget.
        """
        start_time = time.perf_counter()
        retrieval_id = f"ret_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(UTC).isoformat()
        ordering_val = (
            request.context_ordering.value
            if hasattr(request.context_ordering, "value")
            else str(request.context_ordering)
        )

        # 1. Expand candidate search limit to allow token-budget and diversity selection
        candidate_k = request.candidate_k or max(request.top_k * 3, 15)
        candidate_k = min(candidate_k, 100)

        search_request = KnowledgeSearchRequest(
            query=request.query,
            top_k=candidate_k,
            filters=request.filters,
        )

        # 2. Invoke Chunk 4.2 semantic search
        search_response = await self.retriever.search(search_request, current_user=current_user)

        # 3. Handle zero search results
        if search_response.result_count == 0 or not search_response.results:
            duration = (time.perf_counter() - start_time) * 1000
            meta = RetrievalMetadata(
                embedding_space=search_response.embedding_space,
                candidate_count=0,
                retrieved_count=0,
                selected_count=0,
                skipped_count=0,
                token_budget=request.max_context_tokens,
                assembled_token_count=0,
                overhead_token_count=0,
                token_count_method="tiktoken_cl100k_base",
                retrieval_duration_ms=round(duration, 2),
                context_ordering=ordering_val,
            )
            return KnowledgeRetrievalResponse(
                retrieval_id=retrieval_id,
                status=RetrievalStatus.NO_RESULTS,
                status_reason="No authorized knowledge documents matched the query criteria.",
                query=request.query,
                created_at=now_iso,
                metadata=meta,
                context_blocks=[],
                citations=[],
                formatted_context=None,
                skipped_chunks=[],
                limitations=[
                    "No matching operational guidelines or policies found in knowledge base."
                ],
                warnings=[],
            )

        # 4. Filter by minimum relevance threshold if requested
        candidates = search_response.results
        skipped_for_threshold: list[KnowledgeSearchResult] = []

        if request.min_relevance_threshold is not None:
            filtered_candidates = []
            for c in candidates:
                if c.similarity_score >= request.min_relevance_threshold:
                    filtered_candidates.append(c)
                else:
                    skipped_for_threshold.append(c)
            candidates = filtered_candidates

        # 5. Evaluate context sufficiency
        if not candidates:
            duration = (time.perf_counter() - start_time) * 1000
            meta = RetrievalMetadata(
                embedding_space=search_response.embedding_space,
                candidate_count=search_response.result_count,
                retrieved_count=len(search_response.results),
                selected_count=0,
                skipped_count=len(skipped_for_threshold),
                token_budget=request.max_context_tokens,
                assembled_token_count=0,
                overhead_token_count=0,
                token_count_method="tiktoken_cl100k_base",
                retrieval_duration_ms=round(duration, 2),
                context_ordering=ordering_val,
            )
            return KnowledgeRetrievalResponse(
                retrieval_id=retrieval_id,
                status=RetrievalStatus.INSUFFICIENT_CONTEXT,
                status_reason=f"All {search_response.result_count} candidate chunks fell below the minimum similarity threshold of {request.min_relevance_threshold}.",
                query=request.query,
                created_at=now_iso,
                metadata=meta,
                context_blocks=[],
                citations=[],
                formatted_context=None,
                skipped_chunks=[],
                limitations=[
                    "Retrieved material lacks sufficient semantic relevance to support reliable grounding."
                ],
                warnings=[
                    "Consider lowering the minimum similarity threshold or using broader terminology."
                ],
            )

        # Check for ungrounded noise (top hit is too weak)
        top_score = candidates[0].similarity_score
        if top_score < MINIMUM_GROUNDING_SIMILARITY:
            duration = (time.perf_counter() - start_time) * 1000
            meta = RetrievalMetadata(
                embedding_space=search_response.embedding_space,
                candidate_count=search_response.result_count,
                retrieved_count=len(candidates),
                selected_count=0,
                skipped_count=len(candidates),
                token_budget=request.max_context_tokens,
                assembled_token_count=0,
                overhead_token_count=0,
                token_count_method="tiktoken_cl100k_base",
                retrieval_duration_ms=round(duration, 2),
                context_ordering=ordering_val,
            )
            return KnowledgeRetrievalResponse(
                retrieval_id=retrieval_id,
                status=RetrievalStatus.INSUFFICIENT_CONTEXT,
                status_reason=f"Top candidate similarity score ({top_score:.3f}) is below the grounding threshold ({MINIMUM_GROUNDING_SIMILARITY}).",
                query=request.query,
                created_at=now_iso,
                metadata=meta,
                context_blocks=[],
                citations=[],
                formatted_context=None,
                skipped_chunks=[],
                limitations=[
                    "Knowledge base contains no closely related operational policies for this question."
                ],
                warnings=[
                    "The retrieved text is not sufficiently similar to guarantee factual relevance."
                ],
            )

        # 6. Token Budget Allocation
        budget_mgr = TokenBudgetManager(max_context_tokens=request.max_context_tokens)
        selected_chunks: list[KnowledgeSearchResult] = []

        for candidate in candidates:
            # If target top_k is reached, record any remaining candidates as skipped
            if len(selected_chunks) >= request.top_k:
                content_tok = get_token_count(candidate.full_text)
                budget_mgr.record_skipped(
                    candidate,
                    rank=candidate.ranking_position,
                    content_tokens=content_tok,
                    reason="top_k_limit_reached",
                )
                continue

            content_tokens = get_token_count(candidate.full_text)
            overhead_tokens = CitationBuilder.estimate_citation_overhead(
                candidate, citation_number=len(selected_chunks) + 1
            )

            if budget_mgr.can_fit(content_tokens, overhead_tokens):
                budget_mgr.allocate(content_tokens, overhead_tokens)
                selected_chunks.append(candidate)
            else:
                budget_mgr.record_skipped(
                    candidate,
                    rank=candidate.ranking_position,
                    content_tokens=content_tokens,
                    reason="token_budget_exceeded",
                )

        # 7. Check if any chunks could fit
        if not selected_chunks:
            duration = (time.perf_counter() - start_time) * 1000
            meta = RetrievalMetadata(
                embedding_space=search_response.embedding_space,
                candidate_count=search_response.result_count,
                retrieved_count=len(candidates),
                selected_count=0,
                skipped_count=len(budget_mgr.skipped_chunks),
                token_budget=request.max_context_tokens,
                assembled_token_count=0,
                overhead_token_count=0,
                token_count_method=budget_mgr.token_count_method,
                retrieval_duration_ms=round(duration, 2),
                context_ordering=ordering_val,
            )
            return KnowledgeRetrievalResponse(
                retrieval_id=retrieval_id,
                status=RetrievalStatus.INSUFFICIENT_CONTEXT,
                status_reason=f"All candidate chunks exceed the maximum context token budget of {request.max_context_tokens} tokens.",
                query=request.query,
                created_at=now_iso,
                metadata=meta,
                context_blocks=[],
                citations=[],
                formatted_context=None,
                skipped_chunks=budget_mgr.skipped_chunks,
                limitations=[
                    "Token budget too small to accommodate even the highest-ranked chunk."
                ],
                warnings=["Increase max_context_tokens to allow full chunk assembly."],
            )

        # 8. Apply Context Ordering Strategy
        ordered_chunks = ContextBuilder.order_chunks(
            selected_chunks, strategy=request.context_ordering
        )

        # 9. Assemble Structured Context Blocks, Citations, and Formatted Context String
        context_blocks, citations, formatted_context = ContextBuilder.build_context_package(
            ordered_chunks, include_formatted_context=request.include_formatted_context
        )

        # 10. Determine Final Retrieval Status
        skipped_due_to_budget = [
            s for s in budget_mgr.skipped_chunks if s.skip_reason == "token_budget_exceeded"
        ]

        if skipped_due_to_budget:
            status = RetrievalStatus.PARTIAL_CONTEXT
            status_reason = (
                f"Assembled {len(context_blocks)} chunks ({budget_mgr.total_tokens} tokens); "
                f"{len(skipped_due_to_budget)} candidate chunk(s) omitted due to token budget limit."
            )
        else:
            status = RetrievalStatus.SUCCESS
            status_reason = f"Successfully assembled {len(context_blocks)} authorized context blocks within token budget."

        duration = (time.perf_counter() - start_time) * 1000

        meta = RetrievalMetadata(
            embedding_space=search_response.embedding_space,
            candidate_count=search_response.result_count,
            retrieved_count=len(candidates),
            selected_count=len(context_blocks),
            skipped_count=len(budget_mgr.skipped_chunks),
            token_budget=request.max_context_tokens,
            assembled_token_count=budget_mgr.total_tokens,
            overhead_token_count=budget_mgr.overhead_tokens,
            token_count_method=budget_mgr.token_count_method,
            retrieval_duration_ms=round(duration, 2),
            context_ordering=ordering_val,
        )

        # Telemetry logging (never log user query text to protect privacy)
        logger.info(
            "RAG context retrieval completed | rid=%s status=%s blocks=%d tokens=%d duration=%.2fms",
            retrieval_id,
            status.value if hasattr(status, "value") else str(status),
            len(context_blocks),
            budget_mgr.total_tokens,
            duration,
        )

        return KnowledgeRetrievalResponse(
            retrieval_id=retrieval_id,
            status=status,
            status_reason=status_reason,
            query=request.query,
            created_at=now_iso,
            metadata=meta,
            context_blocks=context_blocks,
            citations=citations,
            formatted_context=formatted_context,
            skipped_chunks=budget_mgr.skipped_chunks,
            limitations=[
                "Retrieved passages provide operational decision support only and do not constitute clinical diagnostic authority."
            ],
            warnings=[],
        )
