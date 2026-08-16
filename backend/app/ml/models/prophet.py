import pandas as pd
from prophet import Prophet
import logging

from app.ml.contracts.model import ForecastModel


class ProphetForecastModel(ForecastModel):
    """
    Prophet statistical forecasting model.
    """

    def __init__(self, target_column: str, time_column: str, **prophet_kwargs):
        self.target_column = target_column
        self.time_column = time_column
        self.prophet_kwargs = prophet_kwargs
        self.model = None
        
        # Suppress Prophet's very noisy stdout logging
        logging.getLogger("prophet").setLevel(logging.ERROR)
        logging.getLogger("cmdstanpy").disabled = True

    def fit(self, X_train: pd.DataFrame, y_train: pd.Series) -> None:
        """
        Fits the Prophet model.
        Prophet requires a DataFrame with 'ds' and 'y' columns.
        """
        if self.time_column not in X_train.columns:
            raise ValueError(f"Time column '{self.time_column}' is missing from X_train.")
            
        df_prophet = pd.DataFrame({
            "ds": X_train[self.time_column],
            "y": y_train
        }).dropna()
        
        if len(df_prophet) == 0:
            raise ValueError("Training target series is empty.")
            
        # Extract controlled args, fallback to defaults
        kwargs = {}
        if "yearly_seasonality" in self.prophet_kwargs:
            kwargs["yearly_seasonality"] = self.prophet_kwargs["yearly_seasonality"]
        if "weekly_seasonality" in self.prophet_kwargs:
            kwargs["weekly_seasonality"] = self.prophet_kwargs["weekly_seasonality"]
        if "daily_seasonality" in self.prophet_kwargs:
            kwargs["daily_seasonality"] = self.prophet_kwargs["daily_seasonality"]
        if "changepoint_prior_scale" in self.prophet_kwargs:
            kwargs["changepoint_prior_scale"] = self.prophet_kwargs["changepoint_prior_scale"]

        self.model = Prophet(**kwargs)
        
        try:
            self.model.fit(df_prophet)
        except Exception as e:
            raise RuntimeError(f"Prophet fit failed: {e}")

    def predict(self, X: pd.DataFrame) -> pd.Series:
        """
        Predicts future values.
        Prophet needs a DataFrame with the 'ds' column representing future dates.
        """
        if self.model is None:
            raise ValueError("Prophet model is not fitted.")
            
        if len(X) == 0:
            return pd.Series([], index=X.index)
            
        if self.time_column not in X.columns:
            raise ValueError(f"Time column '{self.time_column}' is missing from X.")
            
        df_future = pd.DataFrame({"ds": X[self.time_column]})
        forecast = self.model.predict(df_future)
        
        return pd.Series(forecast["yhat"].values, index=X.index)
