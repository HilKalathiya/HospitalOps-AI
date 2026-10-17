from typing import Any

from app.ml.tracking.base import ExperimentTracker, TrackerRunContext


class NullExperimentTracker(ExperimentTracker):
    """
    No-op experiment tracker used when tracking is disabled or MLflow is unavailable.
    Guarantees zero network overhead, zero file writes, and clean fallback.
    """

    def start_run(
        self,
        run_name: str | None = None,
        tags: dict[str, str] | None = None,
    ) -> TrackerRunContext:
        return TrackerRunContext(self, run_id=None)

    def log_param(self, key: str, value: Any) -> None:
        pass

    def log_params(self, params: dict[str, Any]) -> None:
        pass

    def log_metric(self, key: str, value: float, step: int | None = None) -> None:
        pass

    def log_metrics(self, metrics: dict[str, float], step: int | None = None) -> None:
        pass

    def log_artifact(self, local_path: str, artifact_path: str | None = None) -> None:
        pass

    def log_dict(self, dictionary: dict[str, Any], artifact_file: str) -> None:
        pass

    def set_tag(self, key: str, value: str) -> None:
        pass

    def set_tags(self, tags: dict[str, str]) -> None:
        pass

    def end_run(self, status: str = "FINISHED") -> None:
        pass

    @property
    def is_enabled(self) -> bool:
        return False

    @property
    def active_run_id(self) -> str | None:
        return None

    @property
    def active_experiment_id(self) -> str | None:
        return None
