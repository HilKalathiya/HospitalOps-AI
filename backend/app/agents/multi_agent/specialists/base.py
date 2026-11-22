"""
HospitalOps AI — Base Specialist Agent Specification (Milestone 5, Chunk 5.6.2).

Defines the abstract BaseSpecialist class enforcing:
- Server-side RBAC validation before tool invocation
- Healthcare safety boundary (ClinicalSafetyPolicy enforcement)
- Bounded execution timeouts and output budgets
- Non-leaking structured error handling
- Epistemic classification and provenance preservation
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod

from app.agents.evidence import EvidenceCategory
from app.agents.multi_agent.contracts import (
    STANDARD_SPECIALISTS,
    DelegationRequest,
    MultiAgentErrorCode,
    SpecialistDefinition,
    SpecialistDomain,
    SpecialistExecutionStatus,
    SpecialistId,
    SpecialistResult,
)
from app.agents.policies import AgentPolicyEnforcer
from app.agents.tools.base import ToolContext
from app.models.base import utc_now

logger = logging.getLogger(__name__)


class BaseSpecialist(ABC):
    """
    Abstract base class for all bounded domain specialist agents.

    Specialists are read-only domain experts that execute authorized underlying
    tools and synthesize structured operational findings for the supervisor.
    """

    def __init__(self, specialist_id: SpecialistId, domain: SpecialistDomain) -> None:
        self.specialist_id = specialist_id
        self.domain = domain
        self._enabled: bool = True

    @property
    def definition(self) -> SpecialistDefinition:
        """Retrieve static contract definition for this specialist."""
        return STANDARD_SPECIALISTS[self.specialist_id]

    @property
    def enabled(self) -> bool:
        """Whether this specialist is active."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = bool(value)

    @property
    def required_permissions(self) -> list[str]:
        """Server-side permissions required to execute this specialist."""
        return self.definition.required_permissions

    @property
    def allowed_tool_ids(self) -> list[str]:
        """Allowed underlying tool IDs."""
        return self.definition.allowed_tool_ids

    async def execute(
        self,
        request: DelegationRequest,
        context: ToolContext,
    ) -> SpecialistResult:
        """
        Execute a bounded delegation request within the trusted runtime.

        Enforces:
        1. Specialist identity match.
        2. Specialist enabled state.
        3. Server-validated RBAC permissions.
        4. Clinical scope boundary screening.
        5. Timeout bounding and cancellation handling.
        6. Output size and evidence item clamping.
        """
        started_at = utc_now()

        # 1. Specialist Identity Verification
        if request.target_specialist_id != self.specialist_id:
            ended_at = utc_now()
            duration_ms = max(0.0, (ended_at - started_at).total_seconds() * 1000.0)
            logger.warning(
                "Specialist identity mismatch | requested=%s actual=%s",
                request.target_specialist_id,
                self.specialist_id,
            )
            return SpecialistResult(
                specialist_id=self.specialist_id,
                delegation_id=request.delegation_id,
                status=SpecialistExecutionStatus.FAILED,
                summary=f"Specialist identity mismatch: target '{request.target_specialist_id}' routed to '{self.specialist_id}'.",
                error_message=f"Requested specialist {request.target_specialist_id} does not match handler {self.specialist_id}.",
                error_code=MultiAgentErrorCode.SPECIALIST_NOT_FOUND,
                epistemic_category=self._default_epistemic_category(),
                started_at=started_at,
                ended_at=ended_at,
                duration_ms=duration_ms,
            )

        # 2. Enabled State Check
        if not self.enabled:
            ended_at = utc_now()
            duration_ms = max(0.0, (ended_at - started_at).total_seconds() * 1000.0)
            logger.warning("Specialist is disabled | specialist=%s", self.specialist_id)
            return SpecialistResult(
                specialist_id=self.specialist_id,
                delegation_id=request.delegation_id,
                status=SpecialistExecutionStatus.FAILED,
                summary=f"Specialist '{self.specialist_id.value}' is currently disabled in system configuration.",
                error_message=f"Specialist '{self.specialist_id.value}' is disabled.",
                error_code=MultiAgentErrorCode.SPECIALIST_DISABLED,
                epistemic_category=self._default_epistemic_category(),
                started_at=started_at,
                ended_at=ended_at,
                duration_ms=duration_ms,
            )

        # 3. Server-Side RBAC Revalidation
        missing_permissions = [
            perm for perm in self.required_permissions if perm not in context.permissions
        ]
        if missing_permissions:
            ended_at = utc_now()
            duration_ms = max(0.0, (ended_at - started_at).total_seconds() * 1000.0)
            logger.warning(
                "Specialist RBAC denied | user=%s specialist=%s missing=%s",
                context.user.user_id,
                self.specialist_id,
                missing_permissions,
            )
            return SpecialistResult(
                specialist_id=self.specialist_id,
                delegation_id=request.delegation_id,
                status=SpecialistExecutionStatus.FAILED,
                summary=f"Caller lacks required permission(s) to invoke {self.specialist_id.value}: {missing_permissions}.",
                error_message=f"Access denied: Missing permissions {missing_permissions}.",
                error_code=MultiAgentErrorCode.PERMISSION_DENIED,
                epistemic_category=self._default_epistemic_category(),
                started_at=started_at,
                ended_at=ended_at,
                duration_ms=duration_ms,
            )

        # 4. Clinical Scope Boundary Filter
        is_clinical, clinical_reason = AgentPolicyEnforcer.check_clinical_scope(
            request.task_description
        )
        if is_clinical:
            ended_at = utc_now()
            duration_ms = max(0.0, (ended_at - started_at).total_seconds() * 1000.0)
            logger.info(
                "Specialist task rejected by clinical safety boundary | specialist=%s reason=%s",
                self.specialist_id,
                clinical_reason[:60],
            )
            return SpecialistResult(
                specialist_id=self.specialist_id,
                delegation_id=request.delegation_id,
                status=SpecialistExecutionStatus.FAILED,
                summary="The delegated task requires clinical diagnosis or prescribing, which is prohibited under the healthcare safety policy.",
                error_message=f"Clinical safety violation: {clinical_reason}",
                error_code=MultiAgentErrorCode.POLICY_VIOLATION,
                epistemic_category=self._default_epistemic_category(),
                started_at=started_at,
                ended_at=ended_at,
                duration_ms=duration_ms,
            )

        # 5. Bounded Execution with Timeout
        timeout = float(min(request.timeout_seconds, 45.0))
        try:
            raw_result = await asyncio.wait_for(
                self._execute_domain(request, context),
                timeout=timeout,
            )
        except TimeoutError:
            ended_at = utc_now()
            duration_ms = max(0.0, (ended_at - started_at).total_seconds() * 1000.0)
            logger.warning(
                "Specialist execution timed out | specialist=%s timeout=%.1fs",
                self.specialist_id,
                timeout,
            )
            return SpecialistResult(
                specialist_id=self.specialist_id,
                delegation_id=request.delegation_id,
                status=SpecialistExecutionStatus.TIMED_OUT,
                summary=f"Specialist '{self.specialist_id.value}' timed out after {timeout:.1f} seconds.",
                error_message=f"Execution exceeded allotted timeout of {timeout:.1f}s.",
                error_code=MultiAgentErrorCode.EXECUTION_TIMEOUT,
                epistemic_category=self._default_epistemic_category(),
                started_at=started_at,
                ended_at=ended_at,
                duration_ms=duration_ms,
            )
        except asyncio.CancelledError:
            ended_at = utc_now()
            duration_ms = max(0.0, (ended_at - started_at).total_seconds() * 1000.0)
            logger.info("Specialist execution cancelled | specialist=%s", self.specialist_id)
            return SpecialistResult(
                specialist_id=self.specialist_id,
                delegation_id=request.delegation_id,
                status=SpecialistExecutionStatus.CANCELLED,
                summary=f"Specialist '{self.specialist_id.value}' execution was cancelled.",
                error_message="Execution was cancelled.",
                error_code=MultiAgentErrorCode.SPECIALIST_FAILED,
                epistemic_category=self._default_epistemic_category(),
                started_at=started_at,
                ended_at=ended_at,
                duration_ms=duration_ms,
            )
        except Exception as exc:
            ended_at = utc_now()
            duration_ms = max(0.0, (ended_at - started_at).total_seconds() * 1000.0)
            logger.exception(
                "Unhandled exception in specialist execution | specialist=%s error=%s",
                self.specialist_id,
                exc,
            )
            return SpecialistResult(
                specialist_id=self.specialist_id,
                delegation_id=request.delegation_id,
                status=SpecialistExecutionStatus.FAILED,
                summary=f"Specialist execution failed due to an internal error: {str(exc)[:200]}",
                error_message=f"Internal specialist error: {str(exc)[:300]}",
                error_code=MultiAgentErrorCode.SPECIALIST_FAILED,
                epistemic_category=self._default_epistemic_category(),
                started_at=started_at,
                ended_at=ended_at,
                duration_ms=duration_ms,
            )

        # 6. Post-Execution Clamping and Normalization
        ended_at = utc_now()
        duration_ms = max(0.0, (ended_at - started_at).total_seconds() * 1000.0)

        summary = raw_result.summary
        if len(summary) > request.max_output_chars:
            allowed = max(50, request.max_output_chars - 45)
            summary = summary[:allowed] + "\n... [Output truncated to budget]"

        evidence = raw_result.evidence[: request.max_evidence_items]
        evidence_ids = [e.evidence_id for e in evidence]

        return SpecialistResult(
            specialist_id=self.specialist_id,
            delegation_id=request.delegation_id,
            status=raw_result.status,
            summary=summary,
            evidence=evidence,
            evidence_ids=evidence_ids,
            provenance=raw_result.provenance,
            citations=raw_result.citations,
            epistemic_category=raw_result.epistemic_category,
            tool_calls_count=raw_result.tool_calls_count,
            error_message=raw_result.error_message,
            error_code=raw_result.error_code,
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=duration_ms,
            is_fallback=raw_result.is_fallback,
        )

    def _default_epistemic_category(self) -> EvidenceCategory:
        """Map specialist domain to default epistemic evidence category."""
        mapping = {
            SpecialistDomain.FORECASTING: EvidenceCategory.FORECAST,
            SpecialistDomain.SIMULATION: EvidenceCategory.SIMULATION,
            SpecialistDomain.OPTIMIZATION: EvidenceCategory.OPTIMIZATION,
            SpecialistDomain.KNOWLEDGE: EvidenceCategory.KNOWLEDGE_POLICY,
        }
        return mapping.get(self.domain, EvidenceCategory.OBSERVED_DATA)

    @abstractmethod
    async def _execute_domain(
        self,
        request: DelegationRequest,
        context: ToolContext,
    ) -> SpecialistResult:
        """
        Domain-specific execution logic implemented by each specialist subclass.
        """
