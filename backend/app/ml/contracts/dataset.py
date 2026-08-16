from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd


@dataclass
class MLDataset:
    """
    Standardized internal representation of a time-series dataset for ML.
    """

    dataset_name: str
    source_collection: str
    df: pd.DataFrame
    target_column: str
    time_column: str
    frequency: str  # e.g., 'D' for daily, 'W' for weekly

    metadata: dict[str, Any]

    @property
    def row_count(self) -> int:
        return len(self.df)

    @property
    def date_range(self) -> tuple[datetime, datetime]:
        if self.df.empty:
            return (datetime.min, datetime.min)
        return (
            self.df[self.time_column].min().to_pydatetime(),
            self.df[self.time_column].max().to_pydatetime(),
        )
