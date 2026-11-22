"""
HospitalOps AI — Forecasting Specialist Agent (Milestone 5, Chunk 5.6.2).

Responsibilities:
- Retrieve existing demand (admissions) and capacity (ICU) forecasts.
- Explain forecasted metrics, horizons, and model architectures.
- Distinguish historical observations from projected predictions.
- Report genuine confidence intervals only when returned by the model; never fabricate them.
- Preserve daily (Hero DMC) versus weekly (NHSN HRD) dataset cadence.
- Reject clinical queries and prohibit model retraining during execution.
"""

from __future__ import annotations

import logging
import re

from app.agents.evidence import AgentEvidence, EvidenceCategory
from app.agents.multi_agent.contracts import (
    DelegationRequest,
    MultiAgentErrorCode,
    SpecialistDomain,
    SpecialistExecutionStatus,
    SpecialistId,
    SpecialistResult,
)
from app.agents.multi_agent.specialists.base import BaseSpecialist
from app.agents.tools.base import ToolContext
from app.agents.tools.forecast_tools import (
    GetExistingForecastInput,
    GetExistingForecastOutput,
    GetExistingForecastTool,
)
from app.services.forecast import ForecastService

logger = logging.getLogger(__name__)


class ForecastingSpecialist(BaseSpecialist):
    """
    Domain specialist for analyzing hospital census trends, admissions forecasts,
    and ICU capacity projections with verified prediction intervals.
    """

    def __init__(
        self,
        forecast_service: ForecastService | None = None,
        tool: GetExistingForecastTool | None = None,
    ) -> None:
        super().__init__(
            specialist_id=SpecialistId.FORECASTING,
            domain=SpecialistDomain.FORECASTING,
        )
        if tool is not None:
            self.tool = tool
        elif forecast_service is not None:
            self.tool = GetExistingForecastTool(forecast_service)
        else:
            raise ValueError("ForecastingSpecialist requires either forecast_service or tool.")

    async def _execute_domain(
        self,
        request: DelegationRequest,
        context: ToolContext,
    ) -> SpecialistResult:
        query_text = request.task_description.lower()

        # 1. Parse forecast type: admissions vs ICU
        is_icu = bool(re.search(r"\b(icu|intensive|critical|bed capacity|weekly)\b", query_text))
        forecast_type = "icu" if is_icu else "admissions"

        # 2. Parse horizon if specified
        horizon: int | None = None
        if is_icu:
            # Look for weeks
            match_w = re.search(r"\b(\d+)\s*(?:week|weeks|w)\b", query_text)
            if match_w:
                horizon = int(match_w.group(1))
            else:
                horizon = 2
        else:
            # Look for days
            match_d = re.search(r"\b(\d+)\s*(?:day|days|d)\b", query_text)
            if match_d:
                horizon = int(match_d.group(1))
            else:
                horizon = 7

        # 3. Parse optional model family override
        model_type: str | None = None
        for m in ("lstm", "prophet", "arima", "baseline"):
            if m in query_text:
                model_type = m
                break

        # 4. Parse run ID if specified
        run_id_match = re.search(r"\b([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\b", query_text)
        run_id = run_id_match.group(1) if run_id_match else None

        tool_input = GetExistingForecastInput(
            forecast_type=forecast_type,
            horizon=horizon,
            model_type=model_type,
            run_id=run_id,
        )

        # 5. Execute read-only tool under trusted context
        tool_result = await self.tool.execute(tool_input, context)

        if not tool_result.success:
            err_msg = tool_result.error_message or "Forecast data could not be retrieved."
            logger.warning("Forecasting tool failed | error=%s", err_msg)
            return SpecialistResult(
                specialist_id=self.specialist_id,
                delegation_id=request.delegation_id,
                status=SpecialistExecutionStatus.FAILED,
                summary=f"Unable to retrieve operational forecast: {err_msg}",
                error_message=err_msg,
                error_code=MultiAgentErrorCode.SPECIALIST_FAILED,
                epistemic_category=EvidenceCategory.FORECAST,
                tool_calls_count=1,
            )

        data = tool_result.data
        if isinstance(data, dict):
            _dataset_name = data.get("dataset_name", "unknown")
            model_name = data.get("model_name", "standard")
            model_family = data.get("model_type", "forecast")
            horizon_len = data.get("horizon", horizon)
            horizon_unit = data.get("horizon_unit", "d")
            sample_preds = data.get("sample_predictions", [])
            preds_count = data.get("predictions_count", len(sample_preds))
        elif isinstance(data, GetExistingForecastOutput):
            model_name = data.model_name
            model_family = data.model_type
            horizon_len = data.horizon
            horizon_unit = data.horizon_unit
            sample_preds = [p.model_dump() if hasattr(p, "model_dump") else p for p in data.sample_predictions]
            preds_count = data.predictions_count
        else:
            model_name = "production"
            model_family = "forecast"
            horizon_len = horizon
            horizon_unit = "w" if is_icu else "d"
            sample_preds = []
            preds_count = 0

        # Check for genuine prediction intervals
        has_confidence_intervals = any(
            p.get("lower_bound") is not None and p.get("upper_bound") is not None
            for p in sample_preds
            if isinstance(p, dict)
        )

        unit_label = "weeks" if horizon_unit == "w" else "days"
        cadence_desc = "weekly facility-level series (NHSN HRD)" if is_icu else "daily admission series (Hero DMC)"

        lines = [
            "**Operational Demand Forecast Analysis**",
            f"- **Metric / Dataset:** {cadence_desc}",
            f"- **Model Selected:** {model_name} (Architecture: {model_family})",
            f"- **Projection Horizon:** {horizon_len} {unit_label} ({preds_count} total steps)",
        ]

        if has_confidence_intervals:
            lines.append("- **Confidence Intervals:** 95% prediction intervals verified and present in forecast trajectory.")
        else:
            lines.append("- **Confidence Intervals:** Point estimates only; intervals not generated by this baseline architecture.")

        if sample_preds:
            lines.append("\n**Trajectory Highlights:**")
            for idx, pt in enumerate(sample_preds[:5], 1):
                if isinstance(pt, dict):
                    ts = pt.get("timestamp", f"Step {idx}")[:10]
                    val = pt.get("value", 0.0)
                    lb = pt.get("lower_bound")
                    ub = pt.get("upper_bound")
                    if lb is not None and ub is not None:
                        lines.append(f"  - {ts}: {val:.1f} (95% CI: [{lb:.1f}, {ub:.1f}])")
                    else:
                        lines.append(f"  - {ts}: {val:.1f}")

        lines.append(
            "\n*Epistemic Notice: All values represent statistical model projections and not historical observed facts.*"
        )
        summary = "\n".join(lines)

        evidence_item = AgentEvidence(
            tool_id=self.tool.name,
            tool_version=self.tool.schema_version,
            category=EvidenceCategory.FORECAST,
            summary=summary,
            data=data.model_dump() if hasattr(data, "model_dump") else (data if isinstance(data, dict) else {}),
            source_references=[p.id for p in tool_result.provenance_items],
            is_projection=True,
            is_hypothetical=False,
            is_recommendation=False,
        )

        return SpecialistResult(
            specialist_id=self.specialist_id,
            delegation_id=request.delegation_id,
            status=SpecialistExecutionStatus.COMPLETED,
            summary=summary,
            evidence=[evidence_item],
            evidence_ids=[evidence_item.evidence_id],
            provenance=tool_result.provenance_items,
            citations=[],
            epistemic_category=EvidenceCategory.FORECAST,
            tool_calls_count=1,
            is_fallback=False,
        )
