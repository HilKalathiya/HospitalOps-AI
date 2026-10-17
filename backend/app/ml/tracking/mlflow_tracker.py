import logging
import math
import os
from pathlib import Path
from typing import Any

from app.ml.tracking.base import ExperimentTracker, TrackerRunContext

logger = logging.getLogger(__name__)

# Lazy import MLflow so the module can be imported even if MLflow has issues
try:
    import mlflow
    from mlflow.exceptions import MlflowException
    MLFLOW_AVAILABLE = True
except ImportError:
    mlflow = None  # type: ignore
    MlflowException = Exception  # type: ignore
    MLFLOW_AVAILABLE = False


class MLflowTracker(ExperimentTracker):
    """
    MLflow implementation of the ExperimentTracker interface.

    Supports:
    - Experiment and run lifecycle management.
    - Parameter, metric, and artifact logging.
    - Validation and test metric isolation.
    - Local SQLite backend (with Model Registry support) or file store.
    - Graceful error recovery if the tracking server is unreachable.
    """

    def __init__(
        self,
        tracking_uri: str = "sqlite:///backend/ml/mlflow.db",
        experiment_name: str = "hospitalops-forecasting",
        artifact_location: str | None = None,
        raise_on_error: bool = False,
    ):
        self.tracking_uri = tracking_uri
        self.experiment_name = experiment_name
        self.artifact_location = artifact_location
        self.raise_on_error = raise_on_error

        self._active_run: Any = None
        self._experiment_id: str | None = None
        self._is_initialized = False
        self._healthy = True

        self._initialize()

    def _initialize(self) -> None:
        if not MLFLOW_AVAILABLE:
            self._healthy = False
            logger.warning("MLflow library is not installed. MLflowTracker will operate in degraded mode.")
            return

        try:
            # If tracking_uri is SQLite, ensure directory exists
            if self.tracking_uri.startswith("sqlite:///"):
                db_path = self.tracking_uri.replace("sqlite:///", "")
                # If relative path, ensure parent exists
                p = Path(db_path)
                p.parent.mkdir(parents=True, exist_ok=True)
            elif self.tracking_uri.startswith("file:"):
                dir_path = self.tracking_uri.replace("file:", "")
                p = Path(dir_path)
                p.mkdir(parents=True, exist_ok=True)

            mlflow.set_tracking_uri(self.tracking_uri)

            # Set or create experiment
            exp = mlflow.get_experiment_by_name(self.experiment_name)
            if exp is None:
                self._experiment_id = mlflow.create_experiment(
                    name=self.experiment_name,
                    artifact_location=self.artifact_location,
                )
            else:
                self._experiment_id = exp.experiment_id

            mlflow.set_experiment(self.experiment_name)
            self._is_initialized = True
            self._healthy = True
            logger.info(
                "MLflow tracking initialized: URI=%s, Experiment=%s (ID=%s)",
                self.tracking_uri,
                self.experiment_name,
                self._experiment_id,
            )
        except Exception as e:
            self._healthy = False
            logger.warning("Failed to initialize MLflow tracking backend (%s): %s", self.tracking_uri, e)
            if self.raise_on_error:
                raise

    @property
    def is_enabled(self) -> bool:
        return self._is_initialized and self._healthy

    @property
    def active_run_id(self) -> str | None:
        if self._active_run is not None:
            return self._active_run.info.run_id
        return None

    @property
    def active_experiment_id(self) -> str | None:
        return self._experiment_id

    def supports_model_registry(self) -> bool:
        """
        MLflow requires a database backend (e.g. SQLite, PostgreSQL, MySQL) to support
        the Model Registry. File-based backends ('file://') do NOT support model registration.
        """
        uri = self.tracking_uri.lower()
        return uri.startswith(("sqlite:", "postgresql:", "mysql:", "mssql:"))

    def start_run(
        self,
        run_name: str | None = None,
        tags: dict[str, str] | None = None,
    ) -> TrackerRunContext:
        if not self.is_enabled:
            return TrackerRunContext(self, run_id=None)

        try:
            # End any existing run
            if mlflow.active_run() is not None:
                mlflow.end_run()

            run = mlflow.start_run(
                run_name=run_name,
                tags=tags,
                nested=True,
            )
            self._active_run = run
            return TrackerRunContext(self, run_id=run.info.run_id)
        except Exception as e:
            logger.warning("Failed to start MLflow run: %s", e)
            if self.raise_on_error:
                raise
            return TrackerRunContext(self, run_id=None)

    def log_param(self, key: str, value: Any) -> None:
        self.log_params({key: value})

    def log_params(self, params: dict[str, Any]) -> None:
        if not self.is_enabled or self._active_run is None:
            return

        cleaned_params = {}
        for k, v in params.items():
            if v is None:
                continue
            if isinstance(v, int | float | str | bool):
                str_val = str(v)
            else:
                str_val = str(v)
            # MLflow parameter value length limit is 500 chars
            if len(str_val) > 500:
                str_val = str_val[:497] + "..."
            cleaned_params[k] = str_val

        if not cleaned_params:
            return

        try:
            mlflow.log_params(cleaned_params)
        except Exception as e:
            logger.warning("Error logging parameters to MLflow: %s", e)
            if self.raise_on_error:
                raise

    def log_metric(self, key: str, value: float, step: int | None = None) -> None:
        self.log_metrics({key: value}, step=step)

    def log_metrics(self, metrics: dict[str, float], step: int | None = None) -> None:
        if not self.is_enabled or self._active_run is None:
            return

        valid_metrics = {}
        for k, v in metrics.items():
            if v is not None and not (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
                try:
                    valid_metrics[k] = float(v)
                except (ValueError, TypeError):
                    continue

        if not valid_metrics:
            return

        try:
            mlflow.log_metrics(valid_metrics, step=step)
        except Exception as e:
            logger.warning("Error logging metrics to MLflow: %s", e)
            if self.raise_on_error:
                raise

    def log_artifact(self, local_path: str, artifact_path: str | None = None) -> None:
        if not self.is_enabled or self._active_run is None:
            return

        if not os.path.exists(local_path):
            logger.warning("Artifact path %s does not exist. Skipping.", local_path)
            return

        try:
            mlflow.log_artifact(local_path, artifact_path=artifact_path)
        except Exception as e:
            logger.warning("Error logging artifact %s to MLflow: %s", local_path, e)
            if self.raise_on_error:
                raise

    def log_dict(self, dictionary: dict[str, Any], artifact_file: str) -> None:
        if not self.is_enabled or self._active_run is None:
            return

        try:
            mlflow.log_dict(dictionary, artifact_file)
        except Exception as e:
            logger.warning("Error logging dict artifact %s to MLflow: %s", artifact_file, e)
            if self.raise_on_error:
                raise

    def set_tag(self, key: str, value: str) -> None:
        self.set_tags({key: value})

    def set_tags(self, tags: dict[str, str]) -> None:
        if not self.is_enabled or self._active_run is None:
            return

        try:
            mlflow.set_tags(tags)
        except Exception as e:
            logger.warning("Error setting tags in MLflow: %s", e)
            if self.raise_on_error:
                raise

    def end_run(self, status: str = "FINISHED") -> None:
        if not self.is_enabled or self._active_run is None:
            return

        try:
            mlflow.end_run(status=status)
        except Exception as e:
            logger.warning("Error ending MLflow run: %s", e)
            if self.raise_on_error:
                raise
        finally:
            self._active_run = None

    def register_model(
        self,
        model_uri: str,
        name: str,
        tags: dict[str, str] | None = None,
    ) -> Any:
        """
        Registers a logged model to the MLflow Model Registry if supported by the backend.
        Returns the registered model version or None if unsupported or failed.
        """
        if not self.is_enabled:
            return None

        if not self.supports_model_registry():
            logger.warning(
                "Configured tracking backend '%s' does not support Model Registry. "
                "A database backend (e.g. SQLite, PostgreSQL) is required for model registry features.",
                self.tracking_uri,
            )
            return None

        try:
            reg_model = mlflow.register_model(model_uri=model_uri, name=name, tags=tags)
            logger.info("Successfully registered model '%s' version %s", name, reg_model.version)
            return reg_model
        except Exception as e:
            logger.warning("Failed to register model '%s' in MLflow: %s", name, e)
            if self.raise_on_error:
                raise
            return None
