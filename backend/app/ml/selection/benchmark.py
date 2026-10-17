import json
import logging
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.ml.contracts.experiment import ExperimentRun
from app.ml.contracts.selection import BenchmarkSelectionReport, SelectionComparison
from app.ml.selection.selector import ModelSelector

logger = logging.getLogger(__name__)


def get_default_hero_dmc_grid():
    baselines = [
        ("baseline", "naive", {}),
        ("baseline", "seasonal_naive_p7", {"seasonal_period": 7}),
        ("baseline", "moving_average_w7", {"window": 7}),
        ("baseline", "moving_average_w14", {"window": 14}),
        ("baseline", "moving_average_w28", {"window": 28}),
    ]
    arima_grid = [
        ("arima", "arima_1_0_0", {"arima_order": (1, 0, 0), "arima_seasonal_order": (0, 0, 0, 0)}),
        ("arima", "arima_1_1_1", {"arima_order": (1, 1, 1), "arima_seasonal_order": (0, 0, 0, 0)}),
        ("arima", "sarima_1_0_0_7", {"arima_order": (1, 0, 0), "arima_seasonal_order": (1, 0, 0, 7)}),
    ]
    prophet_grid = [
        ("prophet", "prophet_default", {}),
        (
            "prophet",
            "prophet_weekly_only",
            {"yearly_seasonality": False, "weekly_seasonality": True, "daily_seasonality": False},
        ),
    ]
    lstm_grid = [
        ("lstm", "lstm_h32_l2_e15", {"lstm_hidden_dim": 32, "lstm_num_layers": 2, "lstm_epochs": 15}),
    ]
    return baselines + arima_grid + prophet_grid + lstm_grid


def get_default_nhsn_grid():
    baselines = [
        ("baseline", "naive", {}),
        ("baseline", "moving_average_w4", {"window": 4}),
        ("baseline", "moving_average_w12", {"window": 12}),
        ("baseline", "seasonal_naive_p52", {"seasonal_period": 52}),
    ]
    arima_grid = [
        ("arima", "arima_1_0_0", {"arima_order": (1, 0, 0), "arima_seasonal_order": (0, 0, 0, 0)}),
        ("arima", "arima_1_1_1", {"arima_order": (1, 1, 1), "arima_seasonal_order": (0, 0, 0, 0)}),
    ]
    prophet_grid = [
        (
            "prophet",
            "prophet_yearly_only",
            {"yearly_seasonality": True, "weekly_seasonality": False, "daily_seasonality": False},
        ),
    ]
    lstm_grid = [
        ("lstm", "lstm_h32_l2_e15", {"lstm_hidden_dim": 32, "lstm_num_layers": 2, "lstm_epochs": 15}),
    ]
    return baselines + arima_grid + prophet_grid + lstm_grid


