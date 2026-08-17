import pandas as pd
import pytest

from app.ml.models.arima import ARIMAForecastModel


def test_arima_fit_predict():
    """
    Tests that ARIMAForecastModel can fit a small series and predict the requested steps.
    """
    # Create a small random series
    dates = pd.date_range("2026-01-01", periods=20, freq="D")
    y = pd.Series([i + (i % 2) for i in range(20)])

    # Simple ARIMA order
    model = ARIMAForecastModel(target_column="y", order=(1, 0, 0))

    # Fit
    X_train = pd.DataFrame({"ds": dates})
    model.fit(X_train, y)

    assert model.model_fit is not None

    # Predict next 3 steps
    future_dates = pd.date_range("2026-01-21", periods=3, freq="D")
    X_test = pd.DataFrame({"ds": future_dates})
    X_test.index = [20, 21, 22]

    preds, lower, upper = model.predict(X_test)

    assert len(preds) == 3
    assert list(preds.index) == [20, 21, 22]


def test_arima_fit_empty_raises():
    model = ARIMAForecastModel(target_column="y", order=(1, 0, 0))
    X_train = pd.DataFrame({"ds": []})
    y = pd.Series([], dtype=float)

    with pytest.raises(ValueError):
        model.fit(X_train, y)
