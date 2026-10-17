import numpy as np
import pandas as pd
import pytest

from app.ml.contracts.config import FeatureConfig, ForecastConfig, SplitConfig
from app.ml.contracts.dataset import MLDataset
from app.ml.contracts.evaluation import (
    EvaluationMetrics,
    calculate_all_metrics,
    calculate_mae,
    calculate_rmse,
    safe_mape,
    safe_smape,
)
from app.ml.contracts.experiment import ExperimentRun
from app.ml.contracts.forecast import ForecastResult
from app.ml.contracts.selection import BenchmarkSelectionReport
from app.ml.pipelines.orchestrator import MLPipelineOrchestrator
from app.ml.selection.benchmark import BenchmarkEvaluator
from app.ml.selection.selector import ModelSelector

# ==============================================================================
# 1. Metric Correctness Tests
# ==============================================================================


def test_metric_correctness_known_examples():
    """Validates MAE, RMSE, sMAPE, and MAPE against hand-calculated values."""
    y_true = [10.0, 20.0, 30.0, 40.0]
    y_pred = [12.0, 18.0, 33.0, 36.0]

    # Errors: [2, 2, 3, 4] -> sum = 11 -> MAE = 11/4 = 2.75
    mae = calculate_mae(y_true, y_pred)
    assert mae == pytest.approx(2.75, abs=1e-5)

    # Squared errors: [4, 4, 9, 16] -> sum = 33 -> RMSE = sqrt(33/4) = sqrt(8.25) ~= 2.87228
    rmse = calculate_rmse(y_true, y_pred)
    assert rmse == pytest.approx(np.sqrt(8.25), abs=1e-5)

    # MAPE: [2/10, 2/20, 3/30, 4/40] = [0.2, 0.1, 0.1, 0.1] -> mean = 0.125 -> 12.5%
    mape = safe_mape(y_true, y_pred)
    assert mape == pytest.approx(12.5, abs=1e-5)

    # sMAPE: 200 * diff / (y_t + y_p):
    # i=0: 200 * 2 / 22 = 18.1818%
    # i=1: 200 * 2 / 38 = 10.5263%
    # i=2: 200 * 3 / 63 = 9.5238%
    # i=3: 200 * 4 / 76 = 10.5263%
    # mean ~= 12.1895%
    smape = safe_smape(y_true, y_pred)
    assert smape == pytest.approx(12.1895, abs=1e-3)

    # calculate_all_metrics
    metrics = calculate_all_metrics(y_true, y_pred)
    assert isinstance(metrics, EvaluationMetrics)
    assert metrics.mae == pytest.approx(2.75)
    assert metrics.rmse == pytest.approx(np.sqrt(8.25))
    assert metrics.mape == pytest.approx(12.5)
    assert metrics.smape == pytest.approx(12.1895, abs=1e-3)


# ==============================================================================
# 2. Zero-Valued Actuals & Percentage Metrics Tests
# ==============================================================================


def test_safe_mape_zero_handling_all_zeros():
    """Tests behavior when all ground truth actuals are zero."""
    y_true_zero = [0.0, 0.0, 0.0]
    y_pred_zero = [0.0, 0.0, 0.0]
    y_pred_nonzero = [1.0, 2.0, 0.5]

    # Perfect prediction on zero actuals returns 0.0%
    assert safe_mape(y_true_zero, y_pred_zero, zero_handling="filter") == 0.0

    # Non-zero predictions on all-zero actuals returns None (undefined error, not 0% or inf)
    assert safe_mape(y_true_zero, y_pred_nonzero, zero_handling="filter") is None

    # Epsilon mode provides bounded positive error
    eps_mape = safe_mape(y_true_zero, y_pred_nonzero, zero_handling="epsilon", epsilon=1.0)
    assert eps_mape is not None
    assert eps_mape > 0.0

    # Raise mode raises ValueError
    with pytest.raises(ValueError, match="Zero or near-zero"):
        safe_mape(y_true_zero, y_pred_nonzero, zero_handling="raise")


def test_safe_mape_zero_handling_mixed_zeros():
    """Tests MAPE when actuals contain a mix of zeros and positive values."""
    y_true = [0.0, 10.0, 20.0, 0.0]
    y_pred = [2.0, 11.0, 18.0, 0.0]

    # Filter mode evaluates on non-zero actuals [10.0, 20.0] with preds [11.0, 18.0]:
    # |10-11|/10 = 0.1, |20-18|/20 = 0.1 -> mean = 10.0%
    mape_filtered = safe_mape(y_true, y_pred, zero_handling="filter")
    assert mape_filtered == pytest.approx(10.0, abs=1e-5)