class BenchmarkEvaluator:
    """
    Evaluates saved experiment runs across all configurations, performs leakage-free
    model selection, and exports reproducible benchmark reports and leaderboards.
    """

    def __init__(
        self,
        runs_dirs: list[str] | None = None,
        output_dir: str = "backend/ml/evaluations",
    ):
        if runs_dirs is None:
            self.runs_dirs = [
                "backend/ml/runs",
                "backend/backend/ml/runs",
                "ml/runs",
            ]
        else:
            self.runs_dirs = runs_dirs
        self.output_dir = output_dir

    def load_runs(self) -> list[ExperimentRun]:
        """Loads and deduplicates all valid experiment runs from specified run directories."""
        loaded_runs: dict[str, ExperimentRun] = {}

        for dir_path in self.runs_dirs:
            p = Path(dir_path)
            if not p.exists() or not p.is_dir():
                continue

            for json_file in p.glob("*.json"):
                try:
                    with open(json_file, encoding="utf-8") as f:
                        data = json.load(f)
                    run = ExperimentRun.model_validate(data)
                    if run.run_id not in loaded_runs:
                        loaded_runs[run.run_id] = run
                except Exception as e:
                    logger.debug("Could not parse %s as ExperimentRun: %s", json_file, e)

        return list(loaded_runs.values())

    def run_benchmark_evaluation(
        self,
        runs: list[ExperimentRun] | None = None,
    ) -> BenchmarkSelectionReport:
        """Runs model selection across Hero DMC and NHSN HRD benchmark configurations."""
        if runs is None:
            runs = self.load_runs()

        selector = ModelSelector()
        comparisons: list[SelectionComparison] = []
        total_successful = 0
        total_failed_or_missing = 0

        # 1. Hero DMC: Daily Admissions for horizons 1d, 7d, 14d, 30d
        hero_grid = get_default_hero_dmc_grid()
        for h in [1, 7, 14, 30]:
            comp = selector.compare_and_select(
                runs=runs,
                dataset_name="hero_dmc",
                target_column="daily_admissions",
                horizon=h,
                horizon_unit="d",
                expected_grid=hero_grid,
            )
            comparisons.append(comp)
            total_successful += len([e for e in comp.leaderboard if e.status == "SUCCESS"])
            total_failed_or_missing += len([e for e in comp.leaderboard if e.status != "SUCCESS"])

        # 2. NHSN HRD: Weekly ICU Beds Occupied for horizons 1w, 2w, 4w
        nhsn_grid = get_default_nhsn_grid()
        for h in [1, 2, 4]:
            comp = selector.compare_and_select(
                runs=runs,
                dataset_name="nhsn_hrd",
                target_column="icu_beds_occupied",
                horizon=h,
                horizon_unit="w",
                expected_grid=nhsn_grid,
            )
            comparisons.append(comp)
            total_successful += len([e for e in comp.leaderboard if e.status == "SUCCESS"])
            total_failed_or_missing += len([e for e in comp.leaderboard if e.status != "SUCCESS"])

        report = BenchmarkSelectionReport(
            report_id=str(uuid.uuid4()),
            generated_at=datetime.now(UTC),
            comparisons=comparisons,
            total_runs_evaluated=len(runs),
            successful_runs=total_successful,
            failed_or_missing_runs=total_failed_or_missing,
        )

        return report

    def save_report(
        self,
        report: BenchmarkSelectionReport,
    ) -> tuple[str, str]:
        """Saves benchmark selection report to JSON and Markdown summary table."""
        os.makedirs(self.output_dir, exist_ok=True)

        json_path = os.path.join(self.output_dir, "model_selection_report.json")
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(report.model_dump_json(indent=2))

        md_path = os.path.join(self.output_dir, "model_selection_summary.md")
        md_content = self.generate_markdown_summary(report)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        return json_path, md_path

    def generate_markdown_summary(self, report: BenchmarkSelectionReport) -> str:
        """Builds clean, structured Markdown benchmark summary tables."""
        lines = [
            "# HospitalOps AI — Forecasting Benchmark & Model Selection Report",
            "",
            f"> **Generated at:** {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}  ",
            f"> **Report ID:** `{report.report_id}`  ",
            f"> **Total Runs Evaluated:** {report.total_runs_evaluated}  ",
            "",
            "## 1. Selected Winner Summary",
            "",
            "All models were evaluated using chronological walk-forward splits. **Selection was performed strictly on validation MAE (tie-breaker: validation RMSE).** Held-out test split metrics are reported for transparent, unbiased generalization verification.",
            "",
            "| Dataset | Target | Horizon | Winner Model | Winner Config | Val MAE | Test MAE | Test RMSE | Test sMAPE | Test MAPE |",
            "|:---|:---|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|",
        ]

        for comp in report.comparisons:
            w = comp.winner
            ds = comp.dataset_name.upper()
            tgt = comp.target_column
            h_str = f"{comp.horizon}{comp.horizon_unit}"

            if w and w.val_metrics:
                v_mae = f"{w.val_metrics.mae:.2f}"
                t_mae = f"{w.test_metrics.mae:.2f}" if w.test_metrics else "N/A"
                t_rmse = f"{w.test_metrics.rmse:.2f}" if w.test_metrics else "N/A"
                t_smape = f"{w.test_metrics.smape:.2f}%" if (w.test_metrics and w.test_metrics.smape is not None) else "N/A"
                t_mape = f"{w.test_metrics.mape:.2f}%" if (w.test_metrics and w.test_metrics.mape is not None) else "N/A"
                lines.append(
                    f"| {ds} | `{tgt}` | **{h_str}** | **{w.model_type.upper()}** | `{w.config_name}` | {v_mae} | {t_mae} | {t_rmse} | {t_smape} | {t_mape} |"
                )
            else:
                lines.append(
                    f"| {ds} | `{tgt}` | **{h_str}** | *None* | *No valid runs* | N/A | N/A | N/A | N/A | N/A |"
                )

        lines.extend([
            "",
            "---",
            "",
            "## 2. Detailed Leaderboard per Horizon",
            "",
        ])

        for comp in report.comparisons:
            ds = comp.dataset_name.upper()
            tgt = comp.target_column
            h_str = f"{comp.horizon}{comp.horizon_unit}"
            lines.extend([
                f"### {ds} — {tgt} (Horizon: {h_str})",
                "",
                "| Rank | Status | Model Type | Configuration | Val MAE | Val RMSE | Test MAE | Test RMSE | Test sMAPE | Test MAPE |",
                "|:---:|:---:|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|",
            ])

            for e in comp.leaderboard:
                status_icon = "✅" if e.status == "SUCCESS" else ("❌" if e.status == "FAILED" else "⚠️")
                rank_str = str(e.rank) if e.rank is not None else "-"
                v_mae = f"{e.val_metrics.mae:.2f}" if e.val_metrics else "-"
                v_rmse = f"{e.val_metrics.rmse:.2f}" if e.val_metrics else "-"
                t_mae = f"{e.test_metrics.mae:.2f}" if e.test_metrics else "-"
                t_rmse = f"{e.test_metrics.rmse:.2f}" if e.test_metrics else "-"
                t_smape = f"{e.test_metrics.smape:.2f}%" if (e.test_metrics and e.test_metrics.smape is not None) else "-"
                t_mape = f"{e.test_metrics.mape:.2f}%" if (e.test_metrics and e.test_metrics.mape is not None) else "-"

                lines.append(
                    f"| {rank_str} | {status_icon} {e.status} | {e.model_type} | `{e.config_name}` | {v_mae} | {v_rmse} | {t_mae} | {t_rmse} | {t_smape} | {t_mape} |"
                )

            lines.append("")

        return "\n".join(lines)
