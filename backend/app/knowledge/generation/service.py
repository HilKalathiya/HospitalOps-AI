"""
HospitalOps AI — Knowledge Answer Service (Chunk 4.4).

Coordinates:
- Clinical out-of-scope query screening
- Provider readiness and configuration checks
- Direct in-memory invocation of Chunk 4.3 retrieval and context assembly
- Grounded answer generation and citation verification
- Non-sensitive operational telemetry logging
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from app.core.config import Settings, get_settings
from app.knowledge.generation.answer_generator import GroundedAnswerGenerator
from app.knowledge.generation.citation_validator import CitationValidator
from app.knowledge.generation.contracts import (
    AnswerHealthResponse,
    AnswerStatus,
    AnswerType,
    KnowledgeAnswerRequest,
    KnowledgeAnswerResponse,
    RetrievalSummary,
)
from app.knowledge.generation.prompt_builder import PROMPT_VERSION, is_clinical_query
from app.knowledge.generation.provider import (
    LLMProvider,
    NullLLMProvider,
    OpenAICompatibleProvider,
)
from app.knowledge.retrieval.contracts import (
    KnowledgeRetrievalRequest,
    RetrievalStatus,
)
from app.knowledge.retrieval.orchestrator import RetrievalContextOrchestrator
from app.models.user import UserDocument

logger = logging.getLogger(__name__)


def create_default_llm_provider(settings: Settings) -> LLMProvider:
    """Instantiate the configured LLM provider based on application settings."""
    if not settings.rag_generation_enabled:
        return NullLLMProvider(
            reason="RAG answer generation is disabled by configuration (RAG_GENERATION_ENABLED=False)."
        )

    provider_type = settings.rag_llm_provider.lower().strip()

    if provider_type in ("mock", "mock_llm", "mock_grounded_llm"):
        from app.knowledge.generation.provider import MockLLMProvider
        return MockLLMProvider()

    if provider_type == "openai_compatible":
        return OpenAICompatibleProvider(
            base_url=settings.rag_llm_base_url,
            api_key=settings.rag_llm_api_key,
            model_name=settings.rag_llm_model,
            timeout_seconds=settings.rag_llm_timeout_seconds,
        )

    return NullLLMProvider(
        reason=f"Configured LLM provider '{provider_type}' is unrecognized or uninitialized."
    )


class KnowledgeAnswerService:
    """Service orchestrating grounded question answering over hospital knowledge."""

    def __init__(
        self,
        orchestrator: RetrievalContextOrchestrator,
        provider: LLMProvider | None = None,
        settings: Settings | None = None,
        llm_provider: LLMProvider | None = None,
    ) -> None:
        self.orchestrator = orchestrator
        self.settings = settings or get_settings()
        chosen_provider = provider or llm_provider
        self.provider = chosen_provider or create_default_llm_provider(self.settings)
        self.generator = GroundedAnswerGenerator(provider=self.provider)

    async def generate_answer(
        self,
        request: KnowledgeAnswerRequest,
        current_user: UserDocument,
    ) -> KnowledgeAnswerResponse:
        """
        Execute grounded question answering with verification and provenance.
        """
        request_id = f"ans_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(UTC).isoformat()

        # 1. Fast Clinical Out-of-Scope Screening
        is_clinical, clinical_reason = is_clinical_query(request.query)
        if is_clinical:
            logger.info("Query screened as clinical out-of-scope | req_id=%s", request_id)
            empty_retrieval = RetrievalSummary(
                retrieval_id="none",
                status=RetrievalStatus.NO_RESULTS,
                candidate_count=0,
                selected_count=0,
                skipped_count=0,
                retrieval_duration_ms=0.0,
            )
            return KnowledgeAnswerResponse(
                request_id=request_id,
                status=AnswerStatus.OUT_OF_SCOPE,
                status_reason=clinical_reason,
                query=request.query,
                answer=(
                    "HospitalOps AI is an operational and administrative decision-support platform. "
                    "It is strictly prohibited from diagnosing patients, prescribing medication, "
                    "or formulating individual clinical treatment plans. Please consult a qualified "
                    "licensed clinician for medical decision-making."
                ),
                answer_type=AnswerType.OUT_OF_SCOPE,
                is_clinical_query=True,
                clinical_disclaimer=clinical_reason,
                citations=[],
                retrieved_sources=[],
                retrieval=empty_retrieval,
                generation=None,
                limitations=["Request involves patient-specific clinical decision making outside platform scope."],
                follow_up_questions=[],
                created_at=now_iso,
            )

        # 2. Check if Answer Generation is Configured and Available
        if self.provider.provider_name == "null" or not self.settings.rag_generation_enabled:
            logger.info("Generation unavailable | req_id=%s provider=%s", request_id, self.provider.provider_name)
            empty_retrieval = RetrievalSummary(
                retrieval_id="none",
                status=RetrievalStatus.NO_RESULTS,
                candidate_count=0,
                selected_count=0,
                skipped_count=0,
                retrieval_duration_ms=0.0,
            )
            return KnowledgeAnswerResponse(
                request_id=request_id,
                status=AnswerStatus.GENERATION_UNAVAILABLE,
                status_reason="RAG answer generation is currently disabled or no LLM provider is configured.",
                query=request.query,
                answer=(
                    "Grounded answer generation is currently unavailable. No language model provider is configured "
                    "or generation is disabled in application settings. Context retrieval remains active under the "
                    "Context Assembler tab."
                ),
                answer_type=AnswerType.INSUFFICIENT_EVIDENCE,
                citations=[],
                retrieved_sources=[],
                retrieval=empty_retrieval,
                generation=None,
                limitations=["Answer generation provider unconfigured."],
                follow_up_questions=[],
                created_at=now_iso,
            )

        # 3. Direct In-Memory Invocation of Chunk 4.3 Retrieval & Context Assembly
        retrieval_req = KnowledgeRetrievalRequest(
            query=request.query,
            top_k=request.top_k,
            candidate_k=request.candidate_k,
            max_context_tokens=request.max_context_tokens,
            filters=request.filters,
            context_ordering=request.context_ordering,
            include_formatted_context=True,
            min_relevance_threshold=request.min_relevance_threshold,
        )

        retrieval_res = await self.orchestrator.retrieve_context(
            request=retrieval_req,
            current_user=current_user,
        )

        retrieval_summary = RetrievalSummary(
            retrieval_id=retrieval_res.retrieval_id,
            status=retrieval_res.status,
            candidate_count=retrieval_res.metadata.candidate_count,
            selected_count=retrieval_res.metadata.selected_count,
            skipped_count=retrieval_res.metadata.skipped_count,
            retrieval_duration_ms=retrieval_res.metadata.retrieval_duration_ms,
            context_tokens_used=retrieval_res.metadata.assembled_token_count,
        )

        # 4. Handle Empty or Insufficient Retrieval States (No Model Call Needed)
        if retrieval_res.status == RetrievalStatus.NO_RESULTS:
            return KnowledgeAnswerResponse(
                request_id=request_id,
                status=AnswerStatus.NO_RESULTS,
                status_reason="No authorized operational guidelines or policies matched the question.",
                query=request.query,
                answer="No authorized hospital reference documents matching this inquiry were found in the knowledge base.",
                answer_type=AnswerType.INSUFFICIENT_EVIDENCE,
                citations=[],
                retrieved_sources=[],
                retrieval=retrieval_summary,
                generation=None,
                limitations=["No matching operational documents retrieved."],
                follow_up_questions=[],
                created_at=now_iso,
            )

        if retrieval_res.status == RetrievalStatus.INSUFFICIENT_CONTEXT:
            return KnowledgeAnswerResponse(
                request_id=request_id,
                status=AnswerStatus.INSUFFICIENT_EVIDENCE,
                status_reason=retrieval_res.status_reason or "Retrieved passages lack sufficient semantic relevance.",
                query=request.query,
                answer=(
                    "The hospital knowledge base contains documents with distant terminology, but none with sufficient "
                    "relevance to establish an evidence-grounded answer to your question."
                ),
                answer_type=AnswerType.INSUFFICIENT_EVIDENCE,
                citations=[],
                retrieved_sources=[],
                retrieval=retrieval_summary,
                generation=None,
                limitations=["Retrieved passages fell below minimum similarity grounding threshold."],
                follow_up_questions=[],
                created_at=now_iso,
            )

        if retrieval_res.status == RetrievalStatus.FAILED:
            return KnowledgeAnswerResponse(
                request_id=request_id,
                status=AnswerStatus.GENERATION_FAILED,
                status_reason="Knowledge retrieval stage failed.",
                query=request.query,
                answer="Failed to retrieve knowledge context.",
                answer_type=AnswerType.INSUFFICIENT_EVIDENCE,
                citations=[],
                retrieved_sources=[],
                retrieval=retrieval_summary,
                generation=None,
                limitations=["Retrieval failure occurred."],
                follow_up_questions=[],
                created_at=now_iso,
            )

        # 5. Build Authoritative Retrieved Sources
        retrieved_sources = CitationValidator.build_all_retrieved_references(
            available_citations=retrieval_res.citations,
            context_blocks=retrieval_res.context_blocks,
        )

        # 6. Execute Grounded Answer Generation
        (
            status,
            answer_type,
            answer_text,
            verified_citations,
            limitations,
            follow_ups,
            generation_meta,
            status_reason,
        ) = await self.generator.generate(
            query=request.query,
            formatted_context=retrieval_res.formatted_context,
            available_citations=retrieval_res.citations,
            context_blocks=retrieval_res.context_blocks,
            retrieval_status=retrieval_res.status,
            temperature=request.temperature,
            max_output_tokens=request.max_output_tokens,
        )

        generation_meta.retrieval_summary = retrieval_summary

        # Telemetry logging (never log user query text to protect privacy)
        logger.info(
            "RAG answer completed | req_id=%s status=%s citations=%d duration=%.2fms",
            request_id,
            status.value,
            len(verified_citations),
            generation_meta.duration_ms,
        )

        return KnowledgeAnswerResponse(
            request_id=request_id,
            status=status,
            status_reason=status_reason,
            query=request.query,
            answer=answer_text,
            answer_type=answer_type,
            citations=verified_citations,
            retrieved_sources=retrieved_sources,
            retrieval=retrieval_summary,
            generation=generation_meta,
            limitations=limitations,
            follow_up_questions=follow_ups,
            created_at=now_iso,
        )

    async def check_health(self) -> AnswerHealthResponse:
        """Inspect generation subsystem readiness."""
        retrieval_health = await self.orchestrator.retriever.check_health()
        provider_ready = await self.provider.check_health()

        is_ok = self.settings.rag_generation_enabled and provider_ready and retrieval_health.is_ready
        status_str = "ok" if is_ok else "degraded"

        return AnswerHealthResponse(
            status=status_str,
            generation_enabled=self.settings.rag_generation_enabled,
            provider_name=self.provider.provider_name,
            model_name=self.provider.model_name,
            provider_configured=(self.provider.provider_name != "null"),
            prompt_version=PROMPT_VERSION,
            retrieval_ready=retrieval_health.is_ready,
        )
