"""
HospitalOps AI — Agent Orchestrator (Milestone 5, Chunk 5.3).

Implements the centralized execution lifecycle:
PENDING -> UNDERSTANDING -> PLANNING -> TOOL_SELECTION ->
TOOL_EXECUTION -> EVIDENCE_REVIEW -> RESPONSE_GENERATION -> COMPLETED

Coordinates:
- OrchestrationStateTracker (explicit transitions & audit trail)
- AgentPlanner (structured task plan & step decisions)
- ToolExecutionCoordinator (permission checks, validation, execution)
- AgentEvidenceCollector (typed, bounded operational evidence)
- AgentResponseGenerator (grounded synthesis & citation verification)
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections import OrderedDict
from typing import TYPE_CHECKING, Any

from app.agents.contracts import (
    AgentExecutionStatus,
    AgentExecutionTrace,
    AgentRunExecutionMetadata,
    AgentRunRequest,
    AgentRunResponse,
    ProvenanceItem,
    StopReason,
    ToolCallRecord,
    ToolErrorCode,
)
from app.agents.evidence import AgentEvidenceCollector
from app.agents.lifecycle import OrchestrationState, OrchestrationStateTracker
from app.agents.multi_agent.aggregator import MultiAgentAggregator
from app.agents.multi_agent.contracts import (
    AggregationStatus,
    SpecialistExecutionStatus,
)
from app.agents.multi_agent.coordinator import MultiAgentCoordinator
from app.agents.multi_agent.registry import SpecialistRegistry
from app.agents.multi_agent.specialists import (
    ForecastingSpecialist,
    KnowledgeSpecialist,
    OptimizationSpecialist,
    SimulationSpecialist,
)
from app.agents.multi_agent.tracer import MultiAgentExecutionTracker
from app.agents.planner import AgentPlanner
from app.agents.policies import DISCLAIMER_TEXT, AgentPolicyEnforcer
from app.agents.registry import AgentRegistry, ToolRegistry
from app.agents.response_generator import AgentResponseGenerator
from app.agents.tool_coordinator import ToolExecutionCoordinator
from app.agents.tools.base import ToolContext
from app.core.security import get_permissions_for_role
from app.knowledge.generation.contracts import CitationReference
from app.knowledge.generation.provider import LLMProvider
from app.models.base import utc_now
from app.models.user import UserDocument

if TYPE_CHECKING:
    from app.repositories.agent_traces import AgentTraceRepository

logger = logging.getLogger(__name__)


def _enum_str(val: Any) -> str:
    """Safely return string representation of enum or str."""
    return val.value if hasattr(val, "value") else str(val)


def _map_multi_agent_error_code(code: Any) -> ToolErrorCode | None:
    """Map MultiAgentErrorCode to corresponding standardized ToolErrorCode."""
    if not code:
        return None
    val = code.value if hasattr(code, "value") else str(code)
    mapping = {
        "EXECUTION_TIMEOUT": ToolErrorCode.EXECUTION_TIMEOUT,
        "PERMISSION_DENIED": ToolErrorCode.PERMISSION_DENIED,
        "SPECIALIST_NOT_FOUND": ToolErrorCode.UNKNOWN_TOOL,
        "SPECIALIST_DISABLED": ToolErrorCode.TOOL_DISABLED,
        "POLICY_VIOLATION": ToolErrorCode.APPROVAL_REQUIRED,
    }
    return mapping.get(val, ToolErrorCode.EXECUTION_FAILED)

# Bounded in-memory store for recent execution traces (last 100 runs)
_MAX_STORED_TRACES = 100
_TRACE_STORE: OrderedDict[str, AgentExecutionTrace] = OrderedDict()


def store_execution_trace(trace: AgentExecutionTrace) -> None:
    """Store trace in bounded FIFO cache for administrative inspection."""
    if len(_TRACE_STORE) >= _MAX_STORED_TRACES:
        _TRACE_STORE.popitem(last=False)
    _TRACE_STORE[trace.execution_id] = trace


def get_stored_trace(execution_id: str) -> AgentExecutionTrace | None:
    """Retrieve execution trace by ID."""
    return _TRACE_STORE.get(execution_id)


class AgentOrchestrator:
    """
    Centralized orchestration engine for HospitalOps AI agents.
    Enforces bounded lifecycles, explicit state transitions,
    safe sequential tool coordination, and grounded evidence synthesis.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        agent_registry: AgentRegistry,
        provider: LLMProvider,
        specialist_registry: SpecialistRegistry | None = None,
        multi_agent_coordinator: MultiAgentCoordinator | None = None,
        trace_repository: AgentTraceRepository | None = None,
        enable_multi_agent: bool | None = None,
    ) -> None:
        self.tool_registry = tool_registry
        self.agent_registry = agent_registry
        self.provider = provider
        self.planner = AgentPlanner(provider=provider, tools=tool_registry.list_all())
        self.coordinator = ToolExecutionCoordinator(registry=tool_registry)
        self.response_generator = AgentResponseGenerator(provider=provider)
        self.trace_repository = trace_repository

        # Multi-agent coordination setup (Chunk 5.6.4)
        if enable_multi_agent is not None:
            self.enable_multi_agent = enable_multi_agent
        else:
            self.enable_multi_agent = (
                specialist_registry is not None or multi_agent_coordinator is not None
            )

        if specialist_registry is not None:
            self.specialist_registry: SpecialistRegistry | None = specialist_registry
        elif self.enable_multi_agent:
            self.specialist_registry = self._build_default_specialist_registry(tool_registry)
        else:
            self.specialist_registry = None

        if multi_agent_coordinator is not None:
            self.multi_agent_coordinator: MultiAgentCoordinator | None = multi_agent_coordinator
        elif self.specialist_registry is not None and self.specialist_registry.registered_count() > 0:
            tracker = MultiAgentExecutionTracker(trace_repository=trace_repository)
            self.multi_agent_coordinator = MultiAgentCoordinator(
                registry=self.specialist_registry,
                tracker=tracker,
                aggregator=MultiAgentAggregator(),
            )
        else:
            self.multi_agent_coordinator = None

    def _build_default_specialist_registry(
        self, tool_registry: ToolRegistry
    ) -> SpecialistRegistry:
        """Instantiate available domain specialists from registered tools."""
        registry = SpecialistRegistry()

        forecast_tool = tool_registry.get("get_existing_forecast")
        if forecast_tool:
            try:
                registry.register(ForecastingSpecialist(tool=forecast_tool))  # type: ignore[arg-type]
            except Exception as exc:
                logger.debug("Could not register default ForecastingSpecialist: %s", exc)

        sim_tool = tool_registry.get("get_simulation_result")
        if sim_tool:
            try:
                registry.register(SimulationSpecialist(tool=sim_tool))  # type: ignore[arg-type]
            except Exception as exc:
                logger.debug("Could not register default SimulationSpecialist: %s", exc)

        opt_tool = tool_registry.get("get_optimization_explanation")
        if opt_tool:
            try:
                registry.register(OptimizationSpecialist(tool=opt_tool))  # type: ignore[arg-type]
            except Exception as exc:
                logger.debug("Could not register default OptimizationSpecialist: %s", exc)

        knowledge_tool = tool_registry.get("search_hospital_knowledge")
        if knowledge_tool:
            try:
                registry.register(KnowledgeSpecialist(tool=knowledge_tool))  # type: ignore[arg-type]
            except Exception as exc:
                logger.debug("Could not register default KnowledgeSpecialist: %s", exc)

        return registry

    async def execute(
        self,
        request: AgentRunRequest,
        current_user: UserDocument,
    ) -> AgentRunResponse:
        """
        Execute an end-to-end agent inquiry through the formal orchestration lifecycle.
        """
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        start_time = time.perf_counter()
        tracker = OrchestrationStateTracker(initial_state=OrchestrationState.PENDING)
        evidence_collector = AgentEvidenceCollector()

        tool_trace: list[ToolCallRecord] = []
        provenance_items: list[ProvenanceItem] = []
        citations: list[CitationReference] = []
        call_history: list[tuple[str, str]] = []
        execution_history: list[dict[str, Any]] = []

        logger.info(
            "Agent orchestration initiated | run_id=%s agent_id=%s user_id=%s query_len=%d",
            run_id,
            request.agent_id,
            current_user.user_id,
            len(request.task),
        )

        # 1. VALIDATION & AGENT LOOKUP
        agent_meta = self.agent_registry.get(request.agent_id)
        if not agent_meta:
            tracker.transition_to(
                OrchestrationState.REJECTED,
                reason=f"Agent '{request.agent_id}' is not registered in system allowlist.",
            )
            duration_ms = (time.perf_counter() - start_time) * 1000
            return self._build_rejected_response(
                run_id=run_id,
                agent_id=request.agent_id,
                agent_name="Unknown Agent",
                message=f"Agent '{request.agent_id}' is not registered in the system.",
                stop_reason=StopReason.NO_RELEVANT_TOOLS,
                duration_ms=duration_ms,
                tracker=tracker,
                current_user=current_user,
                session_id=request.session_id,
            )

        # 2. CLAMP EXECUTION BOUNDS SERVER-SIDE
        opts = request.options
        max_steps = min(10, max(1, opts.max_steps))
        max_tool_calls = min(8, max(1, opts.max_tool_calls))
        timeout_seconds = min(60.0, max(5.0, opts.timeout_seconds))

        # 3. CLINICAL SAFETY GUARD
        is_clinical, refusal_reason = AgentPolicyEnforcer.check_clinical_scope(request.task)
        if is_clinical:
            tracker.transition_to(
                OrchestrationState.REJECTED,
                reason="Query violated non-clinical safety boundary.",
            )
            duration_ms = (time.perf_counter() - start_time) * 1000
            refusal_text = (
                f"Out of Scope Advisory: {refusal_reason}\n\n"
                "HospitalOps AI is an operational decision intelligence platform. "
                "For clinical emergencies, patient diagnoses, or treatment prescriptions, "
                "please consult the attending physician or hospital clinical team directly."
            )
            return self._build_rejected_response(
                run_id=run_id,
                agent_id=agent_meta.agent_id,
                agent_name=agent_meta.name,
                message=refusal_text,
                stop_reason=StopReason.OUT_OF_SCOPE,
                duration_ms=duration_ms,
                tracker=tracker,
                current_user=current_user,
                limitations=[
                    "Clinical queries are prohibited under the HospitalOps AI constitution.",
                    DISCLAIMER_TEXT,
                ],
                session_id=request.session_id,
            )

        # 4. RESOLVE USER PERMISSIONS & CONTEXT
        user_permissions = get_permissions_for_role(current_user.role)
        tool_context = ToolContext(
            user=current_user,
            permissions=user_permissions,
            department_id=current_user.department_id,
            run_id=run_id,
        )

        # 5. STATE: UNDERSTANDING (Formulate Task Plan)
        tracker.transition_to(
            OrchestrationState.UNDERSTANDING, reason="Formulating initial operational task plan."
        )
        eligible_tools = self.coordinator.get_eligible_tools(user_permissions)
        task_plan = await self.planner.understand_and_plan(
            task=request.task,
            available_tools=eligible_tools,
            conversation_context=request.conversation_context,
        )

        # Check if tools are required or if query is unsupported
        if not task_plan.requires_tools:
            if task_plan.task_type == "UNSUPPORTED":
                tracker.transition_to(
                    OrchestrationState.REJECTED,
                    reason="Inquiry unsupported by operational tool catalog.",
                )
                duration_ms = (time.perf_counter() - start_time) * 1000
                return self._build_rejected_response(
                    run_id=run_id,
                    agent_id=agent_meta.agent_id,
                    agent_name=agent_meta.name,
                    message=(
                        f"The requested task '{request.task}' is outside the operational capabilities of HospitalOps AI. "
                        "Please specify an operational inquiry involving bed occupancy, forecasts, what-if simulations, "
                        "resource optimizations, or hospital standard operating procedures."
                    ),
                    stop_reason=StopReason.NO_RELEVANT_TOOLS,
                    duration_ms=duration_ms,
                    tracker=tracker,
                    current_user=current_user,
                    task_plan=task_plan,
                    session_id=request.session_id,
                )

            # Direct no-tool answer path
            tracker.transition_to(
                OrchestrationState.RESPONSE_GENERATION,
                reason="Task does not require tool invocations; generating direct response.",
            )
            direct_result = await self.response_generator.generate_response(
                task=request.task,
                task_plan=task_plan,
                evidence_collector=evidence_collector,
                citations=[],
                conversation_context=request.conversation_context,
            )
            tracker.transition_to(
                OrchestrationState.COMPLETED, reason="Direct inquiry completed successfully."
            )
            duration_ms = (time.perf_counter() - start_time) * 1000
            return self._build_completed_response(
                run_id=run_id,
                agent_meta=agent_meta,
                final_answer=direct_result.answer,
                citations=[],
                provenance_items=[],
                evidence_collector=evidence_collector,
                tool_trace=[],
                tracker=tracker,
                task_plan=task_plan,
                stop_reason=StopReason.FINAL_ANSWER_READY,
                duration_ms=duration_ms,
                steps_count=1,
                tool_calls_count=0,
                limitations=direct_result.limitations,
                current_user=current_user,
                session_id=request.session_id,
            )

        # 6. EVALUATE MULTI-AGENT SPECIALIST DELEGATION (Chunk 5.6.4)
        eval_multi_agent = False
        if request.options.enable_delegation is False:
            eval_multi_agent = False
        elif request.options.enable_delegation is True:
            eval_multi_agent = True
            if self.specialist_registry is None:
                self.specialist_registry = self._build_default_specialist_registry(self.tool_registry)
            if self.multi_agent_coordinator is None and self.specialist_registry.registered_count() > 0:
                tracker = MultiAgentExecutionTracker(trace_repository=self.trace_repository)
                self.multi_agent_coordinator = MultiAgentCoordinator(
                    registry=self.specialist_registry,
                    tracker=tracker,
                    aggregator=MultiAgentAggregator(),
                )
        else:
            eval_multi_agent = self.enable_multi_agent and (self.multi_agent_coordinator is not None)

        if eval_multi_agent and self.multi_agent_coordinator is not None:
            available_spec_ids = (
                [
                    s.specialist_id
                    for s in self.specialist_registry.list_specialists(include_disabled=False)
                ]
                if self.specialist_registry
                else []
            )
            delegation_decision = self.planner.plan_delegation(
                task=request.task,
                task_plan=task_plan,
                available_specialists=available_spec_ids,
                user_permissions=user_permissions,
                parent_execution_id=run_id,
                conversation_context=request.conversation_context,
            )

            if (
                delegation_decision.should_delegate
                and delegation_decision.delegation_plan is not None
            ):
                plan = delegation_decision.delegation_plan
                logger.info(
                    "Executing multi-agent delegation | run_id=%s mode=%s specialists=%s",
                    run_id,
                    delegation_decision.delegation_mode,
                    [_enum_str(s) for s in delegation_decision.selected_specialists],
                )
                tracker.transition_to(
                    OrchestrationState.PLANNING,
                    reason="Formulated multi-agent specialist delegation plan.",
                    metadata={
                        "mode": delegation_decision.delegation_mode,
                        "specialists": [
                            _enum_str(s) for s in delegation_decision.selected_specialists
                        ],
                    },
                )
                tracker.transition_to(
                    OrchestrationState.TOOL_SELECTION,
                    reason=f"Selected {len(delegation_decision.selected_specialists)} domain specialists for delegation.",
                    metadata={
                        "specialists": [
                            _enum_str(s) for s in delegation_decision.selected_specialists
                        ]
                    },
                )
                tracker.transition_to(
                    OrchestrationState.TOOL_EXECUTION,
                    reason="Dispatching delegation plan to MultiAgentCoordinator.",
                )

                try:
                    agg_result = await self.multi_agent_coordinator.coordinate(
                        plan=plan,
                        context=tool_context,
                        timeout_override=timeout_seconds,
                    )
                except asyncio.CancelledError:
                    logger.warning("Multi-agent coordination cancelled by caller | run_id=%s", run_id)
                    tracker.transition_to(
                        OrchestrationState.CANCELLED, reason="Execution cancelled by caller."
                    )
                    raise
                except Exception as exc:
                    logger.error(
                        "Multi-agent coordinator failure | run_id=%s error=%s", run_id, exc
                    )
                    tracker.transition_to(
                        OrchestrationState.FAILED,
                        reason=f"Multi-agent coordinator error: {exc}",
                    )
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    return self._build_completed_response(
                        run_id=run_id,
                        agent_meta=agent_meta,
                        final_answer=f"Multi-agent coordination failed: {exc}",
                        citations=[],
                        provenance_items=[],
                        evidence_collector=evidence_collector,
                        tool_trace=[],
                        tracker=tracker,
                        task_plan=task_plan,
                        stop_reason=StopReason.PROVIDER_UNAVAILABLE,
                        duration_ms=duration_ms,
                        steps_count=1,
                        tool_calls_count=0,
                        limitations=[
                            "Multi-agent coordinator encountered an internal error.",
                            DISCLAIMER_TEXT,
                        ],
                        current_user=current_user,
                        session_id=request.session_id,
                    )

                # Ingest evidence into collector
                for ev in agg_result.aggregated_evidence:
                    evidence_collector.add_existing_evidence(ev)
                provenance_items.extend(agg_result.all_provenance)
                citations.extend(agg_result.all_citations)

                for res in agg_result.specialist_results:
                    task_desc = next(
                        (
                            d.task_description
                            for d in plan.delegations
                            if d.delegation_id == res.delegation_id
                        ),
                        "",
                    )
                    tool_trace.append(
                        ToolCallRecord(
                            call_id=res.delegation_id,
                            tool_name=(
                                res.specialist_id.value
                                if hasattr(res.specialist_id, "value")
                                else str(res.specialist_id)
                            ),
                            step_index=len(tool_trace) + 1,
                            arguments={"task_description": task_desc},
                            status=(
                                "SUCCESS"
                                if res.status == SpecialistExecutionStatus.COMPLETED
                                else "FAILED"
                            ),
                            duration_ms=res.duration_ms,
                            output_summary=res.summary,
                            error_message=res.error_message,
                            error_code=_map_multi_agent_error_code(res.error_code),
                            provenance_ids=[p.id for p in res.provenance],
                        )
                    )

                tracker.transition_to(
                    OrchestrationState.EVIDENCE_REVIEW,
                    reason="Reviewed aggregated multi-agent evidence.",
                    metadata={
                        "status": (
                            agg_result.status.value
                            if hasattr(agg_result.status, "value")
                            else str(agg_result.status)
                        ),
                        "successful": [
                            _enum_str(s)
                            for s in agg_result.successful_contributors
                        ],
                        "unsuccessful": [
                            _enum_str(s)
                            for s in agg_result.unsuccessful_contributors
                        ],
                    },
                )

                # State: RESPONSE_GENERATION
                tracker.transition_to(
                    OrchestrationState.RESPONSE_GENERATION,
                    reason="Synthesizing final response from aggregated specialist evidence.",
                    metadata={
                        "evidence_count": evidence_collector.count,
                        "is_partial": agg_result.is_partial_result,
                    },
                )

                is_partial = agg_result.is_partial_result
                unsuccessful_names = [
                    _enum_str(s)
                    for s in agg_result.unsuccessful_contributors
                ]
                stop_notes = (
                    f"Specialists failed or timed out: {unsuccessful_names}"
                    if is_partial
                    else None
                )

                synth_result = await self.response_generator.generate_response(
                    task=request.task,
                    task_plan=task_plan,
                    evidence_collector=evidence_collector,
                    citations=citations,
                    is_partial=is_partial,
                    stop_reason_notes=stop_notes,
                    conversation_context=request.conversation_context,
                    conflicts=agg_result.conflicts_or_inconsistencies,
                )

                # Resolve stop reason and state
                if agg_result.status == AggregationStatus.FAILED:
                    stop_reason = StopReason.TOOL_FAILURE
                    final_state = OrchestrationState.FAILED
                elif is_partial:
                    stop_reason = StopReason.SUFFICIENT_EVIDENCE
                    final_state = OrchestrationState.COMPLETED
                elif not synth_result.evidence_sufficient:
                    stop_reason = StopReason.SUFFICIENT_EVIDENCE
                    final_state = OrchestrationState.INSUFFICIENT_EVIDENCE
                else:
                    stop_reason = StopReason.FINAL_ANSWER_READY
                    final_state = OrchestrationState.COMPLETED

                tracker.transition_to(
                    final_state,
                    reason=(
                        f"Multi-agent coordination finished with status "
                        f"{agg_result.status.value if hasattr(agg_result.status, 'value') else str(agg_result.status)}."
                    ),
                )
                duration_ms = (time.perf_counter() - start_time) * 1000

                return self._build_completed_response(
                    run_id=run_id,
                    agent_meta=agent_meta,
                    final_answer=synth_result.answer,
                    citations=synth_result.citations,
                    provenance_items=provenance_items,
                    evidence_collector=evidence_collector,
                    tool_trace=tool_trace,
                    tracker=tracker,
                    task_plan=task_plan,
                    stop_reason=stop_reason,
                    duration_ms=duration_ms,
                    steps_count=len(plan.delegations),
                    tool_calls_count=sum(
                        r.tool_calls_count for r in agg_result.specialist_results
                    ),
                    limitations=synth_result.limitations,
                    current_user=current_user,
                    session_id=request.session_id,
                    multi_agent_trace=self.multi_agent_coordinator.tracker.current_trace,
                    aggregated_result=agg_result,
                )

        # 7. SEQUENTIAL ORCHESTRATION LOOP
        step_count = 0
        tool_calls_count = 0
        stop_reason = StopReason.SUFFICIENT_EVIDENCE
        final_answer_text = ""
        final_limitations: list[str] = []
        is_partial = False

        tracker.transition_to(
            OrchestrationState.PLANNING, reason="Entering multi-step investigation loop."
        )

        while step_count < max_steps:
            elapsed = time.perf_counter() - start_time
            if elapsed >= timeout_seconds:
                logger.warning(
                    "Orchestration timeout exceeded | run_id=%s elapsed=%.1fs", run_id, elapsed
                )
                stop_reason = StopReason.TIMEOUT
                is_partial = True
                break

            step_count += 1

            # Decide next action
            try:
                decision = await self.planner.plan_next_action(
                    task=request.task,
                    execution_history=execution_history,
                    step_index=step_count,
                    task_plan=task_plan,
                    evidence_collector=evidence_collector,
                )
            except Exception as exc:
                logger.error("Planner failure | run_id=%s step=%d err=%s", run_id, step_count, exc)
                stop_reason = StopReason.PROVIDER_UNAVAILABLE
                final_answer_text = (
                    f"Agent reasoning interrupted by unexpected planner error: {exc}"
                )
                is_partial = True
                break

            # Handle Action: FINAL_ANSWER
            if decision.decision == "FINAL_ANSWER":
                final_answer_text = decision.answer
                final_limitations.extend(decision.limitations)
                stop_reason = StopReason.FINAL_ANSWER_READY
                break

            # Handle Action: CALL_TOOL
            if decision.decision == "CALL_TOOL":
                tool_name = decision.tool_name or ""

                if tool_calls_count >= max_tool_calls:
                    logger.info(
                        "Maximum tool-call ceiling reached | run_id=%s limit=%d",
                        run_id,
                        max_tool_calls,
                    )
                    stop_reason = StopReason.MAX_TOOL_CALLS_REACHED
                    is_partial = True
                    break

                # State: TOOL_SELECTION
                tracker.transition_to(
                    OrchestrationState.TOOL_SELECTION,
                    reason=f"Selected tool '{tool_name}' for step {step_count}.",
                    metadata={"tool_name": tool_name, "step": step_count},
                )

                # State: TOOL_EXECUTION
                tracker.transition_to(
                    OrchestrationState.TOOL_EXECUTION,
                    reason=f"Executing tool '{tool_name}'.",
                )
                tool_calls_count += 1

                coord_result = await self.coordinator.execute_tool(
                    tool_name=tool_name,
                    arguments=decision.arguments,
                    reason=decision.reason,
                    step_index=step_count,
                    tool_context=tool_context,
                    evidence_collector=evidence_collector,
                    call_history=call_history,
                )

                tool_trace.append(coord_result.record)
                provenance_items.extend(coord_result.provenance_items)
                citations.extend(coord_result.citations)

                # State: EVIDENCE_REVIEW
                tracker.transition_to(
                    OrchestrationState.EVIDENCE_REVIEW,
                    reason=f"Evaluated output for tool '{tool_name}'.",
                    metadata={"status": coord_result.status},
                )

                execution_history.append(
                    {
                        "tool_name": tool_name,
                        "arguments": decision.arguments,
                        "reason": decision.reason,
                        "output_summary": coord_result.record.output_summary,
                    }
                )

                if coord_result.is_terminal_failure:
                    logger.warning(
                        "Tool execution triggered terminal loop stop | tool=%s", tool_name
                    )
                    stop_reason = StopReason.MAX_TOOL_CALLS_REACHED
                    is_partial = True
                    break

                # If another tool might be needed and within budget, transition back to PLANNING
                if step_count < max_steps and (time.perf_counter() - start_time) < timeout_seconds:
                    tracker.transition_to(
                        OrchestrationState.PLANNING,
                        reason="Planning subsequent investigation step.",
                    )

        # 7. STATE: RESPONSE_GENERATION
        tracker.transition_to(
            OrchestrationState.RESPONSE_GENERATION,
            reason="Synthesizing final evidence-grounded response.",
            metadata={"evidence_count": evidence_collector.count, "is_partial": is_partial},
        )

        synth_result = await self.response_generator.generate_response(
            task=request.task,
            task_plan=task_plan,
            evidence_collector=evidence_collector,
            citations=citations,
            is_partial=is_partial,
            stop_reason_notes=stop_reason.value if is_partial else None,
            conversation_context=request.conversation_context,
        )

        final_response_text = final_answer_text or synth_result.answer
        for lim in synth_result.limitations:
            if lim not in final_limitations:
                final_limitations.append(lim)

        # 8. RESOLVE FINAL LIFECYCLE STATE
        duration_ms = (time.perf_counter() - start_time) * 1000

        if stop_reason == StopReason.TIMEOUT:
            tracker.transition_to(
                OrchestrationState.TIMED_OUT, reason="Orchestration exceeded execution timeout."
            )
        elif stop_reason in (StopReason.MAX_STEPS_REACHED, StopReason.MAX_TOOL_CALLS_REACHED):
            tracker.transition_to(
                OrchestrationState.MAX_STEPS_REACHED, reason="Orchestration step limit reached."
            )
        elif not synth_result.evidence_sufficient:
            tracker.transition_to(
                OrchestrationState.INSUFFICIENT_EVIDENCE,
                reason="Gathered operational evidence was insufficient.",
            )
        elif stop_reason in (StopReason.TOOL_FAILURE, StopReason.PROVIDER_UNAVAILABLE):
            tracker.transition_to(
                OrchestrationState.FAILED, reason="Subsystem or planner error encountered."
            )
        else:
            tracker.transition_to(
                OrchestrationState.COMPLETED, reason="Investigation completed successfully."
            )

        return self._build_completed_response(
            run_id=run_id,
            agent_meta=agent_meta,
            final_answer=final_response_text,
            citations=synth_result.citations,
            provenance_items=provenance_items,
            evidence_collector=evidence_collector,
            tool_trace=tool_trace,
            tracker=tracker,
            task_plan=task_plan,
            stop_reason=stop_reason,
            duration_ms=duration_ms,
            steps_count=step_count,
            tool_calls_count=tool_calls_count,
            limitations=final_limitations,
            current_user=current_user,
            session_id=request.session_id,
        )

    def _build_completed_response(
        self,
        run_id: str,
        agent_meta: Any,
        final_answer: str,
        citations: list[CitationReference],
        provenance_items: list[ProvenanceItem],
        evidence_collector: AgentEvidenceCollector,
        tool_trace: list[ToolCallRecord],
        tracker: OrchestrationStateTracker,
        task_plan: Any,
        stop_reason: StopReason,
        duration_ms: float,
        steps_count: int,
        tool_calls_count: int,
        limitations: list[str],
        current_user: UserDocument,
        session_id: str | None = None,
        multi_agent_trace: Any | None = None,
        aggregated_result: Any | None = None,
    ) -> AgentRunResponse:
        # Deduplicate provenance
        seen_prov: set[str] = set()
        deduped_prov: list[ProvenanceItem] = []
        for p in provenance_items:
            key = f"{p.category}:{p.id}"
            if key not in seen_prov:
                seen_prov.add(key)
                deduped_prov.append(p)

        # Deduplicate citations
        seen_cits: set[str] = set()
        deduped_cits: list[CitationReference] = []
        for c in citations:
            key = f"{c.document_id}_{c.chunk_id}"
            if key not in seen_cits:
                seen_cits.add(key)
                deduped_cits.append(c)

        # Map tracker state to AgentExecutionStatus
        status_map = {
            OrchestrationState.COMPLETED: AgentExecutionStatus.COMPLETED,
            OrchestrationState.TIMED_OUT: AgentExecutionStatus.TIMED_OUT,
            OrchestrationState.MAX_STEPS_REACHED: AgentExecutionStatus.LIMIT_REACHED,
            OrchestrationState.INSUFFICIENT_EVIDENCE: AgentExecutionStatus.COMPLETED,
            OrchestrationState.REJECTED: AgentExecutionStatus.REJECTED,
            OrchestrationState.FAILED: AgentExecutionStatus.FAILED,
            OrchestrationState.CANCELLED: AgentExecutionStatus.CANCELLED,
        }
        exec_status = status_map.get(tracker.current_state, AgentExecutionStatus.COMPLETED)

        response = AgentRunResponse(
            run_id=run_id,
            session_id=session_id,
            agent_id=agent_meta.agent_id,
            agent_name=agent_meta.name,
            status=exec_status,
            final_answer=final_answer,
            task_plan=task_plan,
            sources=deduped_cits,
            provenance=deduped_prov,
            evidence=evidence_collector.items,
            tool_trace=tool_trace,
            state_transitions=tracker.history,
            execution=AgentRunExecutionMetadata(
                steps_completed=steps_count,
                tool_calls=tool_calls_count,
                duration_ms=round(duration_ms, 2),
                stop_reason=stop_reason,
                model=self.provider.model_name,
                provider=self.provider.provider_name,
            ),
            limitations=limitations,
            requires_human_review=True,
            multi_agent_trace=multi_agent_trace,
            aggregated_result=aggregated_result,
            created_at=utc_now(),
        )

        # Store trace for administrative inspection
        trace = AgentExecutionTrace(
            execution_id=run_id,
            agent_id=agent_meta.agent_id,
            user_id=current_user.user_id,
            start_time=utc_now(),
            duration_ms=round(duration_ms, 2),
            initial_state=OrchestrationState.PENDING,
            final_state=tracker.current_state,
            state_transitions=tracker.history,
            task_plan=task_plan,
            tool_calls=tool_trace,
            evidence_ids=[ev.evidence_id for ev in evidence_collector.items],
            multi_agent_trace_id=multi_agent_trace.trace_id if hasattr(multi_agent_trace, "trace_id") else None,
            stop_reason=stop_reason,
            status=exec_status,
        )
        store_execution_trace(trace)

        return response

    def _build_rejected_response(
        self,
        run_id: str,
        agent_id: str,
        agent_name: str,
        message: str,
        stop_reason: StopReason,
        duration_ms: float,
        tracker: OrchestrationStateTracker,
        current_user: UserDocument,
        task_plan: Any = None,
        limitations: list[str] | None = None,
        session_id: str | None = None,
    ) -> AgentRunResponse:
        default_limits = limitations or [DISCLAIMER_TEXT]
        response = AgentRunResponse(
            run_id=run_id,
            session_id=session_id,
            agent_id=agent_id,
            agent_name=agent_name,
            status=AgentExecutionStatus.REJECTED,
            final_answer=message,
            task_plan=task_plan,
            sources=[],
            provenance=[],
            evidence=[],
            tool_trace=[],
            state_transitions=tracker.history,
            execution=AgentRunExecutionMetadata(
                steps_completed=0,
                tool_calls=0,
                duration_ms=round(duration_ms, 2),
                stop_reason=stop_reason,
                model=self.provider.model_name,
                provider=self.provider.provider_name,
            ),
            limitations=default_limits,
            requires_human_review=False,
            created_at=utc_now(),
        )

        trace = AgentExecutionTrace(
            execution_id=run_id,
            agent_id=agent_id,
            user_id=current_user.user_id,
            start_time=utc_now(),
            duration_ms=round(duration_ms, 2),
            initial_state=OrchestrationState.PENDING,
            final_state=tracker.current_state,
            state_transitions=tracker.history,
            task_plan=task_plan,
            tool_calls=[],
            evidence_ids=[],
            stop_reason=stop_reason,
            status=AgentExecutionStatus.REJECTED,
        )
        store_execution_trace(trace)

        return response
