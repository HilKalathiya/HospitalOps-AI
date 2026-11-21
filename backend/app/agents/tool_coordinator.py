"""
HospitalOps AI — Tool Execution Coordinator (Milestone 5, Chunk 5.3).

Coordinates the end-to-end execution of agent tools:
1. Tool lookup and eligibility verification.
2. Server-side RBAC validation.
3. Pre-execution argument validation (Chunk 5.2).
4. Duplicate/loop prevention.
5. Execution under timeout.
6. Post-execution output contract validation.
7. Structured evidence extraction and provenance linking.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from pydantic import Field

from app.agents.contracts import (
    ProvenanceItem,
    ToolCallRecord,
    ToolCategory,
    ToolErrorCode,
)
from app.agents.evidence import AgentEvidence, AgentEvidenceCollector, EvidenceCategory
from app.agents.policies import AgentPolicyEnforcer
from app.agents.registry import ToolRegistry
from app.agents.tools.base import AgentTool, ToolContext, ToolResult
from app.models.base import HospitalOpsBaseModel

logger = logging.getLogger(__name__)


def map_tool_category_to_evidence(cat: ToolCategory) -> EvidenceCategory:
    """Map a tool's domain category to an evidence domain category."""
    mapping = {
        ToolCategory.KNOWLEDGE: EvidenceCategory.KNOWLEDGE_POLICY,
        ToolCategory.FORECASTING: EvidenceCategory.FORECAST,
        ToolCategory.SIMULATION: EvidenceCategory.SIMULATION,
        ToolCategory.OPTIMIZATION: EvidenceCategory.OPTIMIZATION,
        ToolCategory.OPERATIONS: EvidenceCategory.OBSERVED_DATA,
        ToolCategory.SYSTEM: EvidenceCategory.OBSERVED_DATA,
    }
    return mapping.get(cat, EvidenceCategory.OBSERVED_DATA)


class ToolCoordinationResult(HospitalOpsBaseModel):
    """Structured outcome from the tool execution coordinator."""

    tool_id: str
    status: str = Field(description="'SUCCESS', 'BLOCKED', 'VALIDATION_ERROR', 'FAILED', 'TIMEOUT'")
    record: ToolCallRecord
    evidence: AgentEvidence | None = None
    provenance_items: list[ProvenanceItem] = Field(default_factory=list)
    citations: list[Any] = Field(default_factory=list)
    error_code: ToolErrorCode | None = None
    error_message: str | None = None
    is_terminal_failure: bool = False


