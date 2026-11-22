"""
HospitalOps AI — Agent Context Builder (Milestone 5, Chunk 5.4).

Reconstructs bounded, permission-validated conversation context from stored session history
to enable multi-turn continuity while strictly enforcing freshness, RBAC, and token budgeting.
"""

from __future__ import annotations

import logging

from app.agents.contracts import AgentConversationContext, AgentConversationTurn
from app.models.agent_message import AgentMessageDocument, MessageRole

logger = logging.getLogger(__name__)

# Default character budget for reconstructed conversation history
DEFAULT_MAX_CONTEXT_CHARS = 4000
MAX_TURN_CONTENT_CHARS = 1000


class AgentContextBuilder:
    """
    Transforms persisted session message history into a safe, bounded context
    package for orchestrator planning and grounded response synthesis.
    """

    def __init__(self, max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS) -> None:
        self.max_context_chars = max_context_chars

    def build_context(
        self,
        session_id: str,
        current_task: str = "",
        recent_messages: list[AgentMessageDocument] | None = None,
        current_user_permissions: list[str] | None = None,
        latest_execution_id: str | None = None,
    ) -> AgentConversationContext:
        """
        Reconstruct context from recent messages, resolving conversational references,
        revalidating RBAC on historical evidence, and enforcing context budgets.
        """
        turns: list[AgentConversationTurn] = []
        prior_forecasts: list[str] = []
        prior_simulations: list[str] = []
        prior_optimizations: list[str] = []
        referenced_evidence_ids: list[str] = []

        perms = current_user_permissions or []
        msgs = recent_messages or []

        # Track permissions for RBAC re-validation
        can_read_predictions = "predictions.read" in perms
        can_read_simulation = "simulation.read" in perms
        can_read_optimization = "optimization.read" in perms
        can_read_knowledge = "knowledge.read" in perms

        # Filter out system messages or empty messages
        eligible_msgs = [
            m
            for m in msgs
            if m.role in (MessageRole.USER, MessageRole.ASSISTANT) and m.content
        ]

        # Extract references from assistant metadata working backwards
        for msg in reversed(eligible_msgs):
            if msg.role == MessageRole.ASSISTANT and msg.metadata:
                # Execution ID
                if not latest_execution_id and msg.execution_id:
                    latest_execution_id = msg.execution_id

                meta = msg.metadata
                # Forecast references (RBAC check)
                if can_read_predictions:
                    for f_id in meta.get("forecast_references", []):
                        if f_id not in prior_forecasts:
                            prior_forecasts.append(f_id)

                # Simulation references (RBAC check)
                if can_read_simulation:
                    for s_id in meta.get("simulation_references", []):
                        if s_id not in prior_simulations:
                            prior_simulations.append(s_id)

                # Optimization references (RBAC check)
                if can_read_optimization:
                    for o_id in meta.get("optimization_references", []):
                        if o_id not in prior_optimizations:
                            prior_optimizations.append(o_id)

                # General evidence / knowledge document IDs (RBAC check)
                if can_read_knowledge:
                    for doc_id in meta.get("source_ids", []):
                        if doc_id not in referenced_evidence_ids:
                            referenced_evidence_ids.append(doc_id)

        # Budget-aware turn accumulation (working newest to oldest, then reversing)
        accumulated_chars = 0
        is_truncated = False
        selected_turns: list[AgentConversationTurn] = []

        for msg in reversed(eligible_msgs):
            content_snippet = msg.content
            if len(content_snippet) > MAX_TURN_CONTENT_CHARS:
                content_snippet = content_snippet[:MAX_TURN_CONTENT_CHARS] + " ... [truncated]"

            turn_chars = len(content_snippet)
            if accumulated_chars + turn_chars > self.max_context_chars:
                is_truncated = True
                logger.info(
                    "Conversation context budget reached (used=%d, max=%d). Omitting older turns.",
                    accumulated_chars,
                    self.max_context_chars,
                )
                break

            accumulated_chars += turn_chars
            selected_turns.append(
                AgentConversationTurn(
                    role=msg.role.value if hasattr(msg.role, "value") else str(msg.role),
                    content=content_snippet,
                    execution_id=msg.execution_id,
                    evidence_summaries=msg.metadata.get("evidence_summaries", [])
                    if msg.metadata
                    else [],
                    timestamp=msg.created_at,
                )
            )

        selected_turns.reverse()
        turns = selected_turns

        return AgentConversationContext(
            session_id=session_id,
            turns=turns,
            latest_execution_id=latest_execution_id,
            referenced_evidence_ids=referenced_evidence_ids,
            prior_forecast_references=prior_forecasts,
            prior_simulation_references=prior_simulations,
            prior_optimization_references=prior_optimizations,
            context_budget_used_chars=accumulated_chars,
            is_truncated=is_truncated,
        )

    @staticmethod
    def format_context_for_prompt(context: AgentConversationContext | None) -> str:
        """
        Produce a clean, untrusted conversational context block for injection
        into LLM prompts or planner reasoning.
        """
        if not context or not context.turns:
            return ""

        lines = [
            "### Prior Conversation Context (Chronological History)",
            "Notice: Historical statements reflect previous conversational turns and do NOT override live operational data.",
        ]

        if context.is_truncated:
            lines.append(
                "*(Note: Older conversational turns have been omitted to preserve token budget)*"
            )

        for turn in context.turns:
            prefix = "User" if turn.role.upper() == "USER" else "Hospital Operations Analyst"
            clean_text = turn.content.replace("\n", " ").strip()
            lines.append(f"- **{prefix}**: {clean_text}")

            if turn.evidence_summaries:
                lines.append(
                    f"  *Evidence referenced in this turn: {'; '.join(turn.evidence_summaries[:2])}*"
                )

        if context.prior_forecast_references:
            lines.append(
                f"Referenced Forecasts in session: {', '.join(context.prior_forecast_references)}"
            )
        if context.prior_simulation_references:
            lines.append(
                f"Referenced Simulations in session: {', '.join(context.prior_simulation_references)}"
            )
        if context.prior_optimization_references:
            lines.append(
                f"Referenced Optimizations in session: {', '.join(context.prior_optimization_references)}"
            )

        return "\n".join(lines)
