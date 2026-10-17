import json
import logging
import os
import tempfile
from typing import Any

import pandas as pd

from app.ml.contracts.experiment import ExperimentRun
from app.ml.contracts.model import ForecastModel
from app.ml.tracking.base import ExperimentTracker

logger = logging.getLogger(__name__)

# List of prohibited clinical/PHI keys to prevent leaking sensitive patient records
PROHIBITED_PHI_KEYWORDS = {
    "patient_id",
    "subject_id",
    "hadm_id",
    "stay_id",
    "patient_name",
    "ssn",
    "mrn",
    "medical_record_number",
    "diagnosis",
    "notes",
    "clinical_text",
}


def sanitize_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively removes sensitive keys and credentials from dictionary payloads."""
    cleaned = {}
    for k, v in data.items():
        k_lower = k.lower()
        if any(phi in k_lower for phi in PROHIBITED_PHI_KEYWORDS):
            continue
        if "secret" in k_lower or "password" in k_lower or "token" in k_lower or "key" in k_lower:
            continue
        if isinstance(v, dict):
            cleaned[k] = sanitize_dict(v)
        elif isinstance(v, list):
            cleaned[k] = [sanitize_dict(item) if isinstance(item, dict) else item for item in v]
        else:
            cleaned[k] = v
    return cleaned


def log_experiment_artifacts(tracker: ExperimentTracker, experiment: ExperimentRun) -> None:
    """
    Serializes and logs experiment artifacts to the tracking provider:
    - Sanitized configuration JSON
    - Evaluation metrics summary JSON
    - Prediction-vs-actual CSV for each split
    """
    if not tracker.is_enabled or tracker.active_run_id is None:
        return

    with tempfile.TemporaryDirectory() as tmp_dir:
        # 1. Configuration artifact
        config_dict = sanitize_dict(experiment.config.model_dump())
        tracker.log_dict(config_dict, "config.json")

        # 2. Evaluation Summary artifact
        summary_payload = {
            "run_id": experiment.run_id,
            "dataset_name": experiment.dataset_name,
            "pipeline_version": experiment.pipeline_version,
            "forecasts": [
                {
                    "split_name": f.split_name,
                    "model_name": f.model_name,
                    "horizon": f.horizon,
                    "metrics": f.metrics.model_dump(),
                    "high_demand_metrics": f.high_demand_metrics.model_dump()
                    if f.high_demand_metrics
                    else None,
                }
                for f in experiment.forecasts
            ],
        }
        tracker.log_dict(summary_payload, "evaluation_summary.json")

        # 3. Predictions vs Actuals table
        for forecast in experiment.forecasts:
            if forecast.forecast_timestamps and forecast.predictions and forecast.actuals:
                df_preds = pd.DataFrame(
                    {
                        "timestamp": forecast.forecast_timestamps,
                        "actual": forecast.actuals,
                        "predicted": forecast.predictions,
                    }
                )
                df_preds["absolute_error"] = (df_preds["actual"] - df_preds["predicted"]).abs()

                csv_filename = f"predictions_{forecast.split_name}.csv"
                csv_path = os.path.join(tmp_dir, csv_filename)
                df_preds.to_csv(csv_path, index=False)
                tracker.log_artifact(csv_path, artifact_path="predictions")


def log_model_artifact(
    tracker: ExperimentTracker,
    model: ForecastModel,
    model_name: str,
) -> None:
    """
    Safely serializes and logs supported model artifacts without crashing if unsupported.
    """
    if not tracker.is_enabled or tracker.active_run_id is None:
        return

    with tempfile.TemporaryDirectory() as tmp_dir:
        # PyTorch LSTM
        if hasattr(model, "model") and hasattr(model.model, "state_dict"):
            try:
                import torch
                model_path = os.path.join(tmp_dir, "model.pt")
                torch.save(model.model.state_dict(), model_path)
                tracker.log_artifact(model_path, artifact_path="model")

                # Log metadata
                meta_path = os.path.join(tmp_dir, "lstm_architecture.json")
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "hidden_dim": getattr(model, "hidden_dim", None),
                            "num_layers": getattr(model, "num_layers", None),
                            "sequence_length": getattr(model, "sequence_length", None),
                            "horizon": getattr(model, "horizon", None),
                        },
                        f,
                        indent=2,
                    )
                tracker.log_artifact(meta_path, artifact_path="model")
            except Exception as e:
                logger.warning("Failed to serialize PyTorch model: %s", e)

        # Baseline Models
        elif model_name in ["naive", "seasonal_naive", "moving_average"]:
            meta_path = os.path.join(tmp_dir, f"{model_name}_config.json")
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump({"model_class": model.__class__.__name__}, f, indent=2)
            tracker.log_artifact(meta_path, artifact_path="model")
