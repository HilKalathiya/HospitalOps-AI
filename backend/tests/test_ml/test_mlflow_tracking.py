import mlflow
import numpy as np
import pandas as pd
import pytest

from app.ml.contracts.config import FeatureConfig, ForecastConfig, SplitConfig
from app.ml.contracts.dataset import MLDataset
from app.ml.contracts.evaluation import EvaluationMetrics
from app.ml.contracts.experiment import ExperimentRun
from app.ml.contracts.forecast import ForecastResult
from app.ml.pipelines.orchestrator import MLPipelineOrchestrator
from app.ml.tracking.artifacts import log_experiment_artifacts, sanitize_dict
from app.ml.tracking.factory import get_tracker
from app.ml.tracking.mlflow_tracker import MLflowTracker
from app.ml.tracking.null_tracker import NullExperimentTracker


@pytest.fixture
def sample_dataset() -> MLDataset:
    dates = pd.date_range("2025-01-01", periods=60, freq="D")
    df = pd.DataFrame(
        {
            "date": dates,
            "daily_admissions": np.linspace(10, 50, 60) + np.sin(np.arange(60)) * 5,
        }
    )
    return MLDataset(
        dataset_name="hero_dmc",
        source_collection="test",
        df=df,
        target_column="daily_admissions",
        time_column="date",
        frequency="D",
        metadata={},
    )


# ==============================================================================
# 1. NullTracker / Disabled Tracking Tests
# ==============================================================================


def test_null_tracker_graceful_no_op():
    """Verifies that NullExperimentTracker performs clean no-ops with zero side effects."""
    tracker = NullExperimentTracker()
    assert tracker.is_enabled is False
    assert tracker.active_run_id is None
    assert tracker.active_experiment_id is None

    with tracker.start_run(run_name="test_run", tags={"tag1": "v1"}):
        tracker.log_param("param1", "val1")
        tracker.log_params({"param2": 123})
        tracker.log_metric("metric1", 1.23)
        tracker.log_metrics({"metric2": 4.56})
        tracker.set_tag("tag2", "v2")
        tracker.set_tags({"tag3": "v3"})
        tracker.log_dict({"key": "value"}, "test.json")


def test_get_tracker_factory_resolution(monkeypatch):
    """Verifies factory resolves NullTracker when tracking is disabled."""
    tracker = get_tracker(force_null=True)
    assert isinstance(tracker, NullExperimentTracker)

    cfg_disabled = ForecastConfig(
        dataset_name="hero_dmc",
        target_column="daily_admissions",
        features=FeatureConfig(),
        split=SplitConfig(),
        tracking_enabled=False,
    )
    tracker_cfg = get_tracker(config=cfg_disabled)
    assert isinstance(tracker_cfg, NullExperimentTracker)


# ==============================================================================
# 2. MLflowTracker Parameters and Metrics Logging Tests
# ==============================================================================


def test_mlflow_tracker_param_and_metric_logging(tmp_path):
    """Verifies MLflowTracker logs parameters and metrics to a local SQLite store."""
    db_file = tmp_path / "mlflow_test.db"
    tracking_uri = f"sqlite:///{db_file}"
    tracker = MLflowTracker(tracking_uri=tracking_uri, experiment_name="test-params-metrics")

    assert tracker.is_enabled is True
    assert tracker.supports_model_registry() is True

    with tracker.start_run(run_name="param_test_run") as ctx:
        run_id = tracker.active_run_id
        assert run_id is not None
        assert ctx.run_id == run_id

        # Log params
        tracker.log_params(
            {
                "horizon": 7,
                "model_type": "baseline",
                "nested_setting": {"sub": 1},
                "long_param": "x" * 600,  # exceeds 500 chars limit
            }
        )

        # Log metrics with strict validation and test separation
        tracker.log_metrics(
            {
                "val_mae": 2.50,
                "val_rmse": 3.10,
                "val_mape": 12.5,
                "test_mae": 4.20,
                "test_rmse": 5.10,
                "test_mape": 20.0,
            }
        )

    # Inspect MLflow run directly via MLflow Client
    client = mlflow.tracking.MlflowClient(tracking_uri=tracking_uri)
    run_data = client.get_run(run_id).data

    assert run_data.params["horizon"] == "7"
    assert run_data.params["model_type"] == "baseline"
    assert len(run_data.params["long_param"]) <= 500
    assert run_data.params["long_param"].endswith("...")

    # Verify separate validation and test metrics
    assert run_data.metrics["val_mae"] == 2.50
    assert run_data.metrics["val_rmse"] == 3.10
    assert run_data.metrics["val_mape"] == 12.5
    assert run_data.metrics["test_mae"] == 4.20
    assert run_data.metrics["test_rmse"] == 5.10
    assert run_data.metrics["test_mape"] == 20.0


