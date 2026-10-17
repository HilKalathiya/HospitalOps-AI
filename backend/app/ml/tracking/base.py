from abc import ABC, abstractmethod
from types import TracebackType
from typing import Any


class TrackerRunContext:
    """Context manager for managing tracking run lifecycle."""

    def __init__(self, tracker: "ExperimentTracker", run_id: str | None = None):
        self.tracker = tracker
        self.run_id = run_id

    def __enter__(self) -> "TrackerRunContext":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            self.tracker.set_tag("error", str(exc_val))
            self.tracker.end_run(status="FAILED")
        else:
            self.tracker.end_run(status="FINISHED")


class ExperimentTracker(ABC):
    """
    Abstract interface for experiment tracking systems (e.g. MLflow, NullTracker).
    Decouples the forecasting engine from concrete tracking SDKs.
    """

    @abstractmethod
    def start_run(
        self,
        run_name: str | None = None,
        tags: dict[str, str] | None = None,
    ) -> TrackerRunContext:
        """Starts a new experiment tracking run."""
        pass

    @abstractmethod
    def log_param(self, key: str, value: Any) -> None:
        """Logs a single hyperparameter or configuration value."""
        pass

    @abstractmethod
    def log_params(self, params: dict[str, Any]) -> None:
        """Logs a batch of hyperparameters or configuration values."""
        pass

    @abstractmethod
    def log_metric(self, key: str, value: float, step: int | None = None) -> None:
        """Logs a single scalar metric value."""
        pass

    @abstractmethod
    def log_metrics(self, metrics: dict[str, float], step: int | None = None) -> None:
        """Logs a batch of scalar metric values."""
        pass

    @abstractmethod
    def log_artifact(self, local_path: str, artifact_path: str | None = None) -> None:
        """Logs a local file as an experiment artifact."""
        pass

    @abstractmethod
    def log_dict(self, dictionary: dict[str, Any], artifact_file: str) -> None:
        """Logs a dictionary as a JSON artifact."""
        pass

    @abstractmethod
    def set_tag(self, key: str, value: str) -> None:
        """Sets a metadata tag on the active run."""
        pass

    @abstractmethod
    def set_tags(self, tags: dict[str, str]) -> None:
        """Sets multiple metadata tags on the active run."""
        pass

    @abstractmethod
    def end_run(self, status: str = "FINISHED") -> None:
        """Ends the active run with the given status."""
        pass

    @property
    @abstractmethod
    def is_enabled(self) -> bool:
        """Whether tracking is active."""
        pass

    @property
    @abstractmethod
    def active_run_id(self) -> str | None:
        """Returns the ID of the currently active run, if any."""
        pass

    @property
    @abstractmethod
    def active_experiment_id(self) -> str | None:
        """Returns the ID of the active experiment, if any."""
        pass
