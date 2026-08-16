import pandas as pd

from app.data_ingestion.repositories import HistoricalAdmissionsRepository
from app.ml.adapters.base import BaseAdapter
from app.ml.contracts.dataset import MLDataset


class HeroDMCAdapter(BaseAdapter):
    """
    Adapter for Hero DMC Historical Admissions.
    Produces a daily time series of total admissions.
    """

    def __init__(self, repository: HistoricalAdmissionsRepository):
        self.repository = repository

    async def fetch_dataset(self) -> MLDataset:
        # Fetch all documents
        cursor = self.repository.collection.find({"admission_date": {"$ne": None}})
        docs = await cursor.to_list(length=None)

        if not docs:
            # Return empty dataset if no data
            df = pd.DataFrame(columns=["date", "daily_admissions"])
            return MLDataset(
                dataset_name="hero_dmc",
                source_collection="historical_admissions",
                df=df,
                target_column="daily_admissions",
                time_column="date",
                frequency="D",
                metadata={"total_source_records": 0},
            )

        # Convert to DataFrame
        df_raw = pd.DataFrame(docs)

        # Ensure datetime and drop timezone for aggregation
        df_raw["admission_date"] = (
            pd.to_datetime(df_raw["admission_date"]).dt.tz_localize(None).dt.normalize()
        )

        # Group by date and count admissions
        df_daily = df_raw.groupby("admission_date").size().reset_index(name="daily_admissions")
        df_daily = df_daily.rename(columns={"admission_date": "date"})

        # Sort chronologically
        df_daily = df_daily.sort_values("date").reset_index(drop=True)

        # Reindex to fill missing dates with 0 (since no admissions = 0)
        min_date = df_daily["date"].min()
        max_date = df_daily["date"].max()
        all_dates = pd.date_range(start=min_date, end=max_date, freq="D")

        df_daily = df_daily.set_index("date").reindex(all_dates, fill_value=0).reset_index()
        df_daily = df_daily.rename(columns={"index": "date"})

        return MLDataset(
            dataset_name="hero_dmc",
            source_collection="historical_admissions",
            df=df_daily,
            target_column="daily_admissions",
            time_column="date",
            frequency="D",
            metadata={"total_source_records": len(docs)},
        )
