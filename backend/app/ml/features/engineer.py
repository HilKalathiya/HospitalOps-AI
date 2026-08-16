import pandas as pd

from app.ml.contracts.config import FeatureConfig
from app.ml.contracts.dataset import MLDataset


class FeatureEngineer:
    """
    Computes strict backward-looking features globally before splitting.
    Zero leakage is enforced by always applying .shift(1) to target before lagging or rolling.
    """

    def __init__(self, config: FeatureConfig, horizon: int = 1):
        self.config = config
        self.horizon = horizon

    def engineer_features(self, dataset: MLDataset) -> tuple[pd.DataFrame, list[str]]:
        """
        Returns the augmented dataframe and a list of generated feature columns.
        Modifies df in place but returns the new one.
        """
        df = dataset.df.copy()
        target = dataset.target_column
        time_col = dataset.time_column

        # Must ensure sorted
        df = df.sort_values(time_col).reset_index(drop=True)

        feature_cols = []

        # Calendar features
        if self.config.include_day_of_week:
            df["day_of_week"] = df[time_col].dt.dayofweek
            feature_cols.append("day_of_week")
        if self.config.include_month:
            df["month"] = df[time_col].dt.month
            feature_cols.append("month")
        if self.config.include_year:
            df["year"] = df[time_col].dt.year
            feature_cols.append("year")

        # target_shifted is what is available *before* time t (accounting for horizon).
        target_shifted = df[target].shift(self.horizon)

        # Lags
        for lag in self.config.lags:
            # lag=1 means we want target at t-1.
            # target_shifted is already t-1.
            # So a lag of L means target_shifted shifted by L-1.
            col_name = f"{target}_lag_{lag}"
            df[col_name] = target_shifted.shift(lag - 1)
            feature_cols.append(col_name)

        # Rolling Windows
        for window in self.config.rolling_windows:
            # rolling over target_shifted ensures no overlap with target(t)
            col_mean = f"{target}_rolling_mean_{window}"
            df[col_mean] = target_shifted.rolling(window=window, min_periods=1).mean()
            feature_cols.append(col_mean)

            col_std = f"{target}_rolling_std_{window}"
            df[col_std] = target_shifted.rolling(window=window, min_periods=1).std()
            feature_cols.append(col_std)

        # Drop rows that have NaNs due to shifting, but ONLY if we want to.
        # Actually, let's keep them and let the pipeline decide or fill with 0/mean.
        # However, for a strict ML pipeline, we drop the initial rows that can't be computed.
        # But wait, dropping here alters the global dataset length. We will do a forward fill
        # or fillna(0) for baseline, or just dropna.
        # We will dropna on the feature columns to ensure we only have valid training data.
        df = df.dropna(subset=feature_cols).reset_index(drop=True)

        return df, feature_cols