def test_safe_smape_zero_handling():
    """Validates safe_smape handles zeros without division by zero errors."""
    y_true = [0.0, 0.0]
    y_pred = [0.0, 0.0]
    assert safe_smape(y_true, y_pred) == 0.0

    y_true_mix = [0.0, 10.0]
    y_pred_mix = [0.0, 10.0]
    assert safe_smape(y_true_mix, y_pred_mix) == 0.0


# ==============================================================================
# 3. Leakage-Free Selection & Test Split Isolation Tests
# ==============================================================================


def test_leakage_free_model_selection():
    """
    Adversarial test:
    Model A has worse validation MAE (10.0) but better test MAE (1.0).
    Model B has better validation MAE (4.0) but worse test MAE (15.0).

    Strict leakage-free selection MUST select Model B based on validation metrics only.
    Test performance must NEVER leak into selection.
    """
    config_a = ForecastConfig(
        dataset_name="hero_dmc",
        target_column="daily_admissions",
        features=FeatureConfig(),
        split=SplitConfig(),
        model_type="arima",
        horizon=7,
    )
    run_a = ExperimentRun(
        run_id="run-a",
        dataset_name="hero_dmc",
        config=config_a,
        forecasts=[
            ForecastResult(
                dataset_name="hero_dmc",
                target="daily_admissions",
                model_name="arima",
                split_name="validation",
                horizon=7,
                metrics=EvaluationMetrics(mae=10.0, rmse=12.0, smape=20.0, mape=18.0),
            ),
            ForecastResult(
                dataset_name="hero_dmc",
                target="daily_admissions",
                model_name="arima",
                split_name="test",
                horizon=7,
                metrics=EvaluationMetrics(mae=1.0, rmse=1.2, smape=2.0, mape=1.8),
            ),
        ],
    )

    config_b = ForecastConfig(
        dataset_name="hero_dmc",
        target_column="daily_admissions",
        features=FeatureConfig(),
        split=SplitConfig(),
        model_type="baseline",
        baseline_model_type="moving_average",
        baseline_model_kwargs={"window": 7},
        horizon=7,
    )
    run_b = ExperimentRun(
        run_id="run-b",
        dataset_name="hero_dmc",
        config=config_b,
        forecasts=[
            ForecastResult(
                dataset_name="hero_dmc",
                target="daily_admissions",
                model_name="moving_average",
                split_name="validation",
                horizon=7,
                metrics=EvaluationMetrics(mae=4.0, rmse=5.0, smape=8.0, mape=7.5),
            ),
            ForecastResult(
                dataset_name="hero_dmc",
                target="daily_admissions",
                model_name="moving_average",
                split_name="test",
                horizon=7,
                metrics=EvaluationMetrics(mae=15.0, rmse=18.0, smape=30.0, mape=28.0),
            ),
        ],
    )

    selector = ModelSelector(primary_metric="val_mae")
    comp = selector.compare_and_select(
        runs=[run_a, run_b],
        dataset_name="hero_dmc",
        target_column="daily_admissions",
        horizon=7,
    )

    # Model B MUST be selected as winner despite having worse test MAE!
    assert comp.winner is not None
    assert comp.winner.config_name == "moving_average_w7"
    assert comp.winner.val_metrics.mae == 4.0
    # Winner's test metrics are transparently reported, but had zero influence on selection
    assert comp.winner.test_metrics.mae == 15.0
    assert comp.leaderboard[0].config_name == "moving_average_w7"
    assert comp.leaderboard[1].config_name == "arima_1_0_0"


# ==============================================================================
# 4. Consistency Across Models & Horizon Compatibility Tests
# ==============================================================================


def test_horizon_and_dataset_partitioning():
    """Ensures incompatible runs (different horizon or dataset) are strictly filtered out."""
    cfg_7d = ForecastConfig(
        dataset_name="hero_dmc",
        target_column="daily_admissions",
        features=FeatureConfig(),
        split=SplitConfig(),
        horizon=7,
    )
    run_7d = ExperimentRun(
        run_id="run-7d",
        dataset_name="hero_dmc",
        config=cfg_7d,
        forecasts=[
            ForecastResult(
                dataset_name="hero_dmc",
                target="daily_admissions",
                model_name="naive",
                split_name="validation",
                horizon=7,
                metrics=EvaluationMetrics(mae=5.0, rmse=6.0),
            )
        ],
    )

    cfg_14d = ForecastConfig(
        dataset_name="hero_dmc",
        target_column="daily_admissions",
        features=FeatureConfig(),
        split=SplitConfig(),
        horizon=14,
    )
    run_14d = ExperimentRun(
        run_id="run-14d",
        dataset_name="hero_dmc",
        config=cfg_14d,
        forecasts=[
            ForecastResult(
                dataset_name="hero_dmc",
                target="daily_admissions",
                model_name="naive",
                split_name="validation",
                horizon=14,
                metrics=EvaluationMetrics(mae=1.0, rmse=1.2),
            )
        ],
    )

    selector = ModelSelector()
    comp = selector.compare_and_select(
        runs=[run_7d, run_14d],
        dataset_name="hero_dmc",
        target_column="daily_admissions",
        horizon=7,
    )

    # Only run_7d should be evaluated for horizon 7
    assert len([e for e in comp.leaderboard if e.status == "SUCCESS"]) == 1
    assert comp.winner.val_metrics.mae == 5.0


