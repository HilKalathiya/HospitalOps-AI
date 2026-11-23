"""
HospitalOps AI — Bounded Multi-Agent Coordinator (Milestone 5, Chunk 5.6.3).

Coordinates the execution of bounded specialist delegations formulated by the
Hospital Operations Analyst Agent (supervisor). Enforces:
- Strict maximum recursion depth of 1 (no recursive specialist spawning)
- Maximum 4 specialists per execution
- Bounded concurrency via asyncio semaphores
- Prerequisite dependency resolution and failure short-circuiting
- Comprehensive timeout enforcement and cancellation handling
- Full audit event telemetry via MultiAgentExecutionTracker
- Evidence aggregation and conflict analysis via MultiAgentAggregator
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from app.agents.evidence import EvidenceCategory
from app.agents.multi_agent.aggregator import (
    SPECIALIST_EPISTEMIC_MAP,
    MultiAgentAggregator,
)
from app.agents.multi_agent.contracts import (
    AggregatedSpecialistResult,
    DelegationPlan,
    DelegationRequest,
    MultiAgentErrorCode,
    SpecialistExecutionStatus,
    SpecialistResult,
)
from app.agents.multi_agent.registry import SpecialistRegistry
from app.agents.multi_agent.tracer import MultiAgentExecutionTracker, _sanitize_value
from app.agents.tools.base import ToolContext

logger = logging.getLogger(__name__)


def _enum_val(v: Any) -> str:
    """Safely return enum value or string representation."""
    return v.value if hasattr(v, "value") else str(v)


def _validate_dependency_graph(
    dependencies: dict[str, list[str]],
    delegation_ids: set[str],
) -> None:
    """
    Validate that dependencies form a valid Directed Acyclic Graph (DAG) with known nodes.
    Rejects self-dependencies, unknown delegation references, and dependency cycles.
    """
    for dep_id, prereqs in dependencies.items():
        if dep_id not in delegation_ids:
            raise ValueError(f"Dependency references unknown delegation ID '{dep_id}'.")
        for prereq in prereqs:
            if prereq not in delegation_ids:
                raise ValueError(
                    f"Prerequisite '{prereq}' for delegation '{dep_id}' is not in plan."
                )
            if prereq == dep_id:
                raise ValueError(f"Delegation '{dep_id}' cannot declare a dependency on itself.")

    visited: dict[str, int] = {node: 0 for node in delegation_ids}

    def _has_cycle(u: str) -> bool:
        visited[u] = 1
        for v in dependencies.get(u, []):
            if visited.get(v, 0) == 1:
                return True
            if visited.get(v, 0) == 0 and _has_cycle(v):
                return True
        visited[u] = 2
        return False

    for node in delegation_ids:
        if visited[node] == 0 and _has_cycle(node):
            raise ValueError(
                f"Cyclic dependency detected in delegation plan dependencies: {dependencies}."
            )


class MultiAgentCoordinator:
    """
    Supervisor coordination engine executing domain specialist tasks.
    """

    def __init__(
        self,
        registry: SpecialistRegistry,
        aggregator: MultiAgentAggregator | None = None,
        tracker: MultiAgentExecutionTracker | None = None,
        max_concurrency: int = 4,
    ) -> None:
        self.registry = registry
        self.aggregator = aggregator or MultiAgentAggregator()
        self.tracker = tracker or MultiAgentExecutionTracker()
        self.max_concurrency = max(1, min(max_concurrency, 4))
        self._semaphore = asyncio.Semaphore(self.max_concurrency)

    async def coordinate(
        self,
        plan: DelegationPlan,
        context: ToolContext,
        timeout_override: float | None = None,
    ) -> AggregatedSpecialistResult:
        """
        Execute a validated DelegationPlan across registered domain specialists.

        Enforces:
        1. Max recursion depth == 1.
        2. Plan validation (1 to 4 specialists).
        3. Audit trace initiation.
        4. Dependency graph resolution.
        5. Bounded concurrency & total wall-clock timeout.
        6. Specialist execution, fallback, and partial failure containment.
        7. Cross-specialist evidence aggregation and conflict detection.
        """
        start_mono = time.monotonic()

        # 1. Pre-flight Validation
        if plan.max_depth != 1:
            raise ValueError(
                f"Delegation depth violation: max_depth must be strictly 1, got {plan.max_depth}."
            )

        if not (1 <= len(plan.delegations) <= 4):
            raise ValueError(
                f"Delegation count violation: plan must specify between 1 and 4 specialists, got {len(plan.delegations)}."
            )

        spec_ids = [d.target_specialist_id for d in plan.delegations]
        if len(spec_ids) != len(set(spec_ids)):
            raise ValueError(
                "Duplicate specialist delegations detected in plan: each specialist may only be invoked once."
            )

        valid_ids = {d.delegation_id for d in plan.delegations}
        _validate_dependency_graph(plan.dependencies, valid_ids)

        user_id = str(
            getattr(context.user, "user_id", None)
            or getattr(context.user, "id", None)
            or getattr(context.user, "email", None)
            or "usr_unknown"
        )

        # 2. Start Execution Trace
        self.tracker.start_trace(
            parent_execution_id=plan.parent_execution_id,
            user_id=user_id,
            plan=plan,
        )

        total_timeout = timeout_override or plan.total_timeout_seconds

        # 3. Prepare task state containers
        results_by_id: dict[str, SpecialistResult] = {}
        completion_events: dict[str, asyncio.Event] = {
            d.delegation_id: asyncio.Event() for d in plan.delegations
        }

        async def _execute_delegation(request: DelegationRequest) -> SpecialistResult:
            del_id = request.delegation_id
            spec_id = request.target_specialist_id
            epistemic_cat = SPECIALIST_EPISTEMIC_MAP.get(
                spec_id, EvidenceCategory.OBSERVED_DATA
            )

            # Wait for prerequisite delegations if declared
            prereqs = plan.dependencies.get(del_id, [])
            for prereq_id in prereqs:
                if prereq_id in completion_events:
                    await completion_events[prereq_id].wait()
                    prereq_res = results_by_id.get(prereq_id)
                    if prereq_res is None or prereq_res.status != SpecialistExecutionStatus.COMPLETED:
                        skipped_res = SpecialistResult(
                            specialist_id=spec_id,
                            delegation_id=del_id,
                            status=SpecialistExecutionStatus.SKIPPED,
                            summary=(
                                f"Skipped execution: Prerequisite delegation '{prereq_id}' did not "
                                f"complete successfully (status: {_enum_val(prereq_res.status) if prereq_res else 'NOT_FOUND'})."
                            ),
                            epistemic_category=epistemic_cat,
                            error_code=MultiAgentErrorCode.SPECIALIST_FAILED,
                            error_message=f"Prerequisite '{prereq_id}' failed or skipped",
                        )
                        results_by_id[del_id] = skipped_res
                        completion_events[del_id].set()
                        self.tracker.record_specialist_skipped(
                            delegation_id=del_id,
                            specialist_id=spec_id,
                            reason=skipped_res.summary,
                        )
                        return skipped_res

            # Acquire concurrency semaphore
            async with self._semaphore:
                # Specialist registration and enabled checks
                specialist = self.registry.get_specialist(spec_id)
                if not specialist:
                    failed_res = SpecialistResult(
                        specialist_id=spec_id,
                        delegation_id=del_id,
                        status=SpecialistExecutionStatus.FAILED,
                        summary=f"Specialist '{_enum_val(spec_id)}' is not registered in the system registry.",
                        epistemic_category=epistemic_cat,
                        error_code=MultiAgentErrorCode.SPECIALIST_NOT_FOUND,
                        error_message="Specialist not registered",
                    )
                    results_by_id[del_id] = failed_res
                    completion_events[del_id].set()
                    self.tracker.record_specialist_failed(
                        delegation_id=del_id,
                        specialist_id=spec_id,
                        error_code=MultiAgentErrorCode.SPECIALIST_NOT_FOUND,
                        error_message=failed_res.error_message or "",
                    )
                    return failed_res

                if not specialist.enabled:
                    disabled_res = SpecialistResult(
                        specialist_id=spec_id,
                        delegation_id=del_id,
                        status=SpecialistExecutionStatus.FAILED,
                        summary=f"Specialist '{_enum_val(spec_id)}' is currently disabled.",
                        epistemic_category=epistemic_cat,
                        error_code=MultiAgentErrorCode.SPECIALIST_DISABLED,
                        error_message="Specialist is disabled",
                    )
                    results_by_id[del_id] = disabled_res
                    completion_events[del_id].set()
                    self.tracker.record_specialist_failed(
                        delegation_id=del_id,
                        specialist_id=spec_id,
                        error_code=MultiAgentErrorCode.SPECIALIST_DISABLED,
                        error_message=disabled_res.error_message or "",
                    )
                    return disabled_res

                # Record started event
                self.tracker.record_specialist_started(request)

                # Forward upstream prerequisite evidence IDs if available
                enriched_context_evidence = list(request.context_evidence_ids)
                for prereq_id in prereqs:
                    prereq_res = results_by_id.get(prereq_id)
                    if prereq_res and prereq_res.evidence_ids:
                        for ev_id in prereq_res.evidence_ids:
                            if ev_id not in enriched_context_evidence:
                                enriched_context_evidence.append(ev_id)

                if enriched_context_evidence != request.context_evidence_ids:
                    request = request.model_copy(
                        update={"context_evidence_ids": enriched_context_evidence}
                    )

                # Execute specialist
                t0 = time.monotonic()
                try:
                    res = await specialist.execute(request, context)
                except TimeoutError:
                    dur_ms = max(0.0, (time.monotonic() - t0) * 1000.0)
                    res = SpecialistResult(
                        specialist_id=spec_id,
                        delegation_id=del_id,
                        status=SpecialistExecutionStatus.TIMED_OUT,
                        summary=f"Specialist '{_enum_val(spec_id)}' timed out after {request.timeout_seconds}s.",
                        epistemic_category=epistemic_cat,
                        error_code=MultiAgentErrorCode.EXECUTION_TIMEOUT,
                        error_message=f"Timeout of {request.timeout_seconds}s exceeded",
                        duration_ms=dur_ms,
                    )
                except asyncio.CancelledError:
                    dur_ms = max(0.0, (time.monotonic() - t0) * 1000.0)
                    res = SpecialistResult(
                        specialist_id=spec_id,
                        delegation_id=del_id,
                        status=SpecialistExecutionStatus.CANCELLED,
                        summary=f"Specialist '{_enum_val(spec_id)}' execution was cancelled.",
                        epistemic_category=epistemic_cat,
                        error_code=MultiAgentErrorCode.SPECIALIST_FAILED,
                        error_message="Execution cancelled",
                        duration_ms=dur_ms,
                    )
                    raise
                except Exception as exc:
                    dur_ms = max(0.0, (time.monotonic() - t0) * 1000.0)
                    logger.exception(
                        "Unhandled exception executing specialist %s: %s", _enum_val(spec_id), exc
                    )
                    raw_err = str(exc)
                    safe_err = _sanitize_value(raw_err)
                    if any(redacted in safe_err for redacted in ["[REDACTED", "Traceback", "File \""]):
                        safe_err = "Specialist encountered an internal operational execution error."
                    res = SpecialistResult(
                        specialist_id=spec_id,
                        delegation_id=del_id,
                        status=SpecialistExecutionStatus.FAILED,
                        summary=f"Specialist '{_enum_val(spec_id)}' encountered an internal execution error.",
                        epistemic_category=epistemic_cat,
                        error_code=MultiAgentErrorCode.SPECIALIST_FAILED,
                        error_message=safe_err,
                        duration_ms=dur_ms,
                    )

                results_by_id[del_id] = res
                completion_events[del_id].set()

                # Record outcome event
                if res.status == SpecialistExecutionStatus.COMPLETED:
                    self.tracker.record_specialist_completed(res)
                elif res.status == SpecialistExecutionStatus.TIMED_OUT:
                    self.tracker.record_specialist_timed_out(
                        delegation_id=del_id,
                        specialist_id=spec_id,
                        duration_ms=res.duration_ms,
                    )
                elif res.status == SpecialistExecutionStatus.CANCELLED:
                    self.tracker.record_specialist_cancelled(
                        delegation_id=del_id,
                        specialist_id=spec_id,
                        duration_ms=res.duration_ms,
                    )
                else:
                    self.tracker.record_specialist_failed(
                        delegation_id=del_id,
                        specialist_id=spec_id,
                        error_code=res.error_code or MultiAgentErrorCode.SPECIALIST_FAILED,
                        error_message=res.error_message or "Execution failed",
                        duration_ms=res.duration_ms,
                    )

                return res

        # 4. Schedule and execute all delegation tasks under total timeout budget
        tasks = [
            asyncio.create_task(_execute_delegation(req))
            for req in plan.delegations
        ]

        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=total_timeout,
            )
        except TimeoutError:
            logger.warning(
                "Multi-agent plan total timeout reached (%fs) | parent_id=%s plan_id=%s",
                total_timeout,
                plan.parent_execution_id,
                plan.plan_id,
            )
            # Cancel unfinished tasks
            for task in tasks:
                if not task.done():
                    task.cancel()

            # Wait briefly for cancellations to settle
            await asyncio.gather(*tasks, return_exceptions=True)

            # Mark any missing delegation results as TIMED_OUT
            for req in plan.delegations:
                if req.delegation_id not in results_by_id:
                    timed_out_res = SpecialistResult(
                        specialist_id=req.target_specialist_id,
                        delegation_id=req.delegation_id,
                        status=SpecialistExecutionStatus.TIMED_OUT,
                        summary=f"Specialist '{_enum_val(req.target_specialist_id)}' timed out when total plan budget expired.",
                        epistemic_category=SPECIALIST_EPISTEMIC_MAP.get(
                            req.target_specialist_id, EvidenceCategory.OBSERVED_DATA
                        ),
                        error_code=MultiAgentErrorCode.EXECUTION_TIMEOUT,
                        error_message=f"Total coordination timeout ({total_timeout}s) exceeded",
                    )
                    results_by_id[req.delegation_id] = timed_out_res
                    self.tracker.record_specialist_timed_out(
                        delegation_id=req.delegation_id,
                        specialist_id=req.target_specialist_id,
                    )
        except asyncio.CancelledError:
            logger.warning(
                "Multi-agent coordination cancelled externally | parent_id=%s plan_id=%s",
                plan.parent_execution_id,
                plan.plan_id,
            )
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise

        # 5. Assemble results in original plan order
        ordered_results = [results_by_id[d.delegation_id] for d in plan.delegations]

        total_coord_duration_ms = max(0.0, (time.monotonic() - start_mono) * 1000.0)

        # 6. Aggregate results
        aggregated = self.aggregator.aggregate(
            parent_execution_id=plan.parent_execution_id,
            plan_id=plan.plan_id,
            results=ordered_results,
            duration_ms=total_coord_duration_ms,
        )

        # 7. Finalize and persist audit trace
        await self.tracker.complete_trace(aggregated)

        return aggregated
