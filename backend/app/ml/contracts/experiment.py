from datetime import UTC, datetime

from pydantic import BaseModel, Field

from app.ml.contracts.config import ForecastConfig
from app.ml.contracts.forecast import ForecastResult


class ExperimentRun(BaseModel):
    """Tracks metadata and artifacts for an ML experiment run."""

    run_id: str
    dataset_name: str
    pipeline_version: str = Field(default="1.0.0")
    config: ForecastConfig

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Forecast Results
    forecasts: list[ForecastResult] = Field(default_factory=list)

    # Dataset statistics
    total_rows: int = 0
    train_rows: int = 0
    val_rows: int = 0
    test_rows: int = 0
    feature_count: int = 0

    artifact_dir: str = ""
    status: str = Field(default="RUNNING")

    # MLflow Tracking Linkage (Chunk 2.6)
    mlflow_run_id: str | None = Field(default=None, description="Linked MLflow run ID if tracked")
    mlflow_experiment_id: str | None = Field(default=None, description="Linked MLflow experiment ID")
