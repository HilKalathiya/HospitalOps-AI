import pandas as pd

from app.ml.contracts.config import SplitConfig


class TemporalSplitter:
    """
    Splits a DataFrame strictly chronologically into Train, Validation, and Test sets.
    """

    def __init__(self, config: SplitConfig):
        self.config = config

    def split(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        total = len(df)
        if total == 0:
            return df.copy(), df.copy(), df.copy()

        train_end = int(total * self.config.train_ratio)
        val_end = train_end + int(total * self.config.val_ratio)

        train_df = df.iloc[:train_end].copy()
        val_df = df.iloc[train_end:val_end].copy()
        test_df = df.iloc[val_end:].copy()

        return train_df, val_df, test_df