class ToolExecutionCoordinator:
    """
    Coordinates tool invocations during agent orchestration.
    Enforces permissions, Chunk 5.2 validation pipelines, loop protections,
    and structured evidence ingestion.
    """

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def get_eligible_tools(self, user_permissions: list[str]) -> list[AgentTool]:
        """Discover tools available to the user under RBAC."""
        definitions = self.registry.discover_tools(user_permissions=user_permissions)
        allowed_ids = {d.tool_id for d in definitions}
        return [t for t in self.registry.list_all() if t.name in allowed_ids]

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        reason: str,
        step_index: int,
        tool_context: ToolContext,
        evidence_collector: AgentEvidenceCollector,
        call_history: list[tuple[str, str]],
    ) -> ToolCoordinationResult:
        """
        Execute a proposed tool invocation with complete validation, RBAC checks,
        and evidence extraction.
        """
        start_time = time.perf_counter()

        # 1. Check Tool Registration
        tool = self.registry.get(tool_name)
        if not tool:
            msg = f"Tool '{tool_name}' is not registered in the system allowlist."
            logger.warning(msg)
            record = ToolCallRecord(
                step_index=step_index,
                tool_name=tool_name,
                reason=reason,
                arguments=arguments,
                status="BLOCKED",
                duration_ms=0.0,
                output_summary=msg,
                error_message=msg,
                error_code=ToolErrorCode.UNKNOWN_TOOL,
            )
            return ToolCoordinationResult(
                tool_id=tool_name,
                status="BLOCKED",
                record=record,
                error_code=ToolErrorCode.UNKNOWN_TOOL,
                error_message=msg,
            )

        # 2. Check RBAC Permissions
        allowed, denial_reason = AgentPolicyEnforcer.check_tool_permission(tool_context.permissions, tool)
        if not allowed:
            logger.warning("Tool execution blocked by RBAC: %s", denial_reason)
            record = ToolCallRecord(
                step_index=step_index,
                tool_name=tool.name,
                reason=reason,
                arguments=arguments,
                status="BLOCKED",
                duration_ms=0.0,
                output_summary=denial_reason or "Permission denied.",
                error_message=denial_reason,
                error_code=ToolErrorCode.PERMISSION_DENIED,
                schema_version=tool.schema_version,
            )
            return ToolCoordinationResult(
                tool_id=tool.name,
                status="BLOCKED",
                record=record,
                error_code=ToolErrorCode.PERMISSION_DENIED,
                error_message=denial_reason,
            )

        # 3. Check Duplicate Invocation Loop Policy
        if AgentPolicyEnforcer.is_duplicate_call(call_history, tool.name, arguments):
            msg = f"Duplicate identical call to tool '{tool.name}' blocked by loop policy."
            logger.warning(msg)
            record = ToolCallRecord(
                step_index=step_index,
                tool_name=tool.name,
                reason=reason,
                arguments=arguments,
                status="BLOCKED",
                duration_ms=0.0,
                output_summary=msg,
                error_message="Repeated identical tool call.",
                error_code=ToolErrorCode.APPROVAL_REQUIRED,
                schema_version=tool.schema_version,
            )
            return ToolCoordinationResult(
                tool_id=tool.name,
                status="BLOCKED",
                record=record,
                error_code=ToolErrorCode.APPROVAL_REQUIRED,
                error_message=msg,
                is_terminal_failure=True,
            )

        # Record call signature in history
        call_history.append((tool.name, json.dumps(arguments, sort_keys=True, default=str)))

        # 4. Execute with Chunk 5.2 Dual Validation Pipeline
        try:
            result: ToolResult = await tool.execute_with_validation(arguments, tool_context)
            duration_ms = (time.perf_counter() - start_time) * 1000

            record = ToolCallRecord(
                step_index=step_index,
                tool_name=tool.name,
                reason=reason,
                arguments=arguments,
                status=result.status if result.status else ("SUCCESS" if result.success else "FAILED"),
                duration_ms=round(duration_ms, 2),
                output_summary=result.output_summary[:1000],
                error_message=result.error_message,
                error_code=result.error.code if result.error else None,
                schema_version=result.schema_version,
                sources_found=len(result.provenance_items),
                provenance_ids=[p.id for p in result.provenance_items],
            )

            # Ingest as formal evidence if successful
            evidence: AgentEvidence | None = None
            if result.success and result.data is not None:
                ev_category = map_tool_category_to_evidence(tool.category)
                source_refs = [p.id for p in result.provenance_items]
                evidence = evidence_collector.add_evidence(
                    tool_id=tool.name,
                    tool_version=tool.schema_version,
                    category=ev_category,
                    summary=result.output_summary,
                    data=result.data,
                    source_references=source_refs,
                    execution_step=step_index,
                )

            return ToolCoordinationResult(
                tool_id=tool.name,
                status=result.status if result.status else ("SUCCESS" if result.success else "FAILED"),
                record=record,
                evidence=evidence,
                provenance_items=result.provenance_items,
                citations=result.citations,
                error_code=result.error.code if result.error else None,
                error_message=result.error_message,
            )

        except TimeoutError:
            duration_ms = (time.perf_counter() - start_time) * 1000
            msg = f"Tool '{tool.name}' exceeded its timeout threshold."
            logger.error(msg)
            record = ToolCallRecord(
                step_index=step_index,
                tool_name=tool.name,
                reason=reason,
                arguments=arguments,
                status="FAILED",
                duration_ms=round(duration_ms, 2),
                output_summary=msg,
                error_message=msg,
                error_code=ToolErrorCode.EXECUTION_TIMEOUT,
                schema_version=tool.schema_version,
            )
            return ToolCoordinationResult(
                tool_id=tool.name,
                status="TIMEOUT",
                record=record,
                error_code=ToolErrorCode.EXECUTION_TIMEOUT,
                error_message=msg,
            )

        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            msg = f"Unexpected tool execution error: {exc}"
            logger.error("Tool execution failed unexpectedly: %s", exc, exc_info=True)
            record = ToolCallRecord(
                step_index=step_index,
                tool_name=tool.name,
                reason=reason,
                arguments=arguments,
                status="FAILED",
                duration_ms=round(duration_ms, 2),
                output_summary=msg,
                error_message=str(exc),
                error_code=ToolErrorCode.EXECUTION_FAILED,
                schema_version=tool.schema_version,
            )
            return ToolCoordinationResult(
                tool_id=tool.name,
                status="FAILED",
                record=record,
                error_code=ToolErrorCode.EXECUTION_FAILED,
                error_message=str(exc),
            )
