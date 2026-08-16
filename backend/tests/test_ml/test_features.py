import pandas as pd

from app.ml.contracts.config import FeatureConfig
from app.ml.contracts.dataset import MLDataset
from app.ml.features.engineer import FeatureEngineer


def test_feature_engineer_lags():
    dates = pd.date_range("2026-01-01", periods=5, freq="D")
    df = pd.DataFrame({"date": dates, "y": [10, 20, 30, 40, 50]})
    ds = MLDataset("test", "test", df, "y", "date", "D", {})

    config = FeatureConfig(lags=[1])
    engineer = FeatureEngineer(config)

    res, cols = engineer.engineer_features(ds)

    assert "y_lag_1" in cols
    # Original: [10, 20, 30, 40, 50]
    # Shifted:  [NaN, 10, 20, 30, 40]
    # Dropna removes the first row.
    assert len(res) == 4
    assert res.iloc[0]["y"] == 20
    assert res.iloc[0]["y_lag_1"] == 10.0