# ==============================================================================
# 3. Artifact Logging and Sanitization (No PHI / Credentials) Tests
# ==============================================================================


def test_sanitize_dict_removes_phi_and_secrets():
    """Verifies that PHI identifiers and secret keys are completely stripped from logged metadata."""
    payload = {
        "dataset_name": "hero_dmc",
        "horizon": 14,
        "patient_id": "123456",
        "subject_id": 9999,
        "mrn": "MRN-0012",
        "jwt_secret_key": "super-secret-token",
        "api_password": "mypassword",
        "nested": {
            "diagnosis": "pneumonia",
            "clinical_notes": "Patient admitted with fever",
            "safe_metric": 42.0,
        },
    }

    sanitized = sanitize_dict(payload)
    assert "dataset_name" in sanitized
    assert "horizon" in sanitized
    assert "patient_id" not in sanitized
    assert "subject_id" not in sanitized
    assert "mrn" not in sanitized
    assert "jwt_secret_key" not in sanitized
    assert "api_password" not in sanitized
    assert "diagnosis" not in sanitized["nested"]
    assert "clinical_notes" not in sanitized["nested"]
    assert sanitized["nested"]["safe_metric"] == 42.0


def test_log_experiment_artifacts_persists_config_and_predictions(tmp_path):
    """Verifies that log_experiment_artifacts creates and uploads config, summary, and predictions."""
    db_file = tmp_path / "artifacts_test.db"
    tracking_uri = f"sqlite:///{db_file}"
    tracker = MLflowTracker(tracking_uri=tracking_uri, experiment_name="test-artifacts")

    exp = ExperimentRun(
        run_id="exp-123",
        dataset_name="hero_dmc",
        config=ForecastConfig(
            dataset_name="hero_dmc",
            target_column="daily_admissions",
            features=FeatureConfig(),
            split=SplitConfig(),
            horizon=7,
        ),
        forecasts=[
            ForecastResult(
                dataset_name="hero_dmc",
                target="daily_admissions",
                model_name="naive",
                split_name="validation",
                horizon=7,
                metrics=EvaluationMetrics(mae=2.0, rmse=2.5, mape=10.0),
                forecast_timestamps=["2025-01-01", "2025-01-02"],
                predictions=[10.0, 12.0],
                actuals=[11.0, 11.5],
            ),
            ForecastResult(
                dataset_name="hero_dmc",
                target="daily_admissions",
                model_name="naive",
                split_name="test",
                horizon=7,
                metrics=EvaluationMetrics(mae=3.0, rmse=3.5, mape=15.0),
                forecast_timestamps=["2025-01-03", "2025-01-04"],
                predictions=[14.0, 15.0],
                actuals=[13.0, 16.0],
            ),
        ],
    )

    with tracker.start_run(run_name="artifact_run"):
        log_experiment_artifacts(tracker, exp)
        run_id = tracker.active_run_id

    client = mlflow.tracking.MlflowClient(tracking_uri=tracking_uri)
    artifacts = [a.path for a in client.list_artifacts(run_id)]
    assert "config.json" in artifacts
    assert "evaluation_summary.json" in artifacts
    assert "predictions" in artifacts


# ==============================================================================
# 4. Error Handling and Failed Run Status Tests
# ==============================================================================


def test_failed_run_records_failed_status_and_error_tag(tmp_path):
    """Verifies that unhandled exceptions within a run context record status FAILED and error tags."""
    db_file = tmp_path / "error_test.db"
    tracking_uri = f"sqlite:///{db_file}"
    tracker = MLflowTracker(tracking_uri=tracking_uri, experiment_name="test-errors")

    run_id = None
    with pytest.raises(RuntimeError, match="Synthetic simulation error"):
        with tracker.start_run(run_name="error_run"):
            run_id = tracker.active_run_id
            raise RuntimeError("Synthetic simulation error")

    client = mlflow.tracking.MlflowClient(tracking_uri=tracking_uri)
    run = client.get_run(run_id)
    assert run.info.status == "FAILED"
    assert "Synthetic simulation error" in run.data.tags["error"]


def test_misconfigured_tracking_backend_graceful_fallback(tmp_path):
    """Verifies that an unconnectable tracking backend degrades gracefully when raise_on_error is False."""
    # Invalid tracking URI scheme that immediately fails without network retry loops
    tracker = MLflowTracker(
        tracking_uri="unsupported_scheme://invalid_host/db",
        experiment_name="test-unreachable",
        raise_on_error=False,
    )
    assert tracker.is_enabled is False

    # Pipeline calls should succeed safely without crashing
    with tracker.start_run():
        tracker.log_param("k", "v")
        tracker.log_metric("m", 1.0)


