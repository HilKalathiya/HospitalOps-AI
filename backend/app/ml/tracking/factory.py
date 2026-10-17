from app.core.config import get_settings
from app.ml.contracts.config import ForecastConfig
from app.ml.tracking.base import ExperimentTracker
from app.ml.tracking.mlflow_tracker import MLflowTracker
from app.ml.tracking.null_tracker import NullExperimentTracker


def get_tracker(
    config: ForecastConfig | None = None,
    tracking_uri: str | None = None,
    experiment_name: str | None = None,
    force_null: bool = False,
) -> ExperimentTracker:
    """
    Factory to retrieve an appropriate ExperimentTracker.

    Priority for enabled status:
    1. force_null -> NullExperimentTracker
    2. config.tracking_enabled (if explicitly boolean)
    3. settings.mlflow_tracking_enabled
    """
    if force_null:
        return NullExperimentTracker()

    settings = get_settings()

    enabled = settings.mlflow_tracking_enabled
    if config is not None and config.tracking_enabled is not None:
        enabled = config.tracking_enabled

    if not enabled:
        return NullExperimentTracker()

    uri = tracking_uri or settings.mlflow_tracking_uri
    exp_name = (
        experiment_name
        or (config.tracking_experiment_name if config else None)
        or settings.mlflow_experiment_name
    )

    return MLflowTracker(tracking_uri=uri, experiment_name=exp_name)
