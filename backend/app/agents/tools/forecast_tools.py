"""
HospitalOps AI — Forecasting Agent Tools (Milestone 5, Chunks 5.1 & 5.2).

Integrates the Forecasting Engine as a read-only tool to inspect existing
daily admission demand forecasts (Hero DMC) and weekly ICU occupancy projections (NHSN HRD).
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from app.agents.contracts import ProvenanceCategory, ProvenanceItem, ToolCategory
from app.agents.tools.base import AgentTool, ToolContext, ToolResult
from app.services.forecast import ForecastService

logger = logging.getLogger(__name__)


class GetExistingForecastInput(BaseModel):
    """Input parameters for inspecting existing demand and capacity forecasts."""

    forecast_type: str = Field(
        default="admissions",
        description="Type of forecast to inspect: 'admissions' (daily admissions, Hero DMC) or 'icu' (weekly ICU beds, NHSN HRD)",
    )
    horizon: int | None = Field(
        default=None,
        description="Forecast horizon (days for admissions: 1-30, default 7; weeks for ICU: 1-8, default 2)",
    )
    model_type: str | None = Field(
        default=None,
        description="Optional model family override: 'baseline', 'arima', 'prophet', 'lstm'",
    )
    run_id: str | None = Field(
        default=None,
        description="Optional specific historical experiment run ID to retrieve",
    )


class ForecastPointOutput(BaseModel):
    """Individual projected timeseries point."""

    timestamp: str = Field(description="ISO timestamp of projection")
    value: float = Field(description="Point estimate in physical units")
    lower_bound: float | None = Field(default=None, description="Lower prediction interval (e.g. 95% CI)")
    upper_bound: float | None = Field(default=None, description="Upper prediction interval (e.g. 95% CI)")


class GetExistingForecastOutput(BaseModel):
    """Standardized output schema for operational demand forecast inspection."""

    dataset_name: str = Field(description="Underlying dataset ('hero_dmc' or 'nhsn_hrd')")
    target_column: str = Field(description="Physical target metric forecasted")
    model_name: str = Field(description="Specific model identifier or configuration")
    model_type: str = Field(description="Model architecture family ('arima', 'prophet', 'lstm', etc.)")
    horizon: int = Field(description="Horizon length")
    horizon_unit: str = Field(description="Horizon unit ('d' for days, 'w' for weeks)")
    predictions_count: int = Field(ge=0, description="Total projected steps in trajectory")
    sample_predictions: list[ForecastPointOutput] = Field(default_factory=list, description="Initial projection points")


class GetExistingForecastTool(AgentTool):
    """Tool that reads existing verified operational demand forecasts."""

    def __init__(self, forecast_service: ForecastService) -> None:
        self.service = forecast_service

    @property
    def name(self) -> str:
        return "get_existing_forecast"

    @property
    def display_name(self) -> str:
        return "Demand Forecast Inspection"

    @property
    def description(self) -> str:
        return (
            "Retrieve verified machine learning operational demand forecasts for hospital daily admissions "
            "(Hero DMC series, 1-30 days) or weekly ICU capacity (NHSN HRD series, 1-8 weeks). "
            "Returns projected values, confidence bounds, and model provenance."
        )

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FORECASTING

    @property
    def schema_version(self) -> str:
        return "1.0.0"

    @property
    def input_schema(self) -> type[BaseModel]:
        return GetExistingForecastInput

    @property
    def output_schema(self) -> type[BaseModel]:
        return GetExistingForecastOutput

    @property
    def required_permission(self) -> str:
        return "predictions.read"

    @property
    def tags(self) -> list[str]:
        return ["forecast", "admissions", "icu", "hero_dmc", "nhsn_hrd", "demand"]

    @property
    def timeout_seconds(self) -> float:
        return 20.0

    async def execute(self, arguments: BaseModel, context: ToolContext) -> ToolResult:
        args = arguments if isinstance(arguments, GetExistingForecastInput) else GetExistingForecastInput.model_validate(arguments)

        f_type = args.forecast_type.lower()
        try:
            if f_type in ("admissions", "admission", "daily"):
                horizon = args.horizon if args.horizon is not None else 7
                resp = await self.service.get_admissions_forecast(
                    horizon=horizon,
                    model_type=args.model_type,
                    run_id=args.run_id,
                )
            elif f_type in ("icu", "weekly", "capacity"):
                horizon = args.horizon if args.horizon is not None else 2
                resp = await self.service.get_icu_forecast(
                    horizon=horizon,
                    model_type=args.model_type,
                    run_id=args.run_id,
                )
            else:
                return ToolResult(
                    success=False,
                    error_message=f"Unsupported forecast type '{args.forecast_type}'. Must be 'admissions' or 'icu'.",
                    output_summary=f"Unsupported forecast type '{args.forecast_type}'.",
                )
        except Exception as exc:
            logger.warning("Forecast inspection failed | type=%s err=%s", f_type, exc)
            return ToolResult(
                success=False,
                error_message=f"Forecast retrieval failed: {exc}",
                output_summary=f"No matching forecast found or error: {exc}",
            )

        meta = resp.metadata
        points_summary = []
        sample_pts: list[ForecastPointOutput] = []

        for pt in resp.predictions[:7]:
            ci_str = f" [95% CI: {pt.lower_bound:.1f} - {pt.upper_bound:.1f}]" if pt.lower_bound is not None else ""
            val = getattr(pt, "value", getattr(pt, "predicted_value", 0.0))
            points_summary.append(f"{pt.timestamp[:10]}: {val:.1f} {meta.target_units}{ci_str}")
            sample_pts.append(
                ForecastPointOutput(
                    timestamp=pt.timestamp,
                    value=float(val),
                    lower_bound=float(pt.lower_bound) if pt.lower_bound is not None else None,
                    upper_bound=float(pt.upper_bound) if pt.upper_bound is not None else None,
                )
            )

        model_identifier = getattr(meta, "model_name", getattr(meta, "config_name", meta.model_type))

        prov_item = ProvenanceItem(
            category=ProvenanceCategory.FORECAST,
            id=model_identifier,
            label=f"{meta.dataset_name.upper()} {meta.target_column} ({meta.model_type.upper()})",
            details={
                "horizon": f"{meta.horizon}{meta.horizon_unit}",
                "frequency": meta.frequency,
                "winner_resolved": getattr(meta, "winner_model_resolved", True),
                "provenance": getattr(meta, "provenance", "forecast_run"),
            },
        )

        summary_text = (
            f"Forecast Summary (Model: {model_identifier}, Cadence: {meta.frequency}, Horizon: {meta.horizon}{meta.horizon_unit}):\n"
            f"Target: {meta.target_column} in {meta.target_units} (Dataset: {meta.dataset_name})\n"
            + "\n".join(points_summary)
        )

        output_data = GetExistingForecastOutput(
            dataset_name=meta.dataset_name,
            target_column=meta.target_column,
            model_name=model_identifier,
            model_type=meta.model_type,
            horizon=meta.horizon,
            horizon_unit=meta.horizon_unit,
            predictions_count=len(resp.predictions),
            sample_predictions=sample_pts,
        )

        return ToolResult(
            success=True,
            data=output_data,
            output_summary=summary_text,
            provenance_items=[prov_item],
        )