# ==============================================================================
# 5. Missing and Failed Runs Representation Tests
# ==============================================================================


def test_missing_and_failed_runs_explicitly_represented():
    """Verifies that missing and failed runs are explicitly represented with status and error message."""
    cfg_fail = ForecastConfig(
        dataset_name="nhsn_hrd",
        target_column="icu_beds_occupied",
        features=FeatureConfig(),
        split=SplitConfig(),
        model_type="prophet",
        horizon=1,
    )
    run_fail = ExperimentRun(
        run_id="run-fail",
        dataset_name="nhsn_hrd",
        config=cfg_fail,
        status="FAILED",
        forecasts=[],
    )

    expected_grid = [
        ("prophet", "prophet_default", {}),
        ("baseline", "naive", {}),
    ]

    selector = ModelSelector()
    comp = selector.compare_and_select(
        runs=[run_fail],
        dataset_name="nhsn_hrd",
        target_column="icu_beds_occupied",
        horizon=1,
        expected_grid=expected_grid,
    )

    assert comp.winner is None
    status_map = {e.config_name: e.status for e in comp.leaderboard}
    assert status_map["prophet_default"] == "FAILED"
    assert status_map["naive"] == "MISSING"


# ==============================================================================
# 6. Benchmark Report Serialization & Persistence Tests
# ==============================================================================


def test_benchmark_evaluator_report_persistence(tmp_path):
    """Verifies BenchmarkEvaluator creates, validates, and serializes report artifacts."""
    output_dir = str(tmp_path / "evaluations")
    evaluator = BenchmarkEvaluator(
        runs_dirs=["backend/backend/ml/runs", "backend/ml/runs"],
        output_dir=output_dir,
    )

    runs = evaluator.load_runs()
    assert len(runs) > 0, "Saved runs should be discovered from repository"

    report = evaluator.run_benchmark_evaluation(runs)
    assert isinstance(report, BenchmarkSelectionReport)
    assert len(report.comparisons) == 7  # 4 for Hero DMC, 3 for NHSN HRD

    json_path, md_path = evaluator.save_report(report)
    assert (tmp_path / "evaluations" / "model_selection_report.json").exists()
    assert (tmp_path / "evaluations" / "model_selection_summary.md").exists()

    # Verify JSON deserialization roundtrip
    with open(json_path, encoding="utf-8") as f:
        loaded_report = BenchmarkSelectionReport.model_validate_json(f.read())
    assert loaded_report.report_id == report.report_id
    assert len(loaded_report.comparisons) == 7


# ==============================================================================
# 7. Orchestrator Integration with MAPE
# ==============================================================================


def test_orchestrator_integration_metrics():
    """Verifies that MLPipelineOrchestrator computes MAPE and includes it in ForecastResult."""
    dates = pd.date_range("2025-01-01", periods=60, freq="D")
    df = pd.DataFrame(
        {
            "date": dates,
            "daily_admissions": np.linspace(10, 50, 60) + np.sin(np.arange(60)) * 5,
        }
    )
    dataset = MLDataset(
        dataset_name="hero_dmc",
        source_collection="test",
        df=df,
        target_column="daily_admissions",
        time_column="date",
        frequency="D",
        metadata={},
    )

    config = ForecastConfig(
        dataset_name="hero_dmc",
        target_column="daily_admissions",
        features=FeatureConfig(lags=[1, 7], rolling_windows=[7]),
        split=SplitConfig(train_ratio=0.7, val_ratio=0.15, test_ratio=0.15),
        baseline_model_type="naive",
        horizon=1,
    )

    orchestrator = MLPipelineOrchestrator(config)
    exp = orchestrator.run(dataset)

    assert exp.status == "COMPLETED"
    assert len(exp.forecasts) == 2  # Validation and Test

    val_forecast = next(f for f in exp.forecasts if f.split_name == "validation")
    test_forecast = next(f for f in exp.forecasts if f.split_name == "test")

    assert val_forecast.metrics.mape is not None
    assert val_forecast.metrics.mape > 0.0
    assert test_forecast.metrics.mape is not None
    assert test_forecast.metrics.mape > 0.0
