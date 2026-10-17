from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.ml.contracts.evaluation import EvaluationMetrics


class ModelEvaluationEntry(BaseModel):
    """Evaluation result and ranking for an individual model configuration."""

    model_type: str = Field(description="Model family: baseline, arima, prophet, lstm")
    config_name: str = Field(description="Identifier for specific configuration or hyperparameters")
    status: Literal["SUCCESS", "FAILED", "MISSING"] = Field(
        default="SUCCESS", description="Execution and evaluation status"
    )
    error_message: str | None = Field(default=None, description="Failure reason if status != SUCCESS")

    val_metrics: EvaluationMetrics | None = Field(
        default=None, description="Validation split metrics (sole criterion for selection)"
    )
    test_metrics: EvaluationMetrics | None = Field(
        default=None, description="Held-out test split metrics (reported post-selection only)"
    )

    run_id: str | None = Field(default=None, description="Associated experiment run UUID if available")
    rank: int | None = Field(default=None, description="Leaderboard rank based strictly on validation score")


class SelectionComparison(BaseModel):
    """Comparative evaluation and model selection for a specific dataset, target, and horizon."""

    dataset_name: str = Field(description="Normalized dataset identifier (hero_dmc, nhsn_hrd)")
    target_column: str = Field(description="Target variable forecast")
    horizon: int = Field(description="Forecast horizon length")
    horizon_unit: str = Field(description="Time unit for horizon ('d' for days, 'w' for weeks)")
    target_units: str = Field(default="count", description="Physical unit (e.g. admissions, beds)")

    selection_criterion: str = Field(
        default="val_mae", description="Validation metric used to select winning model"
    )
    secondary_criterion: str = Field(
        default="val_rmse", description="Secondary validation metric used for tie-breaking"
    )

    winner: ModelEvaluationEntry | None = Field(
        default=None, description="Winning model chosen strictly on validation metrics"
    )
    leaderboard: list[ModelEvaluationEntry] = Field(
        default_factory=list, description="All evaluated and missing/failed model entries ordered by rank"
    )
    summary_notes: str = Field(
        default="", description="Operational notes or warnings about this forecast configuration"
    )


class BenchmarkSelectionReport(BaseModel):
    """Comprehensive benchmark evaluation and model selection summary across all datasets and horizons."""

    report_id: str = Field(description="Unique report identifier")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    comparisons: list[SelectionComparison] = Field(
        default_factory=list, description="List of horizon comparisons"
    )

    total_runs_evaluated: int = Field(default=0, description="Total run artifacts evaluated")
    successful_runs: int = Field(default=0, description="Total runs with complete validation metrics")
    failed_or_missing_runs: int = Field(default=0, description="Runs that failed or models with missing runs")
