import pandas as pd

from app.data_ingestion.repositories import HistoricalHospitalCapacityRepository
from app.ml.adapters.base import BaseAdapter
from app.ml.contracts.dataset import MLDataset


class NHSNAdapter(BaseAdapter):
    """
    Adapter for NHSN Historical Hospital Capacity.
    Produces a weekly time series of capacity metrics.
    """

    def __init__(
        self,
        repository: HistoricalHospitalCapacityRepository,
        target_column: str = "icu_beds_occupied",
    ):
        self.repository = repository
        self.target_column = target_column

    async def fetch_dataset(self) -> MLDataset:
        # Fetch documents
        cursor = self.repository.collection.find({"week_ending_date": {"$ne": None}})
        docs = await cursor.to_list(length=None)

        if not docs:
            df = pd.DataFrame(columns=["week_ending_date", self.target_column])
            return MLDataset(
                dataset_name="nhsn_hrd",
                source_collection="historical_hospital_capacity",
                df=df,
                target_column=self.target_column,
                time_column="week_ending_date",
                frequency="W",
                metadata={"total_source_records": 0},
            )

        df_raw = pd.DataFrame(docs)

        # Normalize dates
        df_raw["week_ending_date"] = (
            pd.to_datetime(df_raw["week_ending_date"]).dt.tz_localize(None).dt.normalize()
        )

        # In a real scenario we might filter by geographic_aggregation.
        # For simplicity, if there are multiple geographies, we group and sum.
        numeric_cols = df_raw.select_dtypes(include=["number"]).columns.tolist()
        df_weekly = df_raw.groupby("week_ending_date")[numeric_cols].sum(min_count=1).reset_index()

        # Ensure target column exists
        if self.target_column not in df_weekly.columns:
            df_weekly[self.target_column] = None

        # Sort chronologically
        df_weekly = df_weekly.sort_values("week_ending_date").reset_index(drop=True)

        # Missing strategy: NHSN missing target doesn't mean 0. Forward fill is risky, but dropping destroys time-series.
        # We will keep NaNs and let the feature engineering/pipeline handle or complain about it,
        # but we reindex to ensure contiguous weeks.
        min_date = df_weekly["week_ending_date"].min()
        max_date = df_weekly["week_ending_date"].max()
        all_weeks = pd.date_range(
            start=min_date, end=max_date, freq="W-SAT"
        )  # NHSN usually ends on Saturday

        df_weekly = df_weekly.set_index("week_ending_date").reindex(all_weeks).reset_index()
        df_weekly = df_weekly.rename(columns={"index": "week_ending_date"})

        return MLDataset(
            dataset_name="nhsn_hrd",
            source_collection="historical_hospital_capacity",
            df=df_weekly,
            target_column=self.target_column,
            time_column="week_ending_date",
            frequency="W",
            metadata={"total_source_records": len(docs)},
        )
