import argparse
import asyncio
import json

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


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run the ML Pipeline Foundation")
    parser.add_argument(
        "--dataset", required=True, choices=["hero_dmc", "nhsn_hrd"], help="Dataset to process"
    )
    parser.add_argument("--target", required=True, help="Target column to forecast")
    parser.add_argument(
        "--model",
        default="naive",
        choices=["naive", "seasonal_naive", "moving_average"],
        help="Baseline model to run",
    )
    parser.add_argument("--horizon", type=int, default=1, help="Forecast horizon")
    parser.add_argument(
        "--seasonal-period", type=int, default=7, help="Seasonal period for seasonal naive"
    )
    parser.add_argument("--window", type=int, default=7, help="Moving average window")
    parser.add_argument("--walk-forward", type=int, default=1, help="Walk-forward origins")
    parser.add_argument("--dry-run", action="store_true", help="Run without saving artifacts")
    args = parser.parse_args()

    # Get DB connection
    settings = get_settings()
    await init_db(settings)
    db = await get_database()

    print(f"--- Starting ML Pipeline for {args.dataset} (Model: {args.model}) ---")

    # 1. Setup Adapter and Config
    if args.dataset == "hero_dmc":
        repo = HistoricalAdmissionsRepository(db)
        adapter = HeroDMCAdapter(repo)

        # Config tailored for daily admissions
        config = ForecastConfig(
            dataset_name=args.dataset,
            target_column=args.target,
            features=FeatureConfig(
                lags=[1, args.seasonal_period, 14, 30],
                rolling_windows=[args.window, 14, 28],
                include_day_of_week=True,
                include_month=True,
            ),
            split=SplitConfig(train_ratio=0.7, val_ratio=0.15, test_ratio=0.15),
            baseline_model_type=args.model,
            baseline_model_kwargs={"seasonal_period": args.seasonal_period, "window": args.window},
            horizon=args.horizon,
            walk_forward_origins=args.walk_forward,
            high_demand_quantile=0.90,
        )
    else:
        repo = HistoricalHospitalCapacityRepository(db)
        adapter = NHSNAdapter(repo, target_column=args.target)

        # Config tailored for weekly capacity
        config = ForecastConfig(
            dataset_name=args.dataset,
            target_column=args.target,
            features=FeatureConfig(
                lags=[1, 2, 4, args.seasonal_period],
                rolling_windows=[2, 4, 12, args.window],
                include_month=True,
            ),
            split=SplitConfig(train_ratio=0.7, val_ratio=0.15, test_ratio=0.15),
            baseline_model_type=args.model,
            baseline_model_kwargs={"seasonal_period": args.seasonal_period, "window": args.window},
            horizon=args.horizon,
            walk_forward_origins=args.walk_forward,
            high_demand_quantile=0.85,
        )

    # 2. Fetch Dataset
    print(f"Fetching dataset {args.dataset}...")
    dataset = await adapter.fetch_dataset()
    print(
        f"Fetched {dataset.row_count} rows. Date range: {dataset.date_range[0].date()} to {dataset.date_range[1].date()}"
    )

    if dataset.row_count == 0:
        print("Error: Dataset is empty. Did you run the ingestion pipeline first?")
        return

    # 3. Run Pipeline
    print("Orchestrating ML Pipeline...")
    orchestrator = MLPipelineOrchestrator(config)
    experiment = orchestrator.run(dataset)

    # 4. Report Results
    fr = experiment.forecasts[0]

    print("\n--- Pipeline Results ---")
    print(f"Run ID: {experiment.run_id}")
    print(f"Dataset: {experiment.dataset_name}")
    print(f"Target: {config.target_column}")
    print(f"Model: {fr.model_name}")
    print(f"Horizon: {fr.horizon}")
    print(f"Total Rows (after features): {experiment.total_rows}")
    print(f"Features Generated: {experiment.feature_count}")
    print(
        f"Train Rows: {experiment.train_rows}, Val Rows: {experiment.val_rows}, Test Rows: {experiment.test_rows}"
    )

    print("\nBaseline Evaluation (Test Set):")
    print(json.dumps(fr.metrics.model_dump(), indent=2))

    if fr.high_demand_metrics:
        print(f"\nHigh Demand Evaluation (Threshold > {fr.high_demand_threshold:.2f}):")
        print(json.dumps(fr.high_demand_metrics.model_dump(), indent=2))

    print(f"\nArtifact saved to: {experiment.artifact_dir}")
    print("----------------------------------------")


if __name__ == "__main__":
    asyncio.run(main())
