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


def get_hero_dmc_grid():
    baselines = [
        ("baseline", "naive", {}),
        ("baseline", "seasonal_naive", {"seasonal_period": 7}),
        ("baseline", "moving_average", {"window": 7}),
        ("baseline", "moving_average", {"window": 14}),
        ("baseline", "moving_average", {"window": 28}),
    ]

    # Very small grid for local performance
    arima_grid = [
        ("arima", "arima_1_0_0", {"arima_order": (1, 0, 0), "arima_seasonal_order": (0, 0, 0, 0)}),
        ("arima", "arima_1_1_1", {"arima_order": (1, 1, 1), "arima_seasonal_order": (0, 0, 0, 0)}),
        (
            "arima",
            "sarima_1_0_0_7",
            {"arima_order": (1, 0, 0), "arima_seasonal_order": (1, 0, 0, 7)},
        ),
    ]

    prophet_grid = [
        ("prophet", "prophet_default", {}),
        (
            "prophet",
            "prophet_weekly_only",
            {"yearly_seasonality": False, "weekly_seasonality": True, "daily_seasonality": False},
        ),
    ]

    return baselines + arima_grid + prophet_grid


def get_nhsn_grid():
    baselines = [
        ("baseline", "naive", {}),
        ("baseline", "moving_average", {"window": 4}),
        ("baseline", "moving_average", {"window": 12}),
        ("baseline", "seasonal_naive", {"seasonal_period": 52}),
    ]

    arima_grid = [
        ("arima", "arima_1_0_0", {"arima_order": (1, 0, 0), "arima_seasonal_order": (0, 0, 0, 0)}),
        ("arima", "arima_1_1_1", {"arima_order": (1, 1, 1), "arima_seasonal_order": (0, 0, 0, 0)}),
    ]

    prophet_grid = [
        # NHSN is weekly. Default weekly seasonality will fail or overfit.
        (
            "prophet",
            "prophet_yearly_only",
            {"yearly_seasonality": True, "weekly_seasonality": False, "daily_seasonality": False},
        ),
    ]

    return baselines + arima_grid + prophet_grid


