"""
HospitalOps AI — Knowledge Agent Tools (Milestone 5, Chunk 5.1).

Integrates the Chunk 4.2 Semantic Search and Chunk 4.4 Grounded Answer services
as secure, read-only tools for agentic reasoning.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from app.agents.contracts import ProvenanceCategory, ProvenanceItem
from app.agents.tools.base import AgentTool, ToolContext, ToolResult
from app.knowledge.generation.contracts import (
    CitationReference,
    KnowledgeAnswerRequest,
)
from app.knowledge.retrieval import KnowledgeSearchRequest
from app.models.knowledge import AccessLevel, DocumentCategory
from app.services.knowledge import KnowledgeService

logger = logging.getLogger(__name__)


class SearchHospitalKnowledgeInput(BaseModel):
    """Input parameters for searching hospital knowledge documents."""

    query: str = Field(min_length=2, max_length=500, description="Natural-language operational inquiry")
    top_k: int = Field(default=5, ge=1, le=15, description="Number of matching passages to return")
    category: str | None = Field(default=None, description="Optional category filter (e.g. 'CAPACITY_PLANNING', 'SOP')")


class SearchHospitalKnowledgeTool(AgentTool):
    """Tool that retrieves authorized hospital knowledge chunks using vector search."""

    def __init__(self, knowledge_service: KnowledgeService) -> None:
        self.service = knowledge_service

    @property
    def name(self) -> str:
        return "search_hospital_knowledge"

    @property
    def description(self) -> str:
        return (
            "Search verified hospital administrative guidelines, SOPs, clinical protocols, "
            "and equipment manuals for relevant excerpts using semantic vector retrieval."
        )

    @property
    def input_schema(self) -> type[BaseModel]:
        return SearchHospitalKnowledgeInput

    @property
    def required_permission(self) -> str:
        return "knowledge.read"

    async def execute(self, arguments: BaseModel, context: ToolContext) -> ToolResult:
        args = arguments if isinstance(arguments, SearchHospitalKnowledgeInput) else SearchHospitalKnowledgeInput.model_validate(arguments)

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
        summaries: list[str] = []

        for idx, res in enumerate(resp.results, start=1):
            source_id = f"S{idx}"
            title = getattr(res, "document_title", getattr(res, "title", "Document"))
            version = getattr(res, "document_version", getattr(res, "version", 1))
            text_content = getattr(res, "full_text", getattr(res, "content", getattr(res, "content_excerpt", "")))
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
                    access_level=res.access_level if isinstance(res.access_level, AccessLevel) else None,
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
            summaries.append(f"[{source_id}] {title}: {text_content[:200]}...")

        summary_text = (
            f"Found {len(resp.results)} relevant knowledge passages for query '{args.query}'.\n"
            + "\n".join(summaries[:4])
        )

        return ToolResult(
            success=True,
            data={"count": len(resp.results), "result_count": getattr(resp, "result_count", len(resp.results))},
            output_summary=summary_text,
            citations=citations,
            provenance_items=prov_items,
        )


class AnswerFromHospitalKnowledgeInput(BaseModel):
    """Input parameters for generating an evidence-grounded operational answer."""

    question: str = Field(min_length=3, max_length=500, description="Specific operational question to answer")
    top_k: int = Field(default=5, ge=1, le=10, description="Context retrieval chunk count")
    token_budget: int = Field(default=2000, ge=500, le=4000, description="Token budget for context assembly")
    category: str | None = Field(default=None, description="Optional category scope")


class AnswerFromHospitalKnowledgeTool(AgentTool):
    """Tool that uses the Grounded RAG Answer Generation service directly in-memory."""

    def __init__(self, knowledge_service: KnowledgeService) -> None:
        self.service = knowledge_service

    @property
    def name(self) -> str:
        return "answer_from_hospital_knowledge"

    @property
    def description(self) -> str:
        return (
            "Synthesize an evidence-grounded operational answer from hospital policies "
            "with verified citations and non-clinical guardrails."
        )

    @property
    def input_schema(self) -> type[BaseModel]:
        return AnswerFromHospitalKnowledgeInput

    @property
    def required_permission(self) -> str:
        return "knowledge.read"

    async def execute(self, arguments: BaseModel, context: ToolContext) -> ToolResult:
        args = arguments if isinstance(arguments, AnswerFromHospitalKnowledgeInput) else AnswerFromHospitalKnowledgeInput.model_validate(arguments)

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
                    label=f"{cit.title} (v{cit.version})",
                    details={
                        "source_id": cit.source_id,
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

        return ToolResult(
            success=True,
            data={
                "answer": resp.answer,
                "status": status_val,
                "confidence": conf_val,
                "limitations": resp.limitations,
            },
            output_summary=summary_text,
            citations=resp.citations,
            provenance_items=prov_items,
        )
