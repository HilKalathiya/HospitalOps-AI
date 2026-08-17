from abc import ABC, abstractmethod

import pandas as pd


class ForecastModel(ABC):
    """
    Abstract interface for forecasting models.
    """

    @abstractmethod
    def fit(self, X_train: pd.DataFrame, y_train: pd.Series) -> None:
        """Fit the model to the training data."""
        pass

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> tuple[pd.Series, pd.Series | None, pd.Series | None]:
        """Predict the target. Returns (y_pred, y_lower, y_upper)."""
        pass
