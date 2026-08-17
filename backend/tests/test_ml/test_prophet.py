import pandas as pd
import pytest

from app.ml.models.prophet import ProphetForecastModel


@pytest.mark.skip(reason="Prophet cmdstan installation failed on this environment")
def test_prophet_fit_predict():
    """
    Tests that ProphetForecastModel can fit a small series and predict the requested steps.
    """
    dates = pd.date_range("2026-01-01", periods=30, freq="D")
    y = pd.Series([i for i in range(30)])

    model = ProphetForecastModel(
        target_column="y",
        time_column="ds",
        yearly_seasonality=False,
        weekly_seasonality=False,
        daily_seasonality=False,
    )

    X_train = pd.DataFrame({"ds": dates})
    model.fit(X_train, y)

    assert model.model is not None

    future_dates = pd.date_range("2026-01-31", periods=3, freq="D")
    X_test = pd.DataFrame({"ds": future_dates})
    X_test.index = [30, 31, 32]

    preds, lower, upper = model.predict(X_test)

    assert len(preds) == 3
    assert list(preds.index) == [30, 31, 32]


def test_prophet_missing_time_column():
    model = ProphetForecastModel(target_column="y", time_column="ds")
    X_train = pd.DataFrame({"not_ds": ["2026-01-01"]})
    y = pd.Series([10])

    with pytest.raises(ValueError):
        model.fit(X_train, y)
