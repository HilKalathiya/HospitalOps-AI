from datetime import datetime

from pydantic import BaseModel, Field

from app.ml.contracts.evaluation import EvaluationMetrics


class ForecastResult(BaseModel):
    """Contract for a generated forecast and its evaluation."""

    dataset_name: str
    target: str
    model_name: str
    split_name: str = "test"
    horizon: int

    # Core Evaluation
    metrics: EvaluationMetrics

    # High-demand / High-occupancy Evaluation
    high_demand_metrics: EvaluationMetrics | None = None
    high_demand_threshold: float | None = None

    # Raw predictions for analysis (Optional, could be large)
    forecast_timestamps: list[str] = Field(default_factory=list)
    predictions: list[float] = Field(default_factory=list)
    actuals: list[float] = Field(default_factory=list)

    # Walk-forward metadata
    walk_forward_origin_count: int = 1

    pipeline_version: str = "1.0.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)
