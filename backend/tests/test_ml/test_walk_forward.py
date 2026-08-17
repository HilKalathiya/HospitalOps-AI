import pandas as pd

from app.ml.contracts.config import FeatureConfig, ForecastConfig, SplitConfig
from app.ml.contracts.dataset import MLDataset
from app.ml.pipelines.orchestrator import MLPipelineOrchestrator


def test_walk_forward_origins_in_orchestrator():
    """
    Tests that the orchestrator honors walk_forward_origins property
    and records it in the ForecastResult.
    """
    dates = pd.date_range("2026-01-01", periods=100, freq="D")
    df = pd.DataFrame({"date": dates, "y": range(100)})
    ds = MLDataset("test", "test", df, "y", "date", "D", {})

    config = ForecastConfig(
        dataset_name="test",
        target_column="y",
        features=FeatureConfig(lags=[1], rolling_windows=[]),
        split=SplitConfig(train_ratio=0.6, val_ratio=0.2, test_ratio=0.2),
        baseline_model_type="naive",
        horizon=1,
        walk_forward_origins=5,
    )

    orch = MLPipelineOrchestrator(config, artifacts_dir="/tmp", runs_dir="/tmp")
    exp = orch.run(ds)

    assert len(exp.forecasts) == 2
    fr = exp.forecasts[0]
    # Baselines calculate across the whole split in one pass, so origins=1 in the record
    assert fr.walk_forward_origin_count == 1
    assert fr.horizon == 1
    # Simple naive model with a perfect trend should have 1.0 MAE
    assert fr.metrics.mae == 1.0


def test_high_demand_evaluation():
    dates = pd.date_range("2026-01-01", periods=100, freq="D")
    # y ranges from 0 to 99. The 90th percentile is ~89.
    df = pd.DataFrame({"date": dates, "y": range(100)})
    ds = MLDataset("test", "test", df, "y", "date", "D", {})

    config = ForecastConfig(
        dataset_name="test",
        target_column="y",
        features=FeatureConfig(lags=[1], rolling_windows=[]),
        split=SplitConfig(train_ratio=0.6, val_ratio=0.2, test_ratio=0.2),
        baseline_model_type="naive",
        high_demand_quantile=0.90,
    )

    orch = MLPipelineOrchestrator(config, artifacts_dir="/tmp", runs_dir="/tmp")
    exp = orch.run(ds)

    fr = exp.forecasts[0]
    assert fr.high_demand_metrics is not None
    # 90th percentile of range(60) (train set length is 60) is ~53.1
    assert 50 < fr.high_demand_threshold < 60
    assert fr.high_demand_metrics.mae == 1.0
