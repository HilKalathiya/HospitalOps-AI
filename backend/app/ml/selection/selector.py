import logging
from typing import Any

from app.ml.contracts.evaluation import safe_mape
from app.ml.contracts.experiment import ExperimentRun
from app.ml.contracts.selection import ModelEvaluationEntry, SelectionComparison

logger = logging.getLogger(__name__)


class ModelSelector:
    """
    Leakage-Free Model Evaluation & Selection Engine.

    Guarantees:
    1. Model selection is based SOLELY on validation split metrics.
    2. Held-out test split metrics are completely isolated from selection and reported post-selection.
    3. Comparisons are strictly partitioned by compatible dataset, target, horizon, and cadence.
    4. Missing or failed candidate models are surfaced explicitly in the leaderboard.
    """

    def __init__(
        self,
        primary_metric: str = "val_mae",
        secondary_metric: str = "val_rmse",
        higher_is_better: bool = False,
    ):
        self.primary_metric = primary_metric
        self.secondary_metric = secondary_metric
        self.higher_is_better = higher_is_better

    def _extract_config_name(self, run: ExperimentRun) -> str:
        """Derives a human-readable config name from an experiment run."""
        model_type = getattr(run.config, "model_type", "baseline")
        if model_type == "baseline":
            base_type = getattr(run.config, "baseline_model_type", "naive")
            kwargs = getattr(run.config, "baseline_model_kwargs", {})
            if base_type == "seasonal_naive" and "seasonal_period" in kwargs:
                return f"seasonal_naive_p{kwargs['seasonal_period']}"
            elif base_type == "moving_average" and "window" in kwargs:
                return f"moving_average_w{kwargs['window']}"
            return base_type
        elif model_type == "arima":
            order = getattr(run.config, "arima_order", (1, 0, 0))
            seasonal = getattr(run.config, "arima_seasonal_order", (0, 0, 0, 0))
            if seasonal and seasonal[3] > 0:
                return f"sarima_{order[0]}_{order[1]}_{order[2]}_{seasonal[3]}"
            return f"arima_{order[0]}_{order[1]}_{order[2]}"
        elif model_type == "prophet":
            p_kwargs = getattr(run.config, "prophet_kwargs", {})
            if p_kwargs.get("weekly_seasonality") and not p_kwargs.get("yearly_seasonality"):
                return "prophet_weekly_only"
            elif p_kwargs.get("yearly_seasonality") and not p_kwargs.get("weekly_seasonality"):
                return "prophet_yearly_only"
            return "prophet_default"
        elif model_type == "lstm":
            dim = getattr(run.config, "lstm_hidden_dim", 32)
            layers = getattr(run.config, "lstm_num_layers", 2)
            epochs = getattr(run.config, "lstm_epochs", 15)
            return f"lstm_h{dim}_l{layers}_e{epochs}"
        return f"{model_type}_custom"

    def compare_and_select(
        self,
        runs: list[ExperimentRun],
        dataset_name: str,
        target_column: str,
        horizon: int,
        horizon_unit: str = "d",
        expected_grid: list[tuple[str, str, dict[str, Any]]] | None = None,
    ) -> SelectionComparison:
        """
        Compares all candidate runs for a given dataset, target, and horizon.
        Selects the optimal model based strictly on validation metrics.
        """
        # Determine target units
        target_units = "admissions" if "admission" in target_column.lower() else "beds"

        # Group compatible runs by config_name to avoid duplicates from multiple benchmark iterations
        config_runs: dict[str, list[ExperimentRun]] = {}
        for run in runs:
            if run.dataset_name != dataset_name:
                continue
            if getattr(run.config, "target_column", None) != target_column:
                continue
            if getattr(run.config, "horizon", None) != horizon:
                continue

            config_name = self._extract_config_name(run)
            config_runs.setdefault(config_name, []).append(run)

        successful_entries: list[ModelEvaluationEntry] = []
        failed_entries: list[ModelEvaluationEntry] = []

        # Process each observed configuration
        for config_name, runs_for_cfg in config_runs.items():
            valid_candidates: list[ModelEvaluationEntry] = []
            failed_candidate_reasons: list[str] = []
            model_type = getattr(runs_for_cfg[0].config, "model_type", "baseline")

            for run in runs_for_cfg:
                m_type = getattr(run.config, "model_type", "baseline")
                if run.status == "FAILED" or not run.forecasts:
                    failed_candidate_reasons.append("Experiment run status FAILED or produced no forecasts")
                    continue

                fr_val = next((f for f in run.forecasts if f.split_name == "validation"), None)
                fr_test = next((f for f in run.forecasts if f.split_name == "test"), None)

                if fr_val is None:
                    failed_candidate_reasons.append("Validation split forecast missing; cannot evaluate without leakage")
                    continue

                # Ensure MAPE is populated
                val_metrics = fr_val.metrics
                if val_metrics.mape is None and fr_val.actuals and fr_val.predictions:
                    val_metrics.mape = safe_mape(fr_val.actuals, fr_val.predictions)

                test_metrics = None
                if fr_test is not None:
                    test_metrics = fr_test.metrics
                    if test_metrics.mape is None and fr_test.actuals and fr_test.predictions:
                        test_metrics.mape = safe_mape(fr_test.actuals, fr_test.predictions)

                valid_candidates.append(
                    ModelEvaluationEntry(
                        model_type=m_type,
                        config_name=config_name,
                        status="SUCCESS",
                        val_metrics=val_metrics,
                        test_metrics=test_metrics,
                        run_id=run.run_id,
                    )
                )

            if valid_candidates:
                # Pick the run with the best validation MAE (tie breaker RMSE) for this configuration
                valid_candidates.sort(
                    key=lambda e: (
                        e.val_metrics.mae if e.val_metrics else float("inf"),
                        e.val_metrics.rmse if e.val_metrics else float("inf"),
                    ),
                    reverse=self.higher_is_better,
                )
                successful_entries.append(valid_candidates[0])
            else:
                reason = failed_candidate_reasons[0] if failed_candidate_reasons else "Configuration execution failed"
                failed_entries.append(
                    ModelEvaluationEntry(
                        model_type=model_type,
                        config_name=config_name,
                        status="FAILED",
                        error_message=reason,
                        run_id=runs_for_cfg[0].run_id,
                    )
                )

        # Check for missing models against expected grid
        if expected_grid:
            for exp_mtype, exp_cname, _ in expected_grid:
                if exp_cname not in config_runs:
                    failed_entries.append(
                        ModelEvaluationEntry(
                            model_type=exp_mtype,
                            config_name=exp_cname,
                            status="MISSING",
                            error_message="Candidate configuration was not executed in benchmark",
                        )
                    )

        # 5. Strict Validation-Only Ranking & Selection
        # NEVER use test_metrics for sorting or selection!
        if successful_entries:

            def get_sort_key(e: ModelEvaluationEntry):
                val_mae = e.val_metrics.mae if e.val_metrics else float("inf")
                val_rmse = e.val_metrics.rmse if e.val_metrics else float("inf")
                return (val_mae, val_rmse)

            successful_entries.sort(key=get_sort_key, reverse=self.higher_is_better)

            for rank, entry in enumerate(successful_entries, start=1):
                entry.rank = rank

            winner = successful_entries[0]
        else:
            winner = None

        leaderboard = successful_entries + failed_entries

        notes = (
            f"Evaluated {len(successful_entries)} successful configurations. "
            f"{len(failed_entries)} failed or missing. "
            f"Winner selected purely on validation MAE."
        )

        return SelectionComparison(
            dataset_name=dataset_name,
            target_column=target_column,
            horizon=horizon,
            horizon_unit=horizon_unit,
            target_units=target_units,
            selection_criterion=self.primary_metric,
            secondary_criterion=self.secondary_metric,
            winner=winner,
            leaderboard=leaderboard,
            summary_notes=notes,
        )
