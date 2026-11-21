"""
HospitalOps AI — Agent Evidence Collection & Context Management (Milestone 5, Chunk 5.3).

Provides:
- EvidenceCategory: Domain semantic classification.
- AgentEvidence: Formally structured, auditable evidence item.
- AgentEvidenceCollector: In-memory scoped collector enforcing context budgets and domain safety.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field

from app.models.base import HospitalOpsBaseModel, utc_now

logger = logging.getLogger(__name__)

# Default maximum characters of aggregated evidence to prevent prompt explosion
DEFAULT_MAX_EVIDENCE_CHARS = 12000


class EvidenceCategory(str, Enum):
    """
    Domain semantic classification for operational evidence.
    Enforces strict distinction between observed reality, statistical projections,
    hypothetical simulations, and proposed optimization plans.
    """

    OBSERVED_DATA = "OBSERVED_DATA"
    FORECAST = "FORECAST"
    SIMULATION = "SIMULATION"
    OPTIMIZATION = "OPTIMIZATION"
    KNOWLEDGE_POLICY = "KNOWLEDGE_POLICY"


class AgentEvidence(HospitalOpsBaseModel):
    """
    Traceable, validated evidence artifact produced during agent tool execution.
    Preserves provenance and distinguishes empirical reality from projections or simulations.
    """

    evidence_id: str = Field(
        default_factory=lambda: f"ev_{uuid.uuid4().hex[:10]}",
        description="Unique evidence artifact identifier",
    )
    tool_id: str = Field(description="Identifier of the executing tool")
    tool_version: str = Field(default="1.0.0", description="Semver version of the tool contract")
    execution_step: int = Field(default=1, ge=1, description="Sequential step index where evidence was collected")
    category: EvidenceCategory = Field(description="Domain semantic classification")
    summary: str = Field(description="Sanitized summary of the gathered operational facts")
    data: dict[str, Any] = Field(default_factory=dict, description="Structured payload extracted from tool output")
    source_references: list[str] = Field(
        default_factory=list, description="IDs of underlying records (e.g. run ID, doc chunk ID)"
    )
    is_projection: bool = Field(
        default=False, description="True if evidence is a statistical prediction, NOT observed history"
    )
    is_hypothetical: bool = Field(
        default=False, description="True if evidence is a what-if simulation scenario, NOT real events"
    )
    is_recommendation: bool = Field(
        default=False, description="True if evidence is an optimization proposal, NOT an executed action"
    )
    created_at: datetime = Field(default_factory=utc_now)


class AgentEvidenceCollector:
    """
    Session-scoped evidence manager for a single agent invocation.
    Accumulates evidence from tool executions, applies context budgets,
    and formats evidence packages with strict domain safety headers.
    """

    def __init__(self, max_chars: int = DEFAULT_MAX_EVIDENCE_CHARS) -> None:
        self.max_chars = max_chars
        self._items: list[AgentEvidence] = []
        self._total_chars = 0

    @property
    def items(self) -> list[AgentEvidence]:
        return list(self._items)

    @property
    def count(self) -> int:
        return len(self._items)

    def add_evidence(
        self,
        tool_id: str,
        tool_version: str,
        category: EvidenceCategory,
        summary: str,
        data: Any,
        source_references: list[str],
        execution_step: int = 1,
    ) -> AgentEvidence:
        """
        Record a new piece of validated evidence from a tool execution.
        Sets appropriate domain flags according to category.
        """
        is_projection = category == EvidenceCategory.FORECAST
        is_hypothetical = category == EvidenceCategory.SIMULATION
        is_recommendation = category == EvidenceCategory.OPTIMIZATION

        if hasattr(data, "model_dump"):
            data_dict = data.model_dump(mode="json")
        elif isinstance(data, dict):
            data_dict = data
        elif data is None:
            data_dict = {}
        else:
            data_dict = {"value": data}

        evidence = AgentEvidence(
            tool_id=tool_id,
            tool_version=tool_version,
            execution_step=execution_step,
            category=category,
            summary=summary,
            data=data_dict,
            source_references=source_references,
            is_projection=is_projection,
            is_hypothetical=is_hypothetical,
            is_recommendation=is_recommendation,
            created_at=utc_now(),
        )

        item_len = len(summary)
        if self._total_chars + item_len > self.max_chars:
            logger.warning(
                "Evidence budget exceeded (total=%d, item=%d, limit=%d). Clamping summary.",
                self._total_chars,
                item_len,
                self.max_chars,
            )
            allowed = max(100, self.max_chars - self._total_chars)
            evidence.summary = summary[:allowed] + "... [Evidence truncated due to context budget]"

        self._items.append(evidence)
        self._total_chars += len(evidence.summary)
        return evidence

    def get_by_category(self, category: EvidenceCategory) -> list[AgentEvidence]:
        return [item for item in self._items if item.category == category]

    def get_all_source_references(self) -> list[str]:
        refs: list[str] = []
        for item in self._items:
            refs.extend(item.source_references)
        return list(dict.fromkeys(refs))

    def format_for_synthesis(self) -> str:
        """
        Format all collected evidence into an isolated, safe context block
        with explicit domain classification warnings.
        """
        if not self._items:
            return "No verified operational evidence collected."

        sections: list[str] = []
        for idx, ev in enumerate(self._items, 1):
            category_tag = str(ev.category)
            qualifiers: list[str] = []
            if ev.is_projection:
                qualifiers.append("STATISTICAL PROJECTION (Not Observed Reality)")
            if ev.is_hypothetical:
                qualifiers.append("WHAT-IF SIMULATION (Hypothetical Scenario)")
            if ev.is_recommendation:
                qualifiers.append("OPTIMIZATION RECOMMENDATION (Proposed, Not Executed)")

            qualifier_str = f" [{', '.join(qualifiers)}]" if qualifiers else ""

            header = f"[Evidence #{idx} | {category_tag}{qualifier_str} | Tool: {ev.tool_id}]"
            sources = f"Sources: {', '.join(ev.source_references) if ev.source_references else 'None'}"
            sections.append(f"{header}\n{sources}\n{ev.summary}")

        return "\n\n---\n\n".join(sections)
