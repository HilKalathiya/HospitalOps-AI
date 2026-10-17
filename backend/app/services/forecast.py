"""
HospitalOps AI — Forecasting Service (Chunk 2.7).

Orchestrates model selection resolution, forecast retrieval, artifact inspection,
provenance tracking, and safe on-demand execution while preserving strict data boundaries.
"""

import json
import logging
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status

from app.data_ingestion.repositories import (
    HistoricalAdmissionsRepository,
    HistoricalHospitalCapacityRepository,
)
from app.ml.adapters.hero_dmc import HeroDMCAdapter
from app.ml.adapters.nhsn import NHSNAdapter
from app.ml.contracts.config import FeatureConfig, ForecastConfig, SplitConfig
from app.ml.contracts.experiment import ExperimentRun
from app.ml.contracts.forecast import ForecastResult
from app.ml.pipelines.orchestrator import MLPipelineOrchestrator
from app.ml.selection.benchmark import BenchmarkEvaluator
from app.ml.selection.selector import ModelSelector
from app.schemas.forecast import (
    BenchmarkComparisonSummary,
    BenchmarkReportResponse,
    ExperimentRunSummary,
    ForecastMetadata,
    ForecastResponse,
    PredictionPoint,
)

logger = logging.getLogger(__name__)


class ForecastService:
    """
    Core service layer for operational demand forecasting, model selection,
    benchmark reports, and experiment artifact retrieval.
    """

    SUPPORTED_MODEL_TYPES = {"baseline", "arima", "prophet", "lstm"}

    def __init__(
        self,
        admissions_repo: HistoricalAdmissionsRepository | None = None,
        capacity_repo: HistoricalHospitalCapacityRepository | None = None,
        runs_dirs: list[str] | None = None,
        evaluations_dir: str = "backend/ml/evaluations",
    ):
        self.admissions_repo = admissions_repo
        self.capacity_repo = capacity_repo
        self.runs_dirs = runs_dirs or [
            "backend/ml/runs",
            "backend/backend/ml/runs",
            "ml/runs",
        ]
        self.evaluations_dir = evaluations_dir
        self.benchmark_evaluator = BenchmarkEvaluator(
            runs_dirs=self.runs_dirs,
            output_dir=self.evaluations_dir,
        )

    # ── Benchmark & Evaluation Retrieval ──────────────────────────────────────

    def get_benchmarks(
        self,
        dataset_name: str | None = None,
        target_column: str | None = None,
        horizon: int | None = None,
    ) -> BenchmarkReportResponse:
        """
        Retrieves verified model evaluation benchmark records and selection leaderboards.
        Reads saved benchmark artifacts (model_selection_report.json) or runs evaluation.
        """
        report_data = self._load_or_generate_benchmark_report()

        comparisons = report_data.get("comparisons", [])
        filtered_comparisons: list[BenchmarkComparisonSummary] = []

        for comp_dict in comparisons:
            if dataset_name and comp_dict.get("dataset_name") != dataset_name.lower():
                continue
            if target_column and comp_dict.get("target_column") != target_column.lower():
                continue
            if horizon is not None and comp_dict.get("horizon") != horizon:
                continue

            filtered_comparisons.append(BenchmarkComparisonSummary.model_validate(comp_dict))

        return BenchmarkReportResponse(
            report_id=report_data.get("report_id", "default"),
            generated_at=datetime.fromisoformat(report_data["generated_at"])
            if isinstance(report_data.get("generated_at"), str)
            else report_data.get("generated_at", datetime.now(UTC)),
            total_runs_evaluated=report_data.get("total_runs_evaluated", len(filtered_comparisons)),
            successful_runs=report_data.get("successful_runs", 0),
            failed_or_missing_runs=report_data.get("failed_or_missing_runs", 0),
            comparisons=filtered_comparisons,
        )

    def _load_or_generate_benchmark_report(self) -> dict[str, Any]:
        """Loads cached benchmark selection JSON or regenerates it from existing runs."""
        report_file = Path(self.evaluations_dir) / "model_selection_report.json"
        if report_file.exists():
            try:
                with open(report_file, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Could not read cached benchmark report from %s: %s", report_file, e)

        # Regenerate benchmark report from saved runs
        report = self.benchmark_evaluator.run_benchmark_evaluation()
        self.benchmark_evaluator.save_report(report)
        return json.loads(report.model_dump_json())

    # ── Admissions Forecasting ────────────────────────────────────────────────

    async def get_admissions_forecast(
        self,
        horizon: int = 7,
        model_type: str | None = None,
        run_id: str | None = None,
        dataset_name: str = "hero_dmc",
    ) -> ForecastResponse:
        """
        Generates or retrieves daily admissions forecast for the Hero DMC benchmark series.
        Cadence: Daily ('D').
        Units: 'admissions'.
        """
        # 1. Validation
        if horizon < 1 or horizon > 30:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Horizon {horizon} is invalid for daily admissions. Supported range: 1 to 30 days.",
            )

        if dataset_name.lower() != "hero_dmc":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Dataset '{dataset_name}' is not supported for admissions. Supported dataset: 'hero_dmc'.",
            )

        if model_type and model_type.lower() not in self.SUPPORTED_MODEL_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Model type '{model_type}' is invalid. Supported types: {sorted(self.SUPPORTED_MODEL_TYPES)}",
            )

        target_column = "daily_admissions"

        # 2. Model resolution
        selected_winner: dict[str, Any] | None = None
        target_model_type = model_type.lower() if model_type else None
        target_config_name: str | None = None

        if not target_model_type and not run_id:
            # Resolve optimal winner from validation metrics in benchmark report
            winner_info = self._resolve_benchmark_winner(
                dataset_name="hero_dmc",
                target_column=target_column,
                horizon=horizon,
            )
            if winner_info:
                selected_winner = winner_info
                target_model_type = winner_info.get("model_type")
                target_config_name = winner_info.get("config_name")

        # 3. Locate matching saved run artifact
        matched_run = self._find_saved_run(
            run_id=run_id,
            dataset_name="hero_dmc",
            target_column=target_column,
            horizon=horizon,
            model_type=target_model_type,
            config_name=target_config_name,
        )

        if matched_run:
            return self._build_forecast_response_from_run(
                run=matched_run,
                dataset_name="hero_dmc",
                target_column=target_column,
                target_units="admissions",
                frequency="D",
                horizon=horizon,
                horizon_unit="d",
                selected_winner=selected_winner,
            )

        # 4. On-demand execution if repository has historical data
        if self.admissions_repo:
            try:
                adapter = HeroDMCAdapter(self.admissions_repo)
                dataset = await adapter.fetch_dataset()
                if len(dataset.df) >= 30:
                    effective_model = target_model_type or "baseline"
                    config = ForecastConfig(
                        dataset_name="hero_dmc",
                        target_column=target_column,
                        model_type=effective_model,
                        baseline_model_type="naive",
                        horizon=horizon,
                        features=FeatureConfig(lags=[1, 7], rolling_windows=[7]),
                        split=SplitConfig(train_ratio=0.7, val_ratio=0.15, test_ratio=0.15),
                        tracking_enabled=False,
                    )
                    orchestrator = MLPipelineOrchestrator(config=config)
                    exp = orchestrator.run(dataset)
                    return self._build_forecast_response_from_run(
                        run=exp,
                        dataset_name="hero_dmc",
                        target_column=target_column,
                        target_units="admissions",
                        frequency="D",
                        horizon=horizon,
                        horizon_unit="d",
                        selected_winner=selected_winner,
                        provenance="on_demand_fit",
                    )
            except Exception as e:
                logger.warning("On-demand admissions forecast execution failed: %s", e)

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No saved benchmark forecast or historical admission data available for "
                f"dataset='hero_dmc', horizon={horizon}d, model_type='{target_model_type or 'any'}'."
            ),
        )

    # ── ICU Capacity Forecasting ──────────────────────────────────────────────

    async def get_icu_forecast(
        self,
        horizon: int = 2,
        model_type: str | None = None,
        run_id: str | None = None,
        dataset_name: str = "nhsn_hrd",
    ) -> ForecastResponse:
        """
        Generates or retrieves weekly ICU capacity forecast for the NHSN HRD series.
        Cadence: Weekly ('W').
        Units: 'beds'.
        """
        # 1. Validation
        if horizon < 1 or horizon > 8:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Horizon {horizon} is invalid for weekly ICU capacity. Supported range: 1 to 8 weeks.",
            )

        if dataset_name.lower() != "nhsn_hrd":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Dataset '{dataset_name}' is not supported for ICU capacity. Supported dataset: 'nhsn_hrd'.",
            )

        if model_type and model_type.lower() not in self.SUPPORTED_MODEL_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Model type '{model_type}' is invalid. Supported types: {sorted(self.SUPPORTED_MODEL_TYPES)}",
            )

        target_column = "icu_beds_occupied"

        # 2. Model resolution
        selected_winner: dict[str, Any] | None = None
        target_model_type = model_type.lower() if model_type else None
        target_config_name: str | None = None

        if not target_model_type and not run_id:
            winner_info = self._resolve_benchmark_winner(
                dataset_name="nhsn_hrd",
                target_column=target_column,
                horizon=horizon,
            )
            if winner_info:
                selected_winner = winner_info
                target_model_type = winner_info.get("model_type")
                target_config_name = winner_info.get("config_name")

        # 3. Locate matching saved run artifact
        matched_run = self._find_saved_run(
            run_id=run_id,
            dataset_name="nhsn_hrd",
            target_column=target_column,
            horizon=horizon,
            model_type=target_model_type,
            config_name=target_config_name,
        )

        if matched_run:
            return self._build_forecast_response_from_run(
                run=matched_run,
                dataset_name="nhsn_hrd",
                target_column=target_column,
                target_units="beds",
                frequency="W",
                horizon=horizon,
                horizon_unit="w",
                selected_winner=selected_winner,
            )

        # 4. On-demand execution if repository has capacity records
        if self.capacity_repo:
            try:
                adapter = NHSNAdapter(self.capacity_repo, target_column=target_column)
                dataset = await adapter.fetch_dataset()
                if len(dataset.df) >= 20:
                    effective_model = target_model_type or "baseline"
                    config = ForecastConfig(
                        dataset_name="nhsn_hrd",
                        target_column=target_column,
                        model_type=effective_model,
                        baseline_model_type="moving_average",
                        baseline_model_kwargs={"window": 4},
                        horizon=horizon,
                        features=FeatureConfig(lags=[1, 4], rolling_windows=[4]),
                        split=SplitConfig(train_ratio=0.7, val_ratio=0.15, test_ratio=0.15),
                        tracking_enabled=False,
                    )
                    orchestrator = MLPipelineOrchestrator(config=config)
                    exp = orchestrator.run(dataset)
                    return self._build_forecast_response_from_run(
                        run=exp,
                        dataset_name="nhsn_hrd",
                        target_column=target_column,
                        target_units="beds",
                        frequency="W",
                        horizon=horizon,
                        horizon_unit="w",
                        selected_winner=selected_winner,
                        provenance="on_demand_fit",
                    )
            except Exception as e:
                logger.warning("On-demand ICU capacity forecast execution failed: %s", e)

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No saved benchmark forecast or historical capacity data available for "
                f"dataset='nhsn_hrd', target='{target_column}', horizon={horizon}w, "
                f"model_type='{target_model_type or 'any'}'."
            ),
        )

    # ── Occupancy Forecasting (Unsupported Guardrail) ─────────────────────────

    def get_occupancy_forecast(
        self,
        horizon: int = 7,
        dataset_name: str | None = None,
        target_column: str | None = None,
    ) -> ForecastResponse:
        """
        Inspects whether a valid occupancy rate or percentage target is supported.

        Strictly enforces healthcare data integrity:
        - Occupancy rate requires concurrent occupied beds AND total licensed beds
          for the exact same population, ward, and timeframe.
        - Neither Hero DMC nor NHSN HRD has an approved, benchmarked occupancy percentage model.
        - Rather than fabricating synthetic occupancy percentages, returns an explicit
          unsupported error response per acceptance criteria.
        """
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Occupancy rate forecasting is currently unsupported. "
                "A reliable occupancy forecast requires concurrent occupied beds and total licensed capacity "
                "for the exact population and timeframe. Existing trained models support admissions "
                "('daily_admissions') and capacity counts ('icu_beds_occupied'), but not derived occupancy percentages."
            ),
        )

    # ── Run History & Detail ──────────────────────────────────────────────────

    def list_saved_runs(
        self,
        dataset_name: str | None = None,
        target_column: str | None = None,
        model_type: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[ExperimentRunSummary], int]:
        """Lists historical experiment runs with filtering and pagination."""
        all_runs = self.benchmark_evaluator.load_runs()
        filtered: list[ExperimentRunSummary] = []

        selector = ModelSelector()

        for run in all_runs:
            if dataset_name and run.dataset_name != dataset_name.lower():
                continue
            cfg_target = getattr(run.config, "target_column", None)
            if target_column and cfg_target != target_column.lower():
                continue
            cfg_model_type = getattr(run.config, "model_type", "baseline")
            if model_type and cfg_model_type != model_type.lower():
                continue

            # Extract validation and test MAE if available
            val_f = next((f for f in run.forecasts if f.split_name == "validation"), None)
            test_f = next((f for f in run.forecasts if f.split_name == "test"), None)

            config_name = selector._extract_config_name(run)

            filtered.append(
                ExperimentRunSummary(
                    run_id=run.run_id,
                    dataset_name=run.dataset_name,
                    target_column=cfg_target or "unknown",
                    model_type=cfg_model_type,
                    config_name=config_name,
                    horizon=getattr(run.config, "horizon", 1),
                    status=run.status,
                    val_mae=val_f.metrics.mae if (val_f and val_f.metrics) else None,
                    test_mae=test_f.metrics.mae if (test_f and test_f.metrics) else None,
                    created_at=run.created_at,
                )
            )

        def _to_utc(dt: datetime) -> datetime:
            return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)

        # Sort descending by creation date
        filtered.sort(key=lambda r: _to_utc(r.created_at), reverse=True)
        total = len(filtered)
        paginated = filtered[skip : skip + limit]
        return paginated, total

    def get_saved_run_by_id(self, run_id: str) -> ExperimentRun:
        """Retrieves complete experiment run artifact by run_id."""
        all_runs = self.benchmark_evaluator.load_runs()
        for r in all_runs:
            if r.run_id == run_id:
                return r

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment run '{run_id}' not found.",
        )

    # ── Internal Helpers ──────────────────────────────────────────────────────

    def _resolve_benchmark_winner(
        self,
        dataset_name: str,
        target_column: str,
        horizon: int,
    ) -> dict[str, Any] | None:
        """Looks up the validation-selected winner from the benchmark report."""
        report_data = self._load_or_generate_benchmark_report()
        for comp in report_data.get("comparisons", []):
            if (
                comp.get("dataset_name") == dataset_name
                and comp.get("target_column") == target_column
                and comp.get("horizon") == horizon
            ):
                return comp.get("winner")
        return None

    def _find_saved_run(
        self,
        run_id: str | None = None,
        dataset_name: str | None = None,
        target_column: str | None = None,
        horizon: int | None = None,
        model_type: str | None = None,
        config_name: str | None = None,
    ) -> ExperimentRun | None:
        """Locates the best matching ExperimentRun artifact."""
        all_runs = self.benchmark_evaluator.load_runs()

        # If specific run_id requested
        if run_id:
            for r in all_runs:
                if r.run_id == run_id:
                    return r
            return None

        selector = ModelSelector()

        candidates: list[ExperimentRun] = []
        for r in all_runs:
            if dataset_name and r.dataset_name != dataset_name:
                continue
            if target_column and getattr(r.config, "target_column", None) != target_column:
                continue
            if horizon is not None and getattr(r.config, "horizon", None) != horizon:
                continue
            if model_type and getattr(r.config, "model_type", None) != model_type:
                continue

            cfg_name = selector._extract_config_name(r)
            if config_name and cfg_name != config_name:
                continue

            if r.forecasts:
                candidates.append(r)

        if not candidates:
            # If specific config_name didn't match, relax to any valid run matching model_type
            if config_name and model_type:
                for r in all_runs:
                    if (
                        getattr(r.config, "target_column", None) == target_column
                        and getattr(r.config, "horizon", None) == horizon
                        and getattr(r.config, "model_type", None) == model_type
                        and r.forecasts
                    ):
                        return r
            return None

        def _to_utc(dt: datetime) -> datetime:
            return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)

        # Return the most recent candidate run
        candidates.sort(key=lambda x: _to_utc(x.created_at), reverse=True)
        return candidates[0]

    def _build_forecast_response_from_run(
        self,
        run: ExperimentRun,
        dataset_name: str,
        target_column: str,
        target_units: str,
        frequency: str,
        horizon: int,
        horizon_unit: str,
        selected_winner: dict[str, Any] | None = None,
        provenance: str = "saved_benchmark_run",
    ) -> ForecastResponse:
        """Converts an ExperimentRun into a ForecastResponse."""
        selector = ModelSelector()
        config_name = selector._extract_config_name(run)
        model_type = getattr(run.config, "model_type", "baseline")

        # Select the forecast result: prefer 'test', fallback to 'validation'
        target_forecast: ForecastResult | None = next(
            (f for f in run.forecasts if f.split_name == "test"), None
        )
        if not target_forecast:
            target_forecast = next(
                (f for f in run.forecasts if f.split_name == "validation"), None
            )

        if not target_forecast or not target_forecast.predictions:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Run '{run.run_id}' contains no valid prediction sequences.",
            )

        # Validation & test MAE
        val_f = next((f for f in run.forecasts if f.split_name == "validation"), None)
        test_f = next((f for f in run.forecasts if f.split_name == "test"), None)

        predictions_points: list[PredictionPoint] = []
        timestamps = target_forecast.forecast_timestamps
        preds = target_forecast.predictions

        # Truncate to horizon if longer
        pts_count = min(horizon, len(preds))

        for i in range(pts_count):
            ts = timestamps[i] if i < len(timestamps) else f"step_{i+1}"
            raw_val = preds[i]
            if raw_val is None or math.isnan(raw_val) or math.isinf(raw_val):
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=(
                        f"Model run '{run.run_id}' produced non-finite prediction value ({raw_val}) "
                        f"at horizon step {i+1}. The forecast output is unavailable."
                    ),
                )
            val = float(raw_val)

            predictions_points.append(
                PredictionPoint(
                    timestamp=str(ts),
                    value=round(val, 2),
                    lower_bound=None,  # baseline & arima without MC do not fabricate intervals
                    upper_bound=None,
                    confidence_level=None,
                )
            )

        # Extract historical observations leading up to the forecast origin
        historical_points: list[PredictionPoint] = []
        forecast_origin: str | None = None

        if val_f and val_f.forecast_timestamps and val_f.actuals:
            v_ts = val_f.forecast_timestamps
            v_acts = val_f.actuals
            forecast_origin = str(v_ts[-1])

            # Take up to 28 recent points for daily, or up to 12 for weekly
            history_window = 28 if frequency == "D" else 12
            slice_start = max(0, len(v_ts) - history_window)
            for idx in range(slice_start, len(v_ts)):
                act_val = v_acts[idx] if idx < len(v_acts) else None
                if act_val is not None and not math.isnan(act_val) and not math.isinf(act_val):
                    historical_points.append(
                        PredictionPoint(
                            timestamp=str(v_ts[idx]),
                            value=round(float(act_val), 2),
                            lower_bound=None,
                            upper_bound=None,
                            confidence_level=None,
                        )
                    )
        elif timestamps:
            forecast_origin = str(timestamps[0])

        val_mae = val_f.metrics.mae if (val_f and val_f.metrics) else None
        test_mae = test_f.metrics.mae if (test_f and test_f.metrics) else None

        if selected_winner and selected_winner.get("val_metrics"):
            val_mae = selected_winner["val_metrics"].get("mae", val_mae)
        if selected_winner and selected_winner.get("test_metrics"):
            test_mae = selected_winner["test_metrics"].get("mae", test_mae)

        meta = ForecastMetadata(
            dataset_name=dataset_name,
            target_column=target_column,
            target_units=target_units,
            frequency=frequency,
            horizon=horizon,
            horizon_unit=horizon_unit,
            forecast_origin=forecast_origin,
            model_type=model_type,
            config_name=config_name,
            run_id=run.run_id,
            mlflow_run_id=run.mlflow_run_id,
            selection_criterion="val_mae",
            validation_mae=round(val_mae, 4) if val_mae is not None else None,
            test_mae=round(test_mae, 4) if test_mae is not None else None,
            intervals_supported=(model_type == "lstm"),
            provenance=provenance,
            generated_at=datetime.now(UTC),
        )

        return ForecastResponse(
            status="SUCCESS",
            message=f"Forecast resolved using validation winner '{config_name}'.",
            metadata=meta,
            predictions=predictions_points,
            historical_points=historical_points,
        )
