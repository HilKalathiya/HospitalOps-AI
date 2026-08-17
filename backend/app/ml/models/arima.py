import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

from app.ml.contracts.model import ForecastModel


class ARIMAForecastModel(ForecastModel):
    """
    ARIMA / SARIMAX statistical model.
    """

    def __init__(
        self, target_column: str, order: tuple = (1, 0, 0), seasonal_order: tuple = (0, 0, 0, 0)
    ):
        self.target_column = target_column
        self.order = order
        self.seasonal_order = seasonal_order
        self.model_fit = None

    def fit(self, X_train: pd.DataFrame, y_train: pd.Series) -> None:
        """
        Fits the SARIMAX model.
        We use the endogenous target sequence.
        """
        # Ensure y_train is float and drop any NaNs from the beginning
        endog = y_train.dropna().astype(float)

        if len(endog) == 0:
            raise ValueError("Training target series is empty.")

        model = SARIMAX(
            endog=endog.values,
            order=self.order,
            seasonal_order=self.seasonal_order,
            enforce_stationarity=False,
            enforce_invertibility=False,
        )
        # Using a context manager to suppress warnings could be done,
        # but statsmodels generally prints to stdout. We allow warnings to pass.
        # Fit with disp=False to avoid excessive stdout
        try:
            self.model_fit = model.fit(disp=False)
        except Exception as e:
            raise RuntimeError(
                f"ARIMA fit failed for order {self.order}, seasonal_order {self.seasonal_order}: {e}"
            )

    def predict(self, X: pd.DataFrame) -> tuple[pd.Series, pd.Series | None, pd.Series | None]:
        """
        Since ARIMA predicts sequentially from the end of the training data,
        it requires `steps` = len(X).
        The input DataFrame X determines the horizon (number of rows).
        """
        if self.model_fit is None:
            raise ValueError("ARIMA model is not fitted.")

        steps = len(X)
        if steps == 0:
            return pd.Series([], index=X.index), None, None

        # Forecast with confidence intervals
        forecast_res = self.model_fit.get_forecast(steps=steps)
        forecast_values = forecast_res.predicted_mean
        conf_int = forecast_res.conf_int(alpha=0.05)  # 95% CI

        # forecast_values might be a Series or ndarray
        fv = forecast_values.values if hasattr(forecast_values, "values") else forecast_values
        y_pred = pd.Series(fv, index=X.index)

        y_lower = pd.Series(
            conf_int.iloc[:, 0].values if hasattr(conf_int, "iloc") else conf_int[:, 0],
            index=X.index,
        )
        y_upper = pd.Series(
            conf_int.iloc[:, 1].values if hasattr(conf_int, "iloc") else conf_int[:, 1],
            index=X.index,
        )

        return y_pred, y_lower, y_upper
