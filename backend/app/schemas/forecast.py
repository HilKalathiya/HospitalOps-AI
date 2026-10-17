"""
HospitalOps AI — Forecasting API Schemas (Chunk 2.7).

Defines strongly-typed request parameters and response contracts for
forecasting endpoints, benchmark reporting, and historical experiment runs.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from app.ml.contracts.selection import ModelEvaluationEntry


class PredictionPoint(BaseModel):
    """A single forecasted time-series point with optional interval bounds."""

    timestamp: str = Field(
        description="Forecast timestamp as ISO date string (e.g. '2025-01-01')."
    )
    value: float = Field(
        description="Point prediction value in physical target units."
    )
    lower_bound: float | None = Field(
        default=None,
        description="Lower prediction/confidence bound when supported by model (e.g. LSTM MC dropout).",
    )
    upper_bound: float | None = Field(
        default=None,
        description="Upper prediction/confidence bound when supported by model.",
    )
    confidence_level: float | None = Field(
        default=None,
        description="Confidence level (e.g. 0.95 for 95% CI) when bounds are present.",
    )


class ForecastMetadata(BaseModel):
    """Provenance and specification metadata for a generated or retrieved forecast."""

    dataset_name: str = Field(description="Dataset identifier (e.g. 'hero_dmc', 'nhsn_hrd').")
    target_column: str = Field(description="Target column name.")
    target_units: str = Field(description="Physical unit of target (e.g. 'admissions', 'beds').")
    frequency: str = Field(description="Temporal frequency ('D' for daily, 'W' for weekly).")
    horizon: int = Field(description="Forecast horizon length.")
    horizon_unit: str = Field(description="Horizon unit ('d' for days, 'w' for weeks).")
    forecast_origin: str | None = Field(
        default=None, description="Last-observed date / cut-off timestamp."
    )
    model_type: str = Field(description="Selected or requested model family (baseline, arima, prophet, lstm).")
    config_name: str = Field(description="Specific model configuration name.")
    run_id: str | None = Field(default=None, description="Experiment run identifier.")
    mlflow_run_id: str | None = Field(default=None, description="MLflow tracking run ID if logged.")
    selection_criterion: str | None = Field(
        default="val_mae", description="Metric used for model selection."
    )
    validation_mae: float | None = Field(
        default=None, description="Validation MAE of the selected model."
    )
    test_mae: float | None = Field(
        default=None, description="Held-out test MAE (for reporting only, never tuning)."
    )
    intervals_supported: bool = Field(
        default=False, description="Whether the model provides genuine uncertainty intervals."
    )
    provenance: str = Field(
        default="benchmark_selection",
        description="Source of forecast: 'saved_benchmark_run' | 'saved_run' | 'on_demand_fit'.",
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC generation timestamp.",
    )


class ForecastResponse(BaseModel):
    """Top-level domain payload for forecast endpoints."""

    status: str = Field(
        default="SUCCESS",
        description="Execution status ('SUCCESS', 'UNSUPPORTED', 'UNAVAILABLE', 'FAILED').",
    )
    message: str | None = Field(
        default=None, description="Descriptive status or diagnostic message."
    )
    metadata: ForecastMetadata = Field(description="Detailed forecast metadata and provenance.")
    predictions: list[PredictionPoint] = Field(
        default_factory=list, description="Ordered sequence of forecast points."
    )
    historical_points: list[PredictionPoint] = Field(
        default_factory=list,
        description="Historical observed data points leading up to the forecast origin.",
    )


# ── Benchmark & History Schemas ───────────────────────────────────────────────


class BenchmarkComparisonSummary(BaseModel):
    """Summary of model comparison and selection for a given slice."""

    dataset_name: str
    target_column: str
    horizon: int
    horizon_unit: str
    target_units: str
    selection_criterion: str
    winner: ModelEvaluationEntry | None
    leaderboard: list[ModelEvaluationEntry]


class BenchmarkReportResponse(BaseModel):
    """Response payload for GET /api/v1/forecast/benchmarks."""

    report_id: str
    generated_at: datetime
    total_runs_evaluated: int
    successful_runs: int
    failed_or_missing_runs: int
    comparisons: list[BenchmarkComparisonSummary]


class ExperimentRunSummary(BaseModel):
    """Compact summary of a saved experiment run."""

    run_id: str
    dataset_name: str
    target_column: str
    model_type: str
    config_name: str
    horizon: int
    status: str
    val_mae: float | None = None
    test_mae: float | None = None
    created_at: datetime
