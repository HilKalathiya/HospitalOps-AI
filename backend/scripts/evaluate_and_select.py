import argparse
import logging
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.ml.selection.benchmark import BenchmarkEvaluator  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evaluate_and_select")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Model Evaluation and Leakage-Free Selection on Benchmark Runs"
    )
    parser.add_argument(
        "--output-dir",
        default="backend/ml/evaluations",
        help="Directory to save selection report JSON and Markdown summary",
    )
    args = parser.parse_args()

    evaluator = BenchmarkEvaluator(output_dir=args.output_dir)
    logger.info("Loading experiment runs from default run directories...")
    runs = evaluator.load_runs()
    logger.info("Found %d distinct experiment runs.", len(runs))

    if not runs:
        logger.warning("No experiment runs found! Please ensure runs exist in backend/ml/runs.")

    logger.info("Evaluating models and selecting winners per horizon...")
    report = evaluator.run_benchmark_evaluation(runs)

    json_path, md_path = evaluator.save_report(report)
    logger.info("Saved report JSON to: %s", json_path)
    logger.info("Saved Markdown summary to: %s", md_path)

    print("\n" + "=" * 80)
    print("MODEL SELECTION SUMMARY")
    print("=" * 80)
    for comp in report.comparisons:
        w = comp.winner
        h_str = f"{comp.horizon}{comp.horizon_unit}"
        if w and w.val_metrics:
            t_mae = f"{w.test_metrics.mae:.2f}" if w.test_metrics else "N/A"
            t_mape = f"{w.test_metrics.mape:.2f}%" if (w.test_metrics and w.test_metrics.mape is not None) else "N/A"
            print(
                f"[{comp.dataset_name.upper():8}] Horizon: {h_str:4} | Winner: {w.model_type.upper():8} ({w.config_name:20}) | Val MAE: {w.val_metrics.mae:.2f} | Test MAE: {t_mae} | Test MAPE: {t_mape}"
            )
        else:
            print(f"[{comp.dataset_name.upper():8}] Horizon: {h_str:4} | No valid runs found.")
    print("=" * 80)


if __name__ == "__main__":
    main()
