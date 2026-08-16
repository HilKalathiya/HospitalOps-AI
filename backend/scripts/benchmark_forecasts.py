import argparse
import asyncio

import pandas as pd

from app.core.config import get_settings
from app.data_ingestion.repositories import (
    HistoricalAdmissionsRepository,
    HistoricalHospitalCapacityRepository,
)
from app.database.client import get_database, init_db
from app.ml.adapters.hero_dmc import HeroDMCAdapter
from app.ml.adapters.nhsn import NHSNAdapter
from app.ml.contracts.config import FeatureConfig, ForecastConfig, SplitConfig
from app.ml.pipelines.orchestrator import MLPipelineOrchestrator


async def benchmark_hero_dmc(db):
    print("\nStarting Hero DMC Benchmark...")
    repo = HistoricalAdmissionsRepository(db)
    adapter = HeroDMCAdapter(repo)
    dataset = await adapter.fetch_dataset()

    if dataset.row_count == 0:
        print("Hero DMC dataset is empty!")
        return

    horizons = [1, 7, 14, 30]
    models = [
        ("naive", {}),
        ("seasonal_naive", {"seasonal_period": 7}),
        ("moving_average", {"window": 7}),
        ("moving_average", {"window": 14}),
        ("moving_average", {"window": 28}),
    ]

    results = []

    for horizon in horizons:
        for model_name, kwargs in models:
            config = ForecastConfig(
                dataset_name="hero_dmc",
                target_column="daily_admissions",
                features=FeatureConfig(
                    lags=[1, 7, 14, 30],
                    rolling_windows=[7, 14, 28],
                    include_day_of_week=True,
                    include_month=True,
                ),
                split=SplitConfig(train_ratio=0.7, val_ratio=0.15, test_ratio=0.15),
                baseline_model_type=model_name,
                baseline_model_kwargs=kwargs,
                horizon=horizon,
                walk_forward_origins=1,
                high_demand_quantile=0.90,
            )

            try:
                orch = MLPipelineOrchestrator(config)
                exp = orch.run(dataset)
                fr = exp.forecasts[0]

                # Format model name with params
                display_name = model_name
                if model_name == "seasonal_naive":
                    display_name = f"Seasonal Naive ({kwargs['seasonal_period']})"
                elif model_name == "moving_average":
                    display_name = f"Moving Average ({kwargs['window']})"

                results.append(
                    {
                        "Dataset": "Hero DMC",
                        "Target": "daily_admissions",
                        "Model": display_name,
                        "Horizon": f"{horizon}d",
                        "MAE": round(fr.metrics.mae, 2),
                        "RMSE": round(fr.metrics.rmse, 2),
                        "sMAPE": round(fr.metrics.smape, 2),
                        "Surge MAE": round(fr.high_demand_metrics.mae, 2)
                        if fr.high_demand_metrics
                        else "N/A",
                    }
                )
            except Exception as e:
                print(f"Failed {model_name} (h={horizon}): {e}")

    df_results = pd.DataFrame(results)
    # Sort by Horizon then MAE
    df_results = df_results.sort_values(["Horizon", "MAE"])
    print("\nHero DMC Baseline Benchmark:")
    print(df_results.to_markdown(index=False))


async def benchmark_nhsn(db):
    print("\nStarting NHSN Benchmark...")
    repo = HistoricalHospitalCapacityRepository(db)
    adapter = NHSNAdapter(repo, target_column="icu_beds_occupied")
    dataset = await adapter.fetch_dataset()

    if dataset.row_count == 0:
        print("NHSN dataset is empty!")
        return

    horizons = [1, 2, 4]  # weeks
    models = [
        ("naive", {}),
        ("moving_average", {"window": 4}),
        ("moving_average", {"window": 12}),
        # Can test seasonal naive if data has 52 weeks seasonality, but it might not be stable
        ("seasonal_naive", {"seasonal_period": 52}),
    ]

    results = []

    for horizon in horizons:
        for model_name, kwargs in models:
            config = ForecastConfig(
                dataset_name="nhsn_hrd",
                target_column="icu_beds_occupied",
                features=FeatureConfig(
                    lags=[1, 2, 4, 52], rolling_windows=[2, 4, 12], include_month=True
                ),
                split=SplitConfig(train_ratio=0.7, val_ratio=0.15, test_ratio=0.15),
                baseline_model_type=model_name,
                baseline_model_kwargs=kwargs,
                horizon=horizon,
                walk_forward_origins=1,
                high_demand_quantile=0.85,
            )

            try:
                orch = MLPipelineOrchestrator(config)
                exp = orch.run(dataset)
                fr = exp.forecasts[0]

                display_name = model_name
                if model_name == "seasonal_naive":
                    display_name = f"Seasonal Naive ({kwargs['seasonal_period']})"
                elif model_name == "moving_average":
                    display_name = f"Moving Average ({kwargs['window']})"

                results.append(
                    {
                        "Dataset": "NHSN",
                        "Target": "icu_beds_occupied",
                        "Model": display_name,
                        "Horizon": f"{horizon}w",
                        "MAE": round(fr.metrics.mae, 2),
                        "RMSE": round(fr.metrics.rmse, 2),
                        "sMAPE": round(fr.metrics.smape, 2),
                        "Surge MAE": round(fr.high_demand_metrics.mae, 2)
                        if fr.high_demand_metrics
                        else "N/A",
                    }
                )
            except Exception as e:
                print(f"Failed {model_name} (h={horizon}): {e}")

    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values(["Horizon", "MAE"])
    print("\nNHSN Baseline Benchmark:")
    print(df_results.to_markdown(index=False))


async def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark Baseline Models")
    parser.add_argument("--dataset", choices=["hero_dmc", "nhsn_hrd", "all"], default="all")
    args = parser.parse_args()

    settings = get_settings()
    await init_db(settings)
    db = await get_database()

    if args.dataset in ["hero_dmc", "all"]:
        await benchmark_hero_dmc(db)

    if args.dataset in ["nhsn_hrd", "all"]:
        await benchmark_nhsn(db)


if __name__ == "__main__":
    asyncio.run(main())
