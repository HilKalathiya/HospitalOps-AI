"""
HospitalOps AI — Prediction domain model.

Collection: predictions

Persistence model for ML forecast results. This is NOT the ML implementation —
it defines only how forecast outputs are stored and retrieved.

A prediction document stores the output of a single model inference run:
  - the forecast type (what was predicted)
  - the model that produced it
  - the time range covered
  - a list of time-series prediction points with confidence bounds

The ML layer (future chunk) writes prediction documents.
The API/service layer reads them. Agents query the latest prediction
of each type for their reasoning context.
"""

from datetime import datetime
from enum import Enum

from pydantic import Field

from app.models.base import HospitalOpsBaseModel, TimestampedModel

# ── Enums ─────────────────────────────────────────────────────────────────────


class PredictionType(str, Enum):
    """
    What the prediction is forecasting.
    Maps to the integration contracts defined in docs/architecture/integration-contracts.md.
    """

    ICU_DEMAND = "ICU_DEMAND"  # Predicted ICU bed demand
    BED_OCCUPANCY = "BED_OCCUPANCY"  # Predicted overall bed occupancy %
    ADMISSION_VOLUME = "ADMISSION_VOLUME"  # Predicted admission count


# ── Sub-models ────────────────────────────────────────────────────────────────


class PredictionPoint(HospitalOpsBaseModel):
    """
    A single time-series prediction point.
    Represents the model's output for a specific future timestamp.

    Stored as an embedded array within a PredictionDocument.
    """

    timestamp: datetime = Field(description="UTC timestamp this point represents.")
    value: float = Field(description="Predicted value at this timestamp.")
    lower_bound: float = Field(description="Lower bound of the confidence interval.")
    upper_bound: float = Field(description="Upper bound of the confidence interval.")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Model confidence at this point (0.0–1.0).",
    )


# ── Internal MongoDB document model ───────────────────────────────────────────


class PredictionDocument(TimestampedModel):
    """
    Internal representation of a prediction document as stored in MongoDB.
    Repository layer only — never exposed directly to API consumers.

    Key design decisions:
    - predictions: list[PredictionPoint] is stored as an embedded array.
      This avoids a separate time-series collection for MVP scale.
      For high-frequency/high-resolution forecasts, a dedicated time-series
      collection may be warranted in a future chunk.
    - department_id: None for hospital-wide forecasts (e.g., total bed occupancy).
    - model_version allows querying predictions from a specific model run.
    """

    id: str = Field(alias="_id", description="MongoDB document ID (string ObjectId).")
    prediction_id: str = Field(description="Stable application-level prediction identifier.")
    prediction_type: PredictionType = Field(description="What this prediction is forecasting.")
    department_id: str | None = Field(
        default=None,
        description="Reference to departments.department_id. "
        "None for hospital-wide predictions.",
    )
    forecast_start: datetime = Field(description="UTC start of the forecast horizon.")
    forecast_end: datetime = Field(description="UTC end of the forecast horizon.")
    generated_at: datetime = Field(description="UTC timestamp when the model was run.")
    model_name: str = Field(
        max_length=200, description="Name of the ML model that generated this prediction."
    )
    model_version: str = Field(max_length=50, description="Version identifier of the model.")
    predictions: list[PredictionPoint] = Field(
        default_factory=list,
        description="Time-series prediction points, ordered by timestamp ascending.",
    )
    overall_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Overall model confidence for this prediction run.",
    )
    metadata: dict | None = Field(
        default=None,
        description="Additional model-specific metadata (feature importances, etc.).",
    )


# ── API-facing schemas ────────────────────────────────────────────────────────


class PredictionCreate(HospitalOpsBaseModel):
    """Fields required to store a new prediction result."""

    prediction_type: PredictionType
    department_id: str | None = None
    forecast_start: datetime
    forecast_end: datetime
    generated_at: datetime
    model_name: str = Field(max_length=200)
    model_version: str = Field(max_length=50)
    predictions: list[PredictionPoint] = Field(default_factory=list)
    overall_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    metadata: dict | None = None


class PredictionResponse(HospitalOpsBaseModel):
    """Prediction fields returned to API consumers."""

    prediction_id: str
    prediction_type: PredictionType
    department_id: str | None
    forecast_start: datetime
    forecast_end: datetime
    generated_at: datetime
    model_name: str
    model_version: str
    predictions: list[PredictionPoint]
    overall_confidence: float | None
    metadata: dict | None
    created_at: datetime
    updated_at: datetime
