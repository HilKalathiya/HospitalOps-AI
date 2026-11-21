"""
HospitalOps AI — Agent Execution Runtime (Milestone 5, Chunk 5.1).

Coordinates the bounded multi-step agent execution lifecycle:
RECEIVED -> VALIDATING -> SCOPE_CHECK -> PLANNING -> EXECUTING_TOOLS ->
EVALUATING_RESULTS -> GENERATING_FINAL_RESPONSE -> COMPLETED.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

from app.agents.contracts import (
    AgentExecutionStatus,
    AgentHealthResponse,
    AgentRunExecutionMetadata,
    AgentRunRequest,
    AgentRunResponse,
    ProvenanceItem,
    StopReason,
    ToolCallRecord,
)
from app.agents.planner import AgentPlanner
from app.agents.policies import (
    DISCLAIMER_TEXT,
    AgentPolicyEnforcer,
)
from app.agents.registry import AgentRegistry, ToolRegistry
from app.agents.tools.base import ToolContext
from app.core.security import get_permissions_for_role
from app.knowledge.generation.contracts import CitationReference
from app.knowledge.generation.provider import LLMProvider
from app.models.base import utc_now
from app.models.user import UserDocument

logger = logging.getLogger(__name__)


class AgentRuntime:
    """Bounded, policy-governed runtime for the Hospital Operations Analyst Agent."""

    VERSION = "1.0.0"

    def __init__(
        self,
        tool_registry: ToolRegistry,
        agent_registry: AgentRegistry,
        provider: LLMProvider,
    ) -> None:
        self.tool_registry = tool_registry
        self.agent_registry = agent_registry
        self.provider = provider
        self.planner = AgentPlanner(provider=provider, tools=tool_registry.list_all())

    async def check_health(self) -> AgentHealthResponse:
        """Inspect agent framework and provider readiness."""
        is_healthy = False
        try:
            is_healthy = await self.provider.check_health()
        except Exception as exc:
            logger.debug("Provider health check failed: %s", exc)

        all_tools = [t.name for t in self.tool_registry.list_all()]
        provider_name = self.provider.provider_name
        is_configured = provider_name != "null"

        status_str = "ready" if (is_configured and is_healthy) else ("degraded" if is_configured else "unavailable")

        return AgentHealthResponse(
            status=status_str,
            provider_configured=is_configured,
            provider_healthy=is_healthy,
            provider_name=provider_name,
            model_name=self.provider.model_name,
            registered_agents_count=len(self.agent_registry.list_all()),
            registered_tools_count=len(all_tools),
            registered_tools=all_tools,
            agent_version=self.VERSION,
        )

    async def run(
        self,
        request: AgentRunRequest,
        current_user: UserDocument,
    ) -> AgentRunResponse:
        """
        Execute an agent run with bounded reasoning, typed tool invocation,
        and evidence synthesis.
        """
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        start_time = time.perf_counter()

        logger.info(
            "Agent run initiated | run_id=%s agent_id=%s user_id=%s task_len=%d",
            run_id,
            request.agent_id,
            current_user.user_id,
            len(request.task),
        )

        # 1. VALIDATING AGENT LOOKUP
        agent_meta = self.agent_registry.get(request.agent_id)
        if not agent_meta:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return AgentRunResponse(
                run_id=run_id,
                agent_id=request.agent_id,
                agent_name="Unknown Agent",
                status=AgentExecutionStatus.REJECTED,
                final_answer=f"Agent '{request.agent_id}' is not registered in the system.",
                execution=AgentRunExecutionMetadata(
                    steps_completed=0,
                    tool_calls=0,
                    duration_ms=duration_ms,
                    stop_reason=StopReason.NO_RELEVANT_TOOLS,
                    model=self.provider.model_name,
                    provider=self.provider.provider_name,
                ),
                limitations=["Agent not found in registry"],
            )

        # 2. CLAMP EXECUTION BOUNDS
        opts = request.options
        max_steps = min(10, max(1, opts.max_steps))
        max_tool_calls = min(8, max(1, opts.max_tool_calls))
        timeout_seconds = min(60.0, max(5.0, opts.timeout_seconds))

        # 3. SCOPE CHECK: CLINICAL QUERY SCREENING
        is_clinical, refusal_reason = AgentPolicyEnforcer.check_clinical_scope(request.task)
        if is_clinical:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return AgentRunResponse(
                run_id=run_id,
                agent_id=agent_meta.agent_id,
                agent_name=agent_meta.name,
                status=AgentExecutionStatus.REJECTED,
                final_answer=(
                    f"Out of Scope Advisory: {refusal_reason}\n\n"
                    "HospitalOps AI is an operational decision intelligence platform. "
                    "For clinical emergencies, patient diagnoses, or treatment prescriptions, "
                    "please consult the attending physician or hospital clinical team directly."
                ),
                execution=AgentRunExecutionMetadata(
                    steps_completed=0,
                    tool_calls=0,
                    duration_ms=duration_ms,
                    stop_reason=StopReason.OUT_OF_SCOPE,
                    model=self.provider.model_name,
                    provider=self.provider.provider_name,
                ),
                limitations=[
                    "Clinical queries are prohibited under the HospitalOps AI constitution.",
                    DISCLAIMER_TEXT,
                ],
            )

        # 4. RESOLVE USER PERMISSIONS & CONTEXT
        user_permissions = get_permissions_for_role(current_user.role)
        tool_context = ToolContext(
            user=current_user,
            permissions=user_permissions,
            department_id=current_user.department_id,
            run_id=run_id,
        )

        # 5. EXECUTION LOOP
        step_count = 0
        tool_calls_count = 0
        tool_trace: list[ToolCallRecord] = []
        provenance_items: list[ProvenanceItem] = []
        citations: list[CitationReference] = []
        call_history: list[tuple[str, str]] = []
        execution_history: list[dict[str, Any]] = []

        stop_reason = StopReason.SUFFICIENT_EVIDENCE
        final_answer_text = ""
        final_limitations: list[str] = []

        while step_count < max_steps:
            elapsed = time.perf_counter() - start_time
            if elapsed >= timeout_seconds:
                logger.warning("Agent run timed out | run_id=%s elapsed=%.1fs limit=%.1fs", run_id, elapsed, timeout_seconds)
                stop_reason = StopReason.TIMEOUT
                break

            step_count += 1

            # Plan next action
            try:
                decision = await self.planner.plan_next_action(
                    task=request.task,
                    execution_history=execution_history,
                    step_index=step_count,
                )
            except Exception as exc:
                logger.error("Planner threw exception | run_id=%s step=%d err=%s", run_id, step_count, exc)
                stop_reason = StopReason.PROVIDER_UNAVAILABLE
                final_answer_text = f"Agent reasoning interrupted by unexpected planner error: {exc}"
                break

            # Action: FINAL ANSWER
            if decision.decision == "FINAL_ANSWER":
                final_answer_text = decision.answer
                final_limitations.extend(decision.limitations)
                stop_reason = StopReason.FINAL_ANSWER_READY
                break

            # Action: CALL TOOL
            if decision.decision == "CALL_TOOL":
                tool_name = decision.tool_name or ""
                if tool_calls_count >= max_tool_calls:
                    logger.info("Maximum tool calls limit reached | run_id=%s count=%d", run_id, tool_calls_count)
                    stop_reason = StopReason.MAX_TOOL_CALLS_REACHED
                    break

                tool = self.tool_registry.get(tool_name)
                if not tool:
                    logger.warning("Agent requested unregistered tool | tool=%s", tool_name)
                    tool_trace.append(
                        ToolCallRecord(
                            step_index=step_count,
                            tool_name=tool_name,
                            reason=decision.reason,
                            arguments=decision.arguments,
                            status="BLOCKED",
                            duration_ms=0.0,
                            output_summary=f"Tool '{tool_name}' is not in the registered allowlist.",
                            error_message="Unregistered tool requested.",
                        )
                    )
                    execution_history.append(
                        {
                            "tool_name": tool_name,
                            "arguments": decision.arguments,
                            "reason": decision.reason,
                            "output_summary": f"Error: Tool '{tool_name}' does not exist.",
                        }
                    )
                    continue

                # Policy: Permission verification
                allowed, denial_reason = AgentPolicyEnforcer.check_tool_permission(user_permissions, tool)
                if not allowed:
                    tool_trace.append(
                        ToolCallRecord(
                            step_index=step_count,
                            tool_name=tool.name,
                            reason=decision.reason,
                            arguments=decision.arguments,
                            status="BLOCKED",
                            duration_ms=0.0,
                            output_summary=denial_reason or "Permission denied.",
                            error_message=denial_reason,
                        )
                    )
                    execution_history.append(
                        {
                            "tool_name": tool.name,
                            "arguments": decision.arguments,
                            "reason": decision.reason,
                            "output_summary": f"Permission Denied: {denial_reason}",
                        }
                    )
                    continue

                # Policy: Duplicate call loop prevention
                if AgentPolicyEnforcer.is_duplicate_call(call_history, tool.name, decision.arguments):
                    logger.warning("Duplicate identical tool call blocked | tool=%s", tool.name)
                    tool_trace.append(
                        ToolCallRecord(
                            step_index=step_count,
                            tool_name=tool.name,
                            reason=decision.reason,
                            arguments=decision.arguments,
                            status="BLOCKED",
                            duration_ms=0.0,
                            output_summary="Duplicate identical tool call blocked by loop prevention policy.",
                            error_message="Repeated identical tool call.",
                        )
                    )
                    stop_reason = StopReason.LIMIT_REACHED
                    break

                # Execute authorized tool
                import json
                call_history.append((tool.name, json.dumps(decision.arguments, sort_keys=True, default=str)))
                tool_calls_count += 1

                t_start = time.perf_counter()
                try:
                    # Validate arguments against schema
                    validated_args = tool.input_schema.model_validate(decision.arguments)
                    result = await asyncio.wait_for(
                        tool.execute(validated_args, tool_context),
                        timeout=min(25.0, timeout_seconds),
                    )
                    t_dur = (time.perf_counter() - t_start) * 1000

                    # Accumulate citations and provenance
                    provenance_items.extend(result.provenance_items)
                    citations.extend(result.citations)

                    # Deduplicate citations by source_id or document_id
                    seen_sources: set[str] = set()
                    unique_citations: list[CitationReference] = []
                    for c in citations:
                        c_id = f"{c.document_id}_{c.chunk_id}"
                        if c_id not in seen_sources:
                            seen_sources.add(c_id)
                            unique_citations.append(c)
                    citations = unique_citations

                    tool_trace.append(
                        ToolCallRecord(
                            step_index=step_count,
                            tool_name=tool.name,
                            reason=decision.reason,
                            arguments=decision.arguments,
                            status="SUCCESS" if result.success else "FAILED",
                            duration_ms=round(t_dur, 2),
                            output_summary=result.output_summary[:800],
                            error_message=result.error_message,
                            sources_found=len(result.provenance_items),
                            provenance_ids=[p.id for p in result.provenance_items],
                        )
                    )

                    execution_history.append(
                        {
                            "tool_name": tool.name,
                            "arguments": decision.arguments,
                            "reason": decision.reason,
                            "output_summary": result.output_summary,
                        }
                    )

                except TimeoutError:
                    t_dur = (time.perf_counter() - t_start) * 1000
                    logger.warning("Tool execution timed out | tool=%s", tool.name)
                    tool_trace.append(
                        ToolCallRecord(
                            step_index=step_count,
                            tool_name=tool.name,
                            reason=decision.reason,
                            arguments=decision.arguments,
                            status="FAILED",
                            duration_ms=round(t_dur, 2),
                            output_summary="Tool execution timed out.",
                            error_message="Tool execution timeout.",
                        )
                    )
                    execution_history.append(
                        {
                            "tool_name": tool.name,
                            "arguments": decision.arguments,
                            "reason": decision.reason,
                            "output_summary": "Error: Tool execution timed out.",
                        }
                    )
                except Exception as exc:
                    t_dur = (time.perf_counter() - t_start) * 1000
                    logger.warning("Tool execution threw error | tool=%s err=%s", tool.name, exc)
                    tool_trace.append(
                        ToolCallRecord(
                            step_index=step_count,
                            tool_name=tool.name,
                            reason=decision.reason,
                            arguments=decision.arguments,
                            status="FAILED",
                            duration_ms=round(t_dur, 2),
                            output_summary=f"Tool error: {exc}",
                            error_message=str(exc),
                        )
                    )
                    execution_history.append(
                        {
                            "tool_name": tool.name,
                            "arguments": decision.arguments,
                            "reason": decision.reason,
                            "output_summary": f"Tool error: {exc}",
                        }
                    )

        # 6. SYNTHESIZE FINAL RESPONSE IF NOT REACHED
        if not final_answer_text:
            if step_count >= max_steps:
                stop_reason = StopReason.MAX_STEPS_REACHED

            if execution_history:
                summaries = [s["output_summary"] for s in execution_history]
                final_answer_text = (
                    "Operational Evidence Synthesis:\n\n"
                    + "\n\n".join(summaries[:3])
                    + "\n\nConclusion: Gathered operational facts support the observed capacity parameters above."
                )
            else:
                final_answer_text = (
                    f"Unable to investigate task '{request.task}'. No relevant operational tools could be executed."
                )
                stop_reason = StopReason.NO_RELEVANT_TOOLS

        # Deduplicate provenance items
        seen_prov: set[str] = set()
        deduped_prov: list[ProvenanceItem] = []
        for p in provenance_items:
            key = f"{p.category}:{p.id}"
            if key not in seen_prov:
                seen_prov.add(key)
                deduped_prov.append(p)

        # Ensure disclaimer in limitations
        if DISCLAIMER_TEXT not in final_limitations:
            final_limitations.append(DISCLAIMER_TEXT)

        duration_ms = (time.perf_counter() - start_time) * 1000

        status = AgentExecutionStatus.COMPLETED
        if stop_reason in (StopReason.OUT_OF_SCOPE, StopReason.NO_RELEVANT_TOOLS):
            status = AgentExecutionStatus.REJECTED
        elif stop_reason in (StopReason.TIMEOUT,):
            status = AgentExecutionStatus.TIMED_OUT
        elif stop_reason in (StopReason.MAX_STEPS_REACHED, StopReason.MAX_TOOL_CALLS_REACHED):
            status = AgentExecutionStatus.LIMIT_REACHED
        elif stop_reason in (StopReason.TOOL_FAILURE, StopReason.PROVIDER_UNAVAILABLE):
            status = AgentExecutionStatus.FAILED

        return AgentRunResponse(
            run_id=run_id,
            agent_id=agent_meta.agent_id,
            agent_name=agent_meta.name,
            status=status,
            final_answer=final_answer_text,
            sources=citations,
            provenance=deduped_prov,
            tool_trace=tool_trace,
            execution=AgentRunExecutionMetadata(
                steps_completed=step_count,
                tool_calls=tool_calls_count,
                duration_ms=round(duration_ms, 2),
                stop_reason=stop_reason,
                model=self.provider.model_name,
                provider=self.provider.provider_name,
            ),
            limitations=final_limitations,
            requires_human_review=True,
            created_at=utc_now(),
        )
