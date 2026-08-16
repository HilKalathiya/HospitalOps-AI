import pandas as pd
import pytest

from app.ml.models.baseline import (
    MovingAverageBaselineModel,
    NaiveBaselineModel,
    SeasonalNaiveBaselineModel,
)


def test_naive_baseline():
    model = NaiveBaselineModel(target_column="y", lag_column="y_lag_1")
    X = pd.DataFrame({"y_lag_1": [10, 20, 30]})
    preds = model.predict(X)
    assert list(preds) == [10, 20, 30]


def test_seasonal_naive_baseline():
    model = SeasonalNaiveBaselineModel(target_column="y", seasonal_lag_column="y_lag_7")
    X = pd.DataFrame({"y_lag_7": [1, 2, 3]})
    preds = model.predict(X)
    assert list(preds) == [1, 2, 3]


def test_moving_average_baseline():
    model = MovingAverageBaselineModel(target_column="y", rolling_mean_column="y_roll_7")
    X = pd.DataFrame({"y_roll_7": [15.5, 16.0]})
    preds = model.predict(X)
    assert list(preds) == [15.5, 16.0]


def test_missing_feature_raises_error():
    model = NaiveBaselineModel(target_column="y", lag_column="y_lag_2")
    X = pd.DataFrame({"y_lag_1": [10]})
    with pytest.raises(ValueError):
        model.predict(X)
