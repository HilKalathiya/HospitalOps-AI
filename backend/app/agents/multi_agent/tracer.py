"""
HospitalOps AI — Multi-Agent Execution Tracker & Audit Logging (Milestone 5, Chunk 5.6.3).

Provides parent-child execution traceability, lifecycle event capture, telemetry sanitization,
and optional persistence for MultiAgentExecutionTrace entities.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.agents.multi_agent.contracts import (
    AggregatedSpecialistResult,
    DelegationPlan,
    DelegationRequest,
    MultiAgentErrorCode,
    MultiAgentEventType,
    MultiAgentExecutionTrace,
    MultiAgentTraceEvent,
    SpecialistId,
    SpecialistResult,
)
from app.models.base import utc_now

if TYPE_CHECKING:
    from app.repositories.agent_traces import AgentTraceRepository

logger = logging.getLogger(__name__)

# Sensitive keys that must be scrubbed from trace event telemetry
SENSITIVE_KEY_SUBSTRINGS = (
    "password",
    "token",
    "secret",
    "api_key",
    "authorization",
    "credential",
    "cookie",
    "system_prompt",
    "chain_of_thought",
)


def _enum_val(v: Any) -> str:
    """Safely return enum value or string representation."""
    return v.value if hasattr(v, "value") else str(v)


def _sanitize_telemetry(data: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively sanitize event details to prevent leakage of credentials,
    hidden system prompts, or raw chain-of-thought tokens.
    """
    sanitized: dict[str, Any] = {}
    for key, value in data.items():
        lower_key = key.lower()
        if any(sens in lower_key for sens in SENSITIVE_KEY_SUBSTRINGS):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_telemetry(value)
        elif isinstance(value, list):
            sanitized[key] = [
                _sanitize_telemetry(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            sanitized[key] = value
    return sanitized


class MultiAgentExecutionTracker:
    """
    Manages in-memory lifecycle audit events and optional database persistence
    for multi-agent coordination traces.
    """

    def __init__(self, trace_repository: AgentTraceRepository | None = None) -> None:
        self._trace_repository = trace_repository
        self._current_trace: MultiAgentExecutionTrace | None = None

    @property
    def current_trace(self) -> MultiAgentExecutionTrace | None:
        """Return the active execution trace being tracked."""
        return self._current_trace

    def start_trace(
        self,
        parent_execution_id: str,
        user_id: str,
        plan: DelegationPlan,
    ) -> MultiAgentExecutionTrace:
        """
        Initialize a new multi-agent execution trace and record initial lifecycle events.
        """
        trace = MultiAgentExecutionTrace(
            parent_execution_id=parent_execution_id,
            user_id=user_id,
            plan=plan,
            events=[],
        )
        self._current_trace = trace

        # Record parent start event
        self.record_event(
            event_type=MultiAgentEventType.PARENT_EXECUTION_STARTED,
            details={
                "plan_id": plan.plan_id,
                "delegation_count": len(plan.delegations),
                "total_timeout_seconds": plan.total_timeout_seconds,
            },
        )

        # Record plan creation event
        self.record_event(
            event_type=MultiAgentEventType.DELEGATION_PLAN_CREATED,
            details={
                "plan_id": plan.plan_id,
                "specialist_ids": [
                    d.target_specialist_id.value
                    if hasattr(d.target_specialist_id, "value")
                    else str(d.target_specialist_id)
                    for d in plan.delegations
                ],
                "dependencies": plan.dependencies,
            },
        )

        logger.info(
            "Multi-agent trace started | trace_id=%s parent_id=%s delegations=%d",
            trace.trace_id,
            parent_execution_id,
            len(plan.delegations),
        )
        return trace

    def record_event(
        self,
        event_type: MultiAgentEventType,
        specialist_id: SpecialistId | None = None,
        delegation_id: str | None = None,
        duration_ms: float = 0.0,
        details: dict[str, Any] | None = None,
    ) -> MultiAgentTraceEvent:
        """
        Append a sanitized trace event to the active execution trace.
        """
        if self._current_trace is None:
            raise RuntimeError(
                "Cannot record multi-agent trace event: No active trace started."
            )

        sanitized_details = _sanitize_telemetry(details or {})

        event = MultiAgentTraceEvent(
            parent_execution_id=self._current_trace.parent_execution_id,
            delegation_id=delegation_id,
            specialist_id=specialist_id,
            event_type=event_type,
            duration_ms=max(0.0, float(duration_ms)),
            details=sanitized_details,
        )

        self._current_trace.events.append(event)
        return event

    def record_specialist_started(self, delegation: DelegationRequest) -> MultiAgentTraceEvent:
        """Record specialist execution kickoff."""
        return self.record_event(
            event_type=MultiAgentEventType.SPECIALIST_STARTED,
            specialist_id=delegation.target_specialist_id,
            delegation_id=delegation.delegation_id,
            details={
                "task_description": delegation.task_description[:300],
                "timeout_seconds": delegation.timeout_seconds,
                "max_evidence_items": delegation.max_evidence_items,
            },
        )

    def record_specialist_completed(self, result: SpecialistResult) -> MultiAgentTraceEvent:
        """Record successful specialist task completion."""
        return self.record_event(
            event_type=MultiAgentEventType.SPECIALIST_COMPLETED,
            specialist_id=result.specialist_id,
            delegation_id=result.delegation_id,
            duration_ms=result.duration_ms,
            details={
                "status": _enum_val(result.status),
                "tool_calls_count": result.tool_calls_count,
                "evidence_count": len(result.evidence),
                "citations_count": len(result.citations),
                "is_fallback": result.is_fallback,
            },
        )

    def record_specialist_failed(
        self,
        delegation_id: str,
        specialist_id: SpecialistId,
        error_code: MultiAgentErrorCode,
        error_message: str,
        duration_ms: float = 0.0,
    ) -> MultiAgentTraceEvent:
        """Record specialist failure event."""
        return self.record_event(
            event_type=MultiAgentEventType.SPECIALIST_FAILED,
            specialist_id=specialist_id,
            delegation_id=delegation_id,
            duration_ms=duration_ms,
            details={
                "error_code": _enum_val(error_code),
                "error_message": error_message,
            },
        )

    def record_specialist_timed_out(
        self,
        delegation_id: str,
        specialist_id: SpecialistId,
        duration_ms: float = 0.0,
    ) -> MultiAgentTraceEvent:
        """Record specialist timeout event."""
        return self.record_event(
            event_type=MultiAgentEventType.SPECIALIST_TIMED_OUT,
            specialist_id=specialist_id,
            delegation_id=delegation_id,
            duration_ms=duration_ms,
            details={
                "error_code": _enum_val(MultiAgentErrorCode.EXECUTION_TIMEOUT),
                "error_message": "Specialist execution exceeded assigned timeout budget",
            },
        )

    def record_specialist_cancelled(
        self,
        delegation_id: str,
        specialist_id: SpecialistId,
        duration_ms: float = 0.0,
    ) -> MultiAgentTraceEvent:
        """Record specialist cancellation event."""
        return self.record_event(
            event_type=MultiAgentEventType.SPECIALIST_CANCELLED,
            specialist_id=specialist_id,
            delegation_id=delegation_id,
            duration_ms=duration_ms,
            details={
                "error_message": "Specialist execution was cancelled by coordinator",
            },
        )

    def record_specialist_skipped(
        self,
        delegation_id: str,
        specialist_id: SpecialistId,
        reason: str,
    ) -> MultiAgentTraceEvent:
        """Record specialist skipped event due to unmet or failed dependency."""
        return self.record_event(
            event_type=MultiAgentEventType.SPECIALIST_SKIPPED,
            specialist_id=specialist_id,
            delegation_id=delegation_id,
            duration_ms=0.0,
            details={"reason": reason},
        )

    async def complete_trace(
        self,
        aggregated_result: AggregatedSpecialistResult,
    ) -> MultiAgentExecutionTrace:
        """
        Finalize the trace with the aggregated multi-agent outcome, record the completion
        event, compute total duration, and persist to repository if configured.
        """
        if self._current_trace is None:
            raise RuntimeError("Cannot complete trace: No active trace started.")

        now = utc_now()
        self._current_trace.aggregated_result = aggregated_result
        self._current_trace.completed_at = now
        self._current_trace.total_duration_ms = max(
            0.0,
            (now - self._current_trace.created_at).total_seconds() * 1000.0,
        )

        # Record aggregation completed event
        self.record_event(
            event_type=MultiAgentEventType.AGGREGATION_COMPLETED,
            duration_ms=aggregated_result.duration_ms,
            details={
                "status": (
                    aggregated_result.status.value
                    if hasattr(aggregated_result.status, "value")
                    else str(aggregated_result.status)
                ),
                "is_partial_result": aggregated_result.is_partial_result,
                "successful_contributors": [
                    s.value if hasattr(s, "value") else str(s)
                    for s in aggregated_result.successful_contributors
                ],
                "unsuccessful_contributors": [
                    s.value if hasattr(s, "value") else str(s)
                    for s in aggregated_result.unsuccessful_contributors
                ],
                "conflicts_count": len(aggregated_result.conflicts_or_inconsistencies),
                "total_evidence_items": len(aggregated_result.aggregated_evidence),
            },
        )

        if self._trace_repository:
            try:
                await self._trace_repository.save_trace(self._current_trace)
                logger.info(
                    "Persisted multi-agent execution trace | trace_id=%s parent_id=%s",
                    self._current_trace.trace_id,
                    self._current_trace.parent_execution_id,
                )
            except Exception as exc:
                logger.error(
                    "Failed to persist multi-agent execution trace | trace_id=%s error=%s",
                    self._current_trace.trace_id,
                    exc,
                )

        return self._current_trace
