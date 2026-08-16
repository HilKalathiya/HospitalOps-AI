import asyncio

import pandas as pd

from app.ml.contracts.config import FeatureConfig, ForecastConfig, SplitConfig
from app.ml.contracts.dataset import MLDataset
from app.ml.pipelines.orchestrator import MLPipelineOrchestrator


def mock_hero_dataset():
    dates = pd.date_range("2021-01-01", periods=1000, freq="D")
    # Simulate some varying admissions
    admissions = [50 + (i % 7) * 5 + (i % 30) for i in range(1000)]
    df = pd.DataFrame({"date": dates, "daily_admissions": admissions})
    return MLDataset(
        dataset_name="hero_dmc",
        source_collection="historical_admissions",
        df=df,
        target_column="daily_admissions",
        time_column="date",
        frequency="D",
        metadata={"total_source_records": 1000},
    )


def mock_nhsn_dataset():
    dates = pd.date_range("2021-01-01", periods=150, freq="W-SAT")
    occupancy = [100 + (i % 4) * 10 + (i % 52) for i in range(150)]
    df = pd.DataFrame({"week_ending_date": dates, "icu_beds_occupied": occupancy})
    return MLDataset(
        dataset_name="nhsn_hrd",
        source_collection="historical_hospital_capacity",
        df=df,
        target_column="icu_beds_occupied",
        time_column="week_ending_date",
        frequency="W",
        metadata={"total_source_records": 150},
    )


async def main():
    print("--- MOCKED ML PIPELINE (Docker DB Down) ---")

    # Hero DMC
    ds_hero = mock_hero_dataset()
    config_hero = ForecastConfig(
        dataset_name="hero_dmc",
        target_column="daily_admissions",
        features=FeatureConfig(
            lags=[1, 7, 14], rolling_windows=[7, 28], include_day_of_week=True, include_month=True
        ),
        split=SplitConfig(train_ratio=0.7, val_ratio=0.15, test_ratio=0.15),
        baseline_model_type="naive",
    )
    orch_hero = MLPipelineOrchestrator(config_hero)
    exp_hero = orch_hero.run(ds_hero)
    print("\nHero DMC Pipeline Results:")
    print(f"Date Range: {ds_hero.date_range[0].date()} to {ds_hero.date_range[1].date()}")
    print(f"Rows (before/after): {ds_hero.row_count} / {exp_hero.total_rows}")
    print(f"Features Generated: {exp_hero.feature_count}")
    print(
        f"Splits: Train {exp_hero.train_rows}, Val {exp_hero.val_rows}, Test {exp_hero.test_rows}"
    )
    print("Metrics (MAE/RMSE):")
    print(
        f"  Train: MAE={exp_hero.train_metrics['mae']:.2f}, RMSE={exp_hero.train_metrics['rmse']:.2f}"
    )
    print(
        f"  Val:   MAE={exp_hero.val_metrics['mae']:.2f}, RMSE={exp_hero.val_metrics['rmse']:.2f}"
    )
    print(
        f"  Test:  MAE={exp_hero.test_metrics['mae']:.2f}, RMSE={exp_hero.test_metrics['rmse']:.2f}"
    )

    # NHSN
    ds_nhsn = mock_nhsn_dataset()
    config_nhsn = ForecastConfig(
        dataset_name="nhsn_hrd",
        target_column="icu_beds_occupied",
        features=FeatureConfig(lags=[1, 2, 4], rolling_windows=[4, 12], include_month=True),
        split=SplitConfig(train_ratio=0.7, val_ratio=0.15, test_ratio=0.15),
        baseline_model_type="naive",
    )
    orch_nhsn = MLPipelineOrchestrator(config_nhsn)
    exp_nhsn = orch_nhsn.run(ds_nhsn)
    print("\nNHSN Pipeline Results:")
    print(f"Date Range: {ds_nhsn.date_range[0].date()} to {ds_nhsn.date_range[1].date()}")
    print(f"Rows (before/after): {ds_nhsn.row_count} / {exp_nhsn.total_rows}")
    print(f"Features Generated: {exp_nhsn.feature_count}")
    print(
        f"Splits: Train {exp_nhsn.train_rows}, Val {exp_nhsn.val_rows}, Test {exp_nhsn.test_rows}"
    )
    print("Metrics (MAE/RMSE):")
    print(
        f"  Train: MAE={exp_nhsn.train_metrics['mae']:.2f}, RMSE={exp_nhsn.train_metrics['rmse']:.2f}"
    )
    print(
        f"  Val:   MAE={exp_nhsn.val_metrics['mae']:.2f}, RMSE={exp_nhsn.val_metrics['rmse']:.2f}"
    )
    print(
        f"  Test:  MAE={exp_nhsn.test_metrics['mae']:.2f}, RMSE={exp_nhsn.test_metrics['rmse']:.2f}"
    )


if __name__ == "__main__":
    asyncio.run(main())
