import pandas as pd
from sklearn.preprocessing import StandardScaler


class DataPreprocessor:
    """
    Handles scaling of feature columns.
    Ensures that fit() is ONLY called on training data.
    """

    def __init__(self, feature_cols: list[str]):
        self.feature_cols = feature_cols
        self.scaler = StandardScaler()
        self.is_fitted = False

    def fit(self, X_train: pd.DataFrame) -> None:
        if not self.feature_cols:
            self.is_fitted = True
            return
        self.scaler.fit(X_train[self.feature_cols])
        self.is_fitted = True

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        if not self.is_fitted:
            raise ValueError("Preprocessor must be fitted before transform.")

        X_trans = X.copy()
        if not self.feature_cols:
            return X_trans

        X_trans[self.feature_cols] = self.scaler.transform(X[self.feature_cols])
        return X_trans

    def fit_transform(self, X_train: pd.DataFrame) -> pd.DataFrame:
        self.fit(X_train)
        return self.transform(X_train)