async def run_benchmark(
    db, dataset_name, target, get_grid_fn, horizons, horizon_unit, features_config, high_demand
):
    print(f"\n--- Starting {dataset_name.upper()} Benchmark ---")

    if dataset_name == "hero_dmc":
        repo = HistoricalAdmissionsRepository(db)
        adapter = HeroDMCAdapter(repo)
    else:
        repo = HistoricalHospitalCapacityRepository(db)
        adapter = NHSNAdapter(repo, target_column=target)

    dataset = await adapter.fetch_dataset()
    if dataset.row_count == 0:
        print(f"{dataset_name} dataset is empty!")
        return

    grid = get_grid_fn()

    # Store results
    # dict mapping horizon -> list of dicts with metrics
    eval_results = {h: [] for h in horizons}

    for horizon in horizons:
        print(f"\nEvaluating Horizon: {horizon}{horizon_unit}")
        for model_type, config_name, kwargs in grid:
            # Extract kwargs based on model_type
            cfg_kwargs = {}
            if model_type == "baseline":
                cfg_kwargs["baseline_model_type"] = config_name
                if "seasonal_period" in kwargs:
                    cfg_kwargs["baseline_model_kwargs"] = {
                        "seasonal_period": kwargs["seasonal_period"]
                    }
                if "window" in kwargs:
                    cfg_kwargs["baseline_model_kwargs"] = {"window": kwargs["window"]}
            elif model_type == "arima":
                cfg_kwargs["arima_order"] = kwargs["arima_order"]
                cfg_kwargs["arima_seasonal_order"] = kwargs["arima_seasonal_order"]
            elif model_type == "prophet":
                cfg_kwargs["prophet_kwargs"] = kwargs

            config = ForecastConfig(
                dataset_name=dataset_name,
                target_column=target,
                features=features_config,
                split=SplitConfig(train_ratio=0.7, val_ratio=0.15, test_ratio=0.15),
                model_type=model_type,
                horizon=horizon,
                walk_forward_origins=3,  # 3 origins to balance rigor and runtime
                high_demand_quantile=high_demand,
                **cfg_kwargs,
            )

            try:
                orch = MLPipelineOrchestrator(config)
                exp = orch.run(dataset)

                # Extract val and test results
                fr_val = next((f for f in exp.forecasts if f.split_name == "validation"), None)
                fr_test = next((f for f in exp.forecasts if f.split_name == "test"), None)

                if fr_val and fr_test:
                    eval_results[horizon].append(
                        {
                            "model_type": model_type,
                            "config_name": config_name,
                            "val_mae": fr_val.metrics.mae,
                            "val_rmse": fr_val.metrics.rmse,
                            "test_mae": fr_test.metrics.mae,
                            "test_rmse": fr_test.metrics.rmse,
                            "test_smape": fr_test.metrics.smape,
                            "test_surge_mae": fr_test.high_demand_metrics.mae
                            if fr_test.high_demand_metrics
                            else None,
                        }
                    )
                else:
                    print(f"Failed to get complete validation/test results for {config_name}")

            except Exception as e:
                print(f"Failed {config_name} (h={horizon}): {e}")

    # Process results: Select the winner for each horizon per model class, and then overall
    final_table = []

    print(f"\n{dataset_name.upper()} Baseline vs ARIMA vs Prophet Benchmark:")
    for horizon in horizons:
        results = eval_results[horizon]
        if not results:
            continue

        df_res = pd.DataFrame(results)

        # Select best baseline
        df_baseline = df_res[df_res["model_type"] == "baseline"]
        if not df_baseline.empty:
            best_base = df_baseline.sort_values(["val_mae", "val_rmse"]).iloc[0]
            final_table.append(
                {
                    "Dataset": dataset_name.upper(),
                    "Target": target,
                    "Class": "Baseline",
                    "Winner Config": best_base["config_name"],
                    "Horizon": f"{horizon}{horizon_unit}",
                    "Val MAE": round(best_base["val_mae"], 2),
                    "Test MAE": round(best_base["test_mae"], 2),
                    "Test RMSE": round(best_base["test_rmse"], 2),
                    "Test sMAPE": round(best_base["test_smape"], 2),
                }
            )

        # Select best arima
        df_arima = df_res[df_res["model_type"] == "arima"]
        if not df_arima.empty:
            best_arima = df_arima.sort_values(["val_mae", "val_rmse"]).iloc[0]
            final_table.append(
                {
                    "Dataset": dataset_name.upper(),
                    "Target": target,
                    "Class": "ARIMA",
                    "Winner Config": best_arima["config_name"],
                    "Horizon": f"{horizon}{horizon_unit}",
                    "Val MAE": round(best_arima["val_mae"], 2),
                    "Test MAE": round(best_arima["test_mae"], 2),
                    "Test RMSE": round(best_arima["test_rmse"], 2),
                    "Test sMAPE": round(best_arima["test_smape"], 2),
                }
            )

        # Select best prophet
        df_prophet = df_res[df_res["model_type"] == "prophet"]
        if not df_prophet.empty:
            best_prophet = df_prophet.sort_values(["val_mae", "val_rmse"]).iloc[0]
            final_table.append(
                {
                    "Dataset": dataset_name.upper(),
                    "Target": target,
                    "Class": "Prophet",
                    "Winner Config": best_prophet["config_name"],
                    "Horizon": f"{horizon}{horizon_unit}",
                    "Val MAE": round(best_prophet["val_mae"], 2),
                    "Test MAE": round(best_prophet["test_mae"], 2),
                    "Test RMSE": round(best_prophet["test_rmse"], 2),
                    "Test sMAPE": round(best_prophet["test_smape"], 2),
                }
            )

    df_final = pd.DataFrame(final_table)
    if not df_final.empty:
        print(df_final.to_markdown(index=False))
    else:
        print("No valid results were generated.")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark Baseline vs Statistical Models")
    parser.add_argument("--dataset", choices=["hero_dmc", "nhsn_hrd", "all"], default="all")
    args = parser.parse_args()

    settings = get_settings()
    await init_db(settings)
    db = await get_database()

    if args.dataset in ["hero_dmc", "all"]:
        feat_cfg = FeatureConfig(
            lags=[1, 7, 14, 30],
            rolling_windows=[7, 14, 28],
            include_day_of_week=True,
            include_month=True,
        )
        await run_benchmark(
            db,
            "hero_dmc",
            "daily_admissions",
            get_hero_dmc_grid,
            [1, 7, 14, 30],
            "d",
            feat_cfg,
            0.90,
        )

    if args.dataset in ["nhsn_hrd", "all"]:
        feat_cfg = FeatureConfig(lags=[1, 2, 4, 52], rolling_windows=[2, 4, 12], include_month=True)
        await run_benchmark(
            db, "nhsn_hrd", "icu_beds_occupied", get_nhsn_grid, [1, 2, 4], "w", feat_cfg, 0.85
        )


if __name__ == "__main__":
    asyncio.run(main())
