from pydantic import BaseModel


class EvaluationMetrics(BaseModel):
    """Standardized metrics for forecasting evaluation in original target units."""

    mae: float
    rmse: float
    smape: float | None = None


def safe_smape(y_true, y_pred) -> float:
    """
    Calculates symmetric Mean Absolute Percentage Error.
    Safe against division by zero.
    Returns value in [0, 200] range, or 0 if both are 0.
    """
    import numpy as np

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
