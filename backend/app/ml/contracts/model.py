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
    def predict(self, X: pd.DataFrame) -> pd.Series:
        """Predict the target for the given features."""
        pass
