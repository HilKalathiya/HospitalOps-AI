from typing import Literal

import numpy as np
from pydantic import BaseModel
from sklearn.metrics import mean_absolute_error, root_mean_squared_error


class EvaluationMetrics(BaseModel):
    """Standardized metrics for forecasting evaluation in original target units."""

    mae: float
    rmse: float
    smape: float | None = None
    mape: float | None = None


def calculate_mae(y_true, y_pred) -> float:
    """Calculates Mean Absolute Error in original physical target units."""
    y_true_arr = np.asarray(y_true, dtype=float)
    y_pred_arr = np.asarray(y_pred, dtype=float)
    valid = ~np.isnan(y_true_arr) & ~np.isnan(y_pred_arr)
    if not np.any(valid):
        return 0.0
    return float(mean_absolute_error(y_true_arr[valid], y_pred_arr[valid]))


def calculate_rmse(y_true, y_pred) -> float:
    """Calculates Root Mean Squared Error in original physical target units."""
    y_true_arr = np.asarray(y_true, dtype=float)
    y_pred_arr = np.asarray(y_pred, dtype=float)
    valid = ~np.isnan(y_true_arr) & ~np.isnan(y_pred_arr)
    if not np.any(valid):
        return 0.0
    return float(root_mean_squared_error(y_true_arr[valid], y_pred_arr[valid]))


def safe_smape(y_true, y_pred) -> float:
    """
    Calculates symmetric Mean Absolute Percentage Error.
    Safe against division by zero.
    Returns value in [0, 200] range, or 0 if both are 0.
    """
    y_true = np.array(y_true, dtype=float)
    y_pred = np.array(y_pred, dtype=float)

    denominator = np.abs(y_true) + np.abs(y_pred)
    # Mask where denominator is 0
    mask = denominator == 0

    # Avoid div by zero
    diff = np.abs(y_true - y_pred)

    result = np.zeros_like(diff)
    result[~mask] = 200.0 * diff[~mask] / denominator[~mask]

    return float(np.mean(result))


def safe_mape(
    y_true,
    y_pred,
    zero_handling: Literal["filter", "epsilon", "raise"] = "filter",
    epsilon: float = 1e-8,
) -> float | None:
    """
    Calculates Mean Absolute Percentage Error (MAPE) in [0, 100]% scale with explicit zero handling.

    Parameters:
    - y_true: Ground truth values.
    - y_pred: Predicted values.
    - zero_handling:
        * 'filter': Computes MAPE exclusively on points where |y_true| > epsilon.
                    If all y_true are near-zero and all y_pred are near-zero, returns 0.0%.
                    If all y_true are near-zero and y_pred has non-zero predictions, returns None
                    to prevent silently fabricating undefined 0.0% or infinite percentage error.
        * 'epsilon': Computes MAPE with max(|y_true|, epsilon) in the denominator.
        * 'raise': Raises ValueError if any |y_true| <= epsilon.
    - epsilon: Tolerance threshold for zero detection.
    """
    y_true_arr = np.asarray(y_true, dtype=float)
    y_pred_arr = np.asarray(y_pred, dtype=float)

    # Filter out NaNs
    valid = ~np.isnan(y_true_arr) & ~np.isnan(y_pred_arr)
    y_t = y_true_arr[valid]
    y_p = y_pred_arr[valid]

    if len(y_t) == 0:
        return None

    near_zero_true = np.abs(y_t) <= epsilon

    if zero_handling == "raise":
        if np.any(near_zero_true):
            raise ValueError("Zero or near-zero values found in actuals for MAPE calculation.")
        return float(np.mean(np.abs((y_t - y_p) / y_t)) * 100.0)

    elif zero_handling == "epsilon":
        denom = np.maximum(np.abs(y_t), epsilon)
        return float(np.mean(np.abs(y_t - y_p) / denom) * 100.0)

    elif zero_handling == "filter":
        non_zero_mask = ~near_zero_true
        if not np.any(non_zero_mask):
            # All actuals are near zero
            near_zero_pred = np.abs(y_p) <= epsilon
            if np.all(near_zero_pred):
                return 0.0
            return None

        # Calculate MAPE over valid non-zero actual points
        errors = np.abs((y_t[non_zero_mask] - y_p[non_zero_mask]) / y_t[non_zero_mask])
        return float(np.mean(errors) * 100.0)

    else:
        raise ValueError(f"Unknown zero_handling mode: {zero_handling}")


def calculate_all_metrics(
    y_true,
    y_pred,
    zero_handling: Literal["filter", "epsilon", "raise"] = "filter",
    epsilon: float = 1e-8,
) -> EvaluationMetrics:
    """Calculates MAE, RMSE, sMAPE, and MAPE for paired predictions and ground truth."""
    mae = calculate_mae(y_true, y_pred)
    rmse = calculate_rmse(y_true, y_pred)
    smape = safe_smape(y_true, y_pred)
    mape = safe_mape(y_true, y_pred, zero_handling=zero_handling, epsilon=epsilon)
    return EvaluationMetrics(mae=mae, rmse=rmse, smape=smape, mape=mape)
