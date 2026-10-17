import numpy as np
import pandas as pd

from app.ml.contracts.config import FeatureConfig, ForecastConfig, SplitConfig
from app.ml.contracts.dataset import MLDataset
from app.ml.models.lstm import LSTMForecastModel
from app.ml.pipelines.orchestrator import MLPipelineOrchestrator


def _create_synthetic_series(n_samples: int = 120, freq: str = "D") -> pd.DataFrame:
    """Creates a deterministic synthetic time-series with trend and weekly seasonality."""
    dates = pd.date_range(start="2025-01-01", periods=n_samples, freq=freq)
    np.random.seed(42)
    t = np.arange(n_samples)
    trend = 0.1 * t
    seasonality = 10.0 * np.sin(2 * np.pi * t / 7.0)
    noise = np.random.normal(0, 1.0, n_samples)
    target = np.clip(50.0 + trend + seasonality + noise, a_min=10.0, a_max=None)

    df = pd.DataFrame(
        {
            "timestamp": dates,
            "admissions": target,
            "admissions_lag_1": np.roll(target, 1),
            "admissions_lag_7": np.roll(target, 7),
            "admissions_rolling_mean_7": pd.Series(target).rolling(7, min_periods=1).mean().values,
            "day_of_week": dates.dayofweek,
            "month": dates.month,
        }
    )
    return df


def test_lstm_model_fit_and_predict():
    """Validates LSTM model training, prediction output shape, non-negativity, and confidence bounds."""
    df = _create_synthetic_series(n_samples=100)
    train_df = df.iloc[:80].copy()
    test_df = df.iloc[80:87].copy()  # 7 steps

    model = LSTMForecastModel(
        target_column="admissions",
        horizon=7,
        sequence_length=10,
        hidden_dim=32,
        num_layers=1,
        dropout=0.1,
        epochs=10,
        batch_size=16,
        mc_samples=10,
        seed=42,
    )

    model.fit(train_df, train_df["admissions"])

    y_pred, y_lower, y_upper = model.predict(test_df)

    assert len(y_pred) == 7
    assert len(y_lower) == 7
    assert len(y_upper) == 7

    assert not y_pred.isna().any(), "Predictions should have no NaNs"
    assert not y_lower.isna().any(), "Lower bounds should have no NaNs"
    assert not y_upper.isna().any(), "Upper bounds should have no NaNs"

    assert (y_pred >= 0.0).all(), "Predictions must be non-negative"
    assert (y_lower >= 0.0).all(), "Lower bounds must be non-negative"

    # Lower bound must be <= upper bound
    assert (y_lower <= y_upper + 1e-4).all(), "Lower bound must be <= upper bound"


def test_lstm_sequence_creation_no_lookahead():
    """Verifies that sequence windows strictly preserve temporal causality."""
    model = LSTMForecastModel(target_column="y", horizon=3, sequence_length=5)

    features = np.arange(20).reshape(-1, 1).astype(np.float32)
    targets = np.arange(20).astype(np.float32) * 2.0

    X_seq, y_seq = model._create_sliding_windows(
        features=features, targets=targets, seq_len=5, horizon=3
    )

    # First sequence: features from 0..4, targets from 5..7
    assert np.array_equal(X_seq[0].flatten(), np.array([0, 1, 2, 3, 4]))
    assert np.array_equal(y_seq[0], np.array([10.0, 12.0, 14.0]))

    # Second sequence: features from 1..5, targets from 6..8
    assert np.array_equal(X_seq[1].flatten(), np.array([1, 2, 3, 4, 5]))
    assert np.array_equal(y_seq[1], np.array([12.0, 14.0, 16.0]))


def test_lstm_reproducibility():
    """Validates that fixed seed produces deterministic model training and output."""
    df = _create_synthetic_series(n_samples=80)
    train_df = df.iloc[:60].copy()
    test_df = df.iloc[60:64].copy()

    model1 = LSTMForecastModel(
        target_column="admissions",
        horizon=4,
        sequence_length=8,
        hidden_dim=16,
        epochs=5,
        seed=123,
        mc_samples=5,
    )
    model1.fit(train_df, train_df["admissions"])
    pred1, _, _ = model1.predict(test_df)

    model2 = LSTMForecastModel(
        target_column="admissions",
        horizon=4,
        sequence_length=8,
        hidden_dim=16,
        epochs=5,
        seed=123,
        mc_samples=5,
    )
    model2.fit(train_df, train_df["admissions"])
    pred2, _, _ = model2.predict(test_df)

    np.testing.assert_allclose(pred1.values, pred2.values, rtol=1e-4)


def test_lstm_small_dataset_adaptation():
    """Verifies that the model dynamically adjusts sequence length when data is small."""
    df = _create_synthetic_series(n_samples=18)
    train_df = df.iloc[:12].copy()
    test_df = df.iloc[12:14].copy()

    model = LSTMForecastModel(
        target_column="admissions",
        horizon=2,
        sequence_length=20,  # larger than train_df
        hidden_dim=16,
        epochs=3,
        seed=42,
    )
    # Should not raise ValueError
    model.fit(train_df, train_df["admissions"])
    y_pred, _, _ = model.predict(test_df)
    assert len(y_pred) == 2


def test_lstm_orchestrator_pipeline(tmp_path):
    """End-to-end integration test of MLPipelineOrchestrator with LSTM and Walk-Forward."""
    df = _create_synthetic_series(n_samples=100)
    dataset = MLDataset(
        dataset_name="synthetic_hospital",
        source_collection="synthetic",
        df=df,
        target_column="admissions",
        time_column="timestamp",
        frequency="D",
        metadata={},
    )

    config = ForecastConfig(
        dataset_name="synthetic_hospital",
        target_column="admissions",
        features=FeatureConfig(lags=[1, 7], rolling_windows=[7]),
        split=SplitConfig(train_ratio=0.7, val_ratio=0.15, test_ratio=0.15),
        model_type="lstm",
        horizon=2,
        walk_forward_origins=2,
        lstm_hidden_dim=16,
        lstm_num_layers=1,
        lstm_epochs=3,
        lstm_sequence_length=7,
        lstm_batch_size=16,
        lstm_mc_samples=5,
    )

    orchestrator = MLPipelineOrchestrator(
        config=config,
        artifacts_dir=str(tmp_path / "artifacts"),
        runs_dir=str(tmp_path / "runs"),
    )


    experiment = orchestrator.run(dataset)

    assert experiment.status == "COMPLETED"
    assert len(experiment.forecasts) == 2  # val and test

    val_res = next(f for f in experiment.forecasts if f.split_name == "validation")
    test_res = next(f for f in experiment.forecasts if f.split_name == "test")

    assert val_res.metrics.mae > 0.0
    assert val_res.metrics.rmse > 0.0
    assert test_res.metrics.mae > 0.0
    assert test_res.metrics.rmse > 0.0
