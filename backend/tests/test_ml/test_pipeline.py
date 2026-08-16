import pandas as pd

from app.ml.contracts.config import FeatureConfig, ForecastConfig, SplitConfig
from app.ml.contracts.dataset import MLDataset
from app.ml.pipelines.orchestrator import MLPipelineOrchestrator


def test_pipeline_orchestrator_naive():
    dates = pd.date_range("2026-01-01", periods=100, freq="D")
    df = pd.DataFrame({"date": dates, "y": range(100)})
    ds = MLDataset("test", "test", df, "y", "date", "D", {})

    config = ForecastConfig(
        dataset_name="test",
        target_column="y",
        features=FeatureConfig(lags=[1], rolling_windows=[]),
        split=SplitConfig(train_ratio=0.6, val_ratio=0.2, test_ratio=0.2),
        baseline_model_type="naive",
    )

    orchestrator = MLPipelineOrchestrator(config, artifacts_dir="/tmp", runs_dir="/tmp")
    experiment = orchestrator.run(ds)

    assert experiment.status == "COMPLETED"
    assert experiment.train_rows > 0
    assert experiment.val_rows > 0
    assert experiment.test_rows > 0

    fr = experiment.forecasts[0]
    assert fr.model_name == "naive"
    assert fr.horizon == 1

    # In a naive model predicting a simple linear trend [0,1,2,3...],
    # y(t) = y(t-1) => pred is t-1, actual is t. MAE should be 1.0.
    assert fr.metrics.mae == 1.0