# ==============================================================================
# 5. Model Registry Backend Capability Tests
# ==============================================================================


def test_model_registry_backend_support_detection(tmp_path):
    """Verifies that SQLite/Postgres backends support registry, while raw file store does not."""
    db_file = tmp_path / "reg.db"
    sqlite_tracker = MLflowTracker(tracking_uri=f"sqlite:///{db_file}", experiment_name="test-reg")
    assert sqlite_tracker.supports_model_registry() is True

    file_tracker = MLflowTracker(tracking_uri=f"file:{tmp_path / 'mlruns'}", experiment_name="test-file")
    assert file_tracker.supports_model_registry() is False

    # Attempting to register on unsupported file backend returns None with warning
    reg_res = file_tracker.register_model(model_uri="models:/test/1", name="test_model")
    assert reg_res is None


# ==============================================================================
# 6. End-to-End Orchestrator Integration Tests
# ==============================================================================


def test_orchestrator_integration_with_mlflow(sample_dataset, tmp_path):
    """Verifies MLPipelineOrchestrator logs end-to-end parameters, metrics, and artifacts to MLflow."""
    db_file = tmp_path / "orchestrator_mlflow.db"
    tracking_uri = f"sqlite:///{db_file}"
    tracker = MLflowTracker(tracking_uri=tracking_uri, experiment_name="hospitalops-orchestrator-test")

    config = ForecastConfig(
        dataset_name="hero_dmc",
        target_column="daily_admissions",
        features=FeatureConfig(lags=[1, 7], rolling_windows=[7]),
        split=SplitConfig(train_ratio=0.7, val_ratio=0.15, test_ratio=0.15),
        baseline_model_type="naive",
        horizon=1,
        tracking_enabled=True,
    )

    orchestrator = MLPipelineOrchestrator(config=config, tracker=tracker)
    exp = orchestrator.run(sample_dataset)

    assert exp.status == "COMPLETED"
    assert exp.mlflow_run_id is not None

    # Verify run data in MLflow
    client = mlflow.tracking.MlflowClient(tracking_uri=tracking_uri)
    run = client.get_run(exp.mlflow_run_id)

    assert run.info.status == "FINISHED"
    assert run.data.params["model_type"] == "baseline"
    assert run.data.params["baseline_model_type"] == "naive"
    assert run.data.params["horizon"] == "1"

    # Metrics
    assert "val_mae" in run.data.metrics
    assert "val_rmse" in run.data.metrics
    assert "val_mape" in run.data.metrics
    assert "test_mae" in run.data.metrics
    assert "test_rmse" in run.data.metrics
    assert "test_mape" in run.data.metrics

    # Artifacts
    artifacts = [a.path for a in client.list_artifacts(exp.mlflow_run_id)]
    assert "config.json" in artifacts
    assert "evaluation_summary.json" in artifacts
    assert "predictions" in artifacts


def test_orchestrator_identical_predictions_with_and_without_tracking(sample_dataset, tmp_path):
    """Ensures enabling or disabling tracking produces strictly identical numerical predictions."""
    config = ForecastConfig(
        dataset_name="hero_dmc",
        target_column="daily_admissions",
        features=FeatureConfig(lags=[1, 7], rolling_windows=[7]),
        split=SplitConfig(train_ratio=0.7, val_ratio=0.15, test_ratio=0.15),
        baseline_model_type="naive",
        horizon=1,
    )

    # 1. Without tracking (NullTracker)
    null_tracker = NullExperimentTracker()
    orch_null = MLPipelineOrchestrator(config=config, tracker=null_tracker)
    exp_null = orch_null.run(sample_dataset)

    # 2. With MLflow tracking
    db_file = tmp_path / "ident.db"
    mlflow_tracker = MLflowTracker(tracking_uri=f"sqlite:///{db_file}", experiment_name="test-ident")
    orch_mlflow = MLPipelineOrchestrator(config=config, tracker=mlflow_tracker)
    exp_mlflow = orch_mlflow.run(sample_dataset)

    # Assert exact match of predictions and metrics
    val_null = next(f for f in exp_null.forecasts if f.split_name == "validation")
    val_mlflow = next(f for f in exp_mlflow.forecasts if f.split_name == "validation")

    assert val_null.predictions == val_mlflow.predictions
    assert val_null.metrics.mae == val_mlflow.metrics.mae
    assert val_null.metrics.rmse == val_mlflow.metrics.rmse
    assert val_null.metrics.mape == val_mlflow.metrics.mape
