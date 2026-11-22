"""
HospitalOps AI — Knowledge Agent Tools (Milestone 5, Chunks 5.1 & 5.2).

Integrates the Chunk 4.2 Semantic Search and Chunk 4.4 Grounded Answer services
as secure, standardized, read-only tools with typed input and output contracts.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from app.agents.contracts import ProvenanceCategory, ProvenanceItem, ToolCategory
from app.agents.tools.base import AgentTool, ToolContext, ToolResult
from app.knowledge.generation.contracts import (
    CitationReference,
    KnowledgeAnswerRequest,
)
from app.knowledge.retrieval import KnowledgeSearchRequest
from app.models.knowledge import AccessLevel, DocumentCategory
from app.services.knowledge import KnowledgeService

logger = logging.getLogger(__name__)


# ── Tool 1: Hospital Knowledge Search ─────────────────────────────────────────


class SearchHospitalKnowledgeInput(BaseModel):
    """Input parameters for searching hospital knowledge documents."""

    query: str = Field(
        min_length=2, max_length=500, description="Natural-language operational inquiry"
    )
    top_k: int = Field(default=5, ge=1, le=15, description="Number of matching passages to return")
    category: str | None = Field(
        default=None, description="Optional category filter (e.g. 'CAPACITY_PLANNING', 'SOP')"
    )


class KnowledgeSearchHit(BaseModel):
    """Clean individual document passage excerpt."""

    document_id: str
    document_title: str
    document_version: int
    chunk_id: str
    chunk_index: int
    section_title: str | None = None
    content_excerpt: str
    similarity_score: float
    category: str | None = None
    access_level: str | None = None


class SearchHospitalKnowledgeOutput(BaseModel):
    """Standardized output schema for hospital knowledge search."""

    query: str = Field(description="Search inquiry query")
    count: int = Field(ge=0, description="Count of passages retrieved")
    result_count: int = Field(ge=0, description="Total matching candidate count")
    results: list[KnowledgeSearchHit] = Field(
        default_factory=list, description="Top matching excerpts"
    )


class SearchHospitalKnowledgeTool(AgentTool):
    """Tool that retrieves authorized hospital knowledge chunks using vector search."""

    def __init__(self, knowledge_service: KnowledgeService) -> None:
        self.service = knowledge_service

    @property
    def name(self) -> str:
        return "search_hospital_knowledge"

    @property
    def display_name(self) -> str:
        return "Hospital Knowledge Search"

    @property
    def description(self) -> str:
        return (
            "Search verified hospital administrative guidelines, SOPs, clinical protocols, "
            "and equipment manuals for relevant excerpts using semantic vector retrieval."
        )

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.KNOWLEDGE

    @property
    def schema_version(self) -> str:
        return "1.0.0"

    @property
    def input_schema(self) -> type[BaseModel]:
        return SearchHospitalKnowledgeInput

    @property
    def output_schema(self) -> type[BaseModel]:
        return SearchHospitalKnowledgeOutput

    @property
    def required_permission(self) -> str:
        return "knowledge.read"

    @property
    def tags(self) -> list[str]:
        return ["knowledge", "semantic-search", "rag", "sop", "policy", "retrieval"]

    @property
    def timeout_seconds(self) -> float:
        return 20.0

    async def execute(self, arguments: BaseModel, context: ToolContext) -> ToolResult:
        args = (
            arguments
            if isinstance(arguments, SearchHospitalKnowledgeInput)
            else SearchHospitalKnowledgeInput.model_validate(arguments)
        )

        cat = None
        if args.category:
            try:
                cat = DocumentCategory(args.category.upper())
            except ValueError:
                cat = None

        search_req = KnowledgeSearchRequest(
            query=args.query,
            top_k=args.top_k,
            category=cat,
        )

        try:
            resp = await self.service.search(request=search_req, current_user=context.user)
        except Exception as exc:
            logger.warning("Knowledge search tool failed | query=%s err=%s", args.query, exc)
            return ToolResult(
                success=False,
                error_message=f"Knowledge search failed: {exc}",
                output_summary=f"Failed to search hospital knowledge: {exc}",
            )

        citations: list[CitationReference] = []
        prov_items: list[ProvenanceItem] = []
        hits: list[KnowledgeSearchHit] = []
        summaries: list[str] = []

        for idx, res in enumerate(resp.results, start=1):
            source_id = f"S{idx}"
            title = getattr(res, "document_title", getattr(res, "title", "Document"))
            version = getattr(res, "document_version", getattr(res, "version", 1))
            text_content = getattr(
                res, "full_text", getattr(res, "content", getattr(res, "content_excerpt", ""))
            )
            section = getattr(res, "section_title", None)

            citations.append(
                CitationReference(
                    citation_id=source_id,
                    document_id=res.document_id,
                    document_title=title,
                    document_version=version,
                    section_title=section,
                    chunk_id=res.chunk_id,
                    source_reference=f"{title} (v{version})",
                    similarity_score=res.similarity_score,
                    category=res.category if isinstance(res.category, DocumentCategory) else None,
                    access_level=res.access_level
                    if isinstance(res.access_level, AccessLevel)
                    else None,
                    excerpt=text_content[:300] if text_content else None,
                )
            )
            prov_items.append(
                ProvenanceItem(
                    category=ProvenanceCategory.KNOWLEDGE,
                    id=res.document_id,
                    label=f"{title} (v{version})",
                    details={
                        "chunk_id": res.chunk_id,
                        "section": section,
                        "similarity": round(res.similarity_score, 3),
                    },
                )
            )
            hits.append(
                KnowledgeSearchHit(
                    document_id=res.document_id,
                    document_title=title,
                    document_version=version,
                    chunk_id=res.chunk_id,
                    chunk_index=getattr(res, "chunk_index", 0),
                    section_title=section,
                    content_excerpt=text_content[:300] if text_content else "",
                    similarity_score=res.similarity_score,
                    category=res.category.value
                    if hasattr(res.category, "value")
                    else str(res.category or ""),
                    access_level=res.access_level.value
                    if hasattr(res.access_level, "value")
                    else str(res.access_level or ""),
                )
            )
            summaries.append(f"[{source_id}] {title}: {text_content[:200]}...")

        summary_text = (
            f"Found {len(resp.results)} relevant knowledge passages for query '{args.query}'.\n"
            + "\n".join(summaries[:4])
        )

        output_data = SearchHospitalKnowledgeOutput(
            query=args.query,
            count=len(resp.results),
            result_count=getattr(resp, "result_count", len(resp.results)),
            results=hits,
        )

        return ToolResult(
            success=True,
            data=output_data,
            output_summary=summary_text,
            citations=citations,
            provenance_items=prov_items,
        )


# ── Tool 2: Grounded Hospital Knowledge Answer ────────────────────────────────


class AnswerFromHospitalKnowledgeInput(BaseModel):
    """Input parameters for generating an evidence-grounded operational answer."""

    question: str = Field(
        min_length=3, max_length=500, description="Specific operational question to answer"
    )
    top_k: int = Field(default=5, ge=1, le=10, description="Context retrieval chunk count")
    token_budget: int = Field(
        default=2000, ge=500, le=4000, description="Token budget for context assembly"
    )
    category: str | None = Field(default=None, description="Optional category scope")


class AnswerFromHospitalKnowledgeOutput(BaseModel):
    """Standardized output schema for grounded knowledge answering."""

    question: str = Field(description="Operational question submitted")
    answer: str = Field(description="Synthesized evidence-grounded answer")
    status: str = Field(description="Answer status: ANSWERED, REJECTED, etc.")
    confidence: str = Field(default="HIGH", description="Assessed confidence level")
    limitations: list[str] = Field(
        default_factory=list, description="Noted limitations or policy scope caveats"
    )
    citations_count: int = Field(default=0, ge=0, description="Number of verified source citations")


class AnswerFromHospitalKnowledgeTool(AgentTool):
    """Tool that uses the Grounded RAG Answer Generation service directly in-memory."""

    def __init__(self, knowledge_service: KnowledgeService) -> None:
        self.service = knowledge_service

    @property
    def name(self) -> str:
        return "answer_from_hospital_knowledge"

    @property
    def display_name(self) -> str:
        return "Grounded Knowledge Answer"

    @property
    def description(self) -> str:
        return (
            "Synthesize an evidence-grounded operational answer from hospital policies "
            "with verified citations and non-clinical guardrails."
        )

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.KNOWLEDGE

    @property
    def schema_version(self) -> str:
        return "1.0.0"

    @property
    def input_schema(self) -> type[BaseModel]:
        return AnswerFromHospitalKnowledgeInput

    @property
    def output_schema(self) -> type[BaseModel]:
        return AnswerFromHospitalKnowledgeOutput

    @property
    def required_permission(self) -> str:
        return "knowledge.read"

    @property
    def tags(self) -> list[str]:
        return ["knowledge", "grounded-qa", "rag", "citations", "policy"]

    @property
    def timeout_seconds(self) -> float:
        return 30.0

    async def execute(self, arguments: BaseModel, context: ToolContext) -> ToolResult:
        args = (
            arguments
            if isinstance(arguments, AnswerFromHospitalKnowledgeInput)
            else AnswerFromHospitalKnowledgeInput.model_validate(arguments)
        )

        cat = None
        if args.category:
            try:
                cat = DocumentCategory(args.category.upper())
            except ValueError:
                cat = None

        req = KnowledgeAnswerRequest(
            question=args.question,
            top_k=args.top_k,
            token_budget=args.token_budget,
            category=cat,
        )

        try:
            resp = await self.service.generate_answer(request=req, current_user=context.user)
        except Exception as exc:
            logger.warning("Knowledge answer tool failed | question=%s err=%s", args.question, exc)
            return ToolResult(
                success=False,
                error_message=f"Knowledge answer generation failed: {exc}",
                output_summary=f"Failed to generate answer from knowledge base: {exc}",
            )

        prov_items: list[ProvenanceItem] = []
        for cit in resp.citations:
            prov_items.append(
                ProvenanceItem(
                    category=ProvenanceCategory.KNOWLEDGE,
                    id=cit.document_id,
                    label=f"{cit.document_title} (v{cit.document_version})",
                    details={
                        "source_id": cit.citation_id,
                        "section": cit.section_title,
                    },
                )
            )

        status_val = resp.status.value if hasattr(resp.status, "value") else str(resp.status)
        conf_val = getattr(resp, "confidence_assessment", "HIGH")

        summary_text = (
            f"Knowledge Answer (Status: {status_val}, Confidence: {conf_val}):\n"
            f"{resp.answer[:400]}..."
        )

        output_data = AnswerFromHospitalKnowledgeOutput(
            question=args.question,
            answer=resp.answer,
            status=status_val,
            confidence=conf_val,
            limitations=resp.limitations,
            citations_count=len(resp.citations),
        )

        return ToolResult(
            success=True,
            data=output_data,
            output_summary=summary_text,
            citations=resp.citations,
            provenance_items=prov_items,
        )
