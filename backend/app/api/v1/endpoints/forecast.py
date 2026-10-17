"""
HospitalOps AI — Forecasting API Endpoints (Chunk 2.7).

Exposes validated operational demand forecasts, ICU capacity projections,
model evaluation benchmarks, and experiment artifacts.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from app.api.dependencies import get_forecast_service, require_permission
from app.ml.contracts.experiment import ExperimentRun
from app.models.user import UserDocument
from app.schemas.common import PaginationMeta, ResponseMeta, SuccessResponse
from app.schemas.forecast import (
    BenchmarkReportResponse,
    ExperimentRunSummary,
    ForecastResponse,
)
from app.services.forecast import ForecastService

router = APIRouter()


# ── Forecast Endpoints ────────────────────────────────────────────────────────


@router.get(
    "/admissions",
    response_model=SuccessResponse[ForecastResponse],
    status_code=status.HTTP_200_OK,
    summary="Daily admission demand forecast",
)
async def get_admissions_forecast(
    current_user: Annotated[UserDocument, Depends(require_permission("predictions.read"))],
    service: Annotated[ForecastService, Depends(get_forecast_service)],
    horizon: int = Query(7, ge=1, le=30, description="Forecast horizon in days (1 to 30)"),
    model_type: str | None = Query(
        None, description="Optional model family override: baseline, arima, prophet, lstm"
    ),
    run_id: str | None = Query(None, description="Optional specific saved run ID to retrieve"),
) -> SuccessResponse[ForecastResponse]:
    """
    Returns future daily admission predictions for the Hero DMC benchmark series.
    The default model resolves strictly from validation-based model selection.
    """
    result = await service.get_admissions_forecast(
        horizon=horizon,
        model_type=model_type,
        run_id=run_id,
        dataset_name="hero_dmc",
    )
    return SuccessResponse(data=result)


@router.get(
    "/icu",
    response_model=SuccessResponse[ForecastResponse],
    status_code=status.HTTP_200_OK,
    summary="Weekly ICU bed capacity forecast",
)
async def get_icu_forecast(
    current_user: Annotated[UserDocument, Depends(require_permission("predictions.read"))],
    service: Annotated[ForecastService, Depends(get_forecast_service)],
    horizon: int = Query(2, ge=1, le=8, description="Forecast horizon in weeks (1 to 8)"),
    model_type: str | None = Query(
        None, description="Optional model family override: baseline, arima, prophet, lstm"
    ),
    run_id: str | None = Query(None, description="Optional specific saved run ID to retrieve"),
) -> SuccessResponse[ForecastResponse]:
    """
    Returns future weekly occupied ICU bed predictions from NHSN HRD.
    Preserves weekly cadence and physical bed units.
    """
    result = await service.get_icu_forecast(
        horizon=horizon,
        model_type=model_type,
        run_id=run_id,
        dataset_name="nhsn_hrd",
    )
    return SuccessResponse(data=result)


@router.get(
    "/occupancy",
    response_model=SuccessResponse[ForecastResponse],
    status_code=status.HTTP_200_OK,
    summary="Hospital occupancy forecast",
)
async def get_occupancy_forecast(
    current_user: Annotated[UserDocument, Depends(require_permission("predictions.read"))],
    service: Annotated[ForecastService, Depends(get_forecast_service)],
    horizon: int = Query(7, ge=1, le=30, description="Requested forecast horizon"),
    dataset_name: str | None = Query(None, description="Requested dataset identifier"),
    target_column: str | None = Query(None, description="Requested occupancy target"),
) -> SuccessResponse[ForecastResponse]:
    """
    Evaluates whether a valid occupancy rate forecast is supported.
    Returns clear 400 error rather than inventing ungrounded occupancy values.
    """
    result = service.get_occupancy_forecast(
        horizon=horizon,
        dataset_name=dataset_name,
        target_column=target_column,
    )
    return SuccessResponse(data=result)


# ── Benchmark & History Endpoints ─────────────────────────────────────────────


@router.get(
    "/benchmarks",
    response_model=SuccessResponse[BenchmarkReportResponse],
    status_code=status.HTTP_200_OK,
    summary="Model evaluation benchmarks and selection report",
)
async def get_benchmarks(
    current_user: Annotated[UserDocument, Depends(require_permission("predictions.read"))],
    service: Annotated[ForecastService, Depends(get_forecast_service)],
    dataset_name: str | None = Query(None, description="Filter by dataset: 'hero_dmc', 'nhsn_hrd'"),
    target_column: str | None = Query(None, description="Filter by target column"),
    horizon: int | None = Query(None, ge=1, description="Filter by horizon"),
) -> SuccessResponse[BenchmarkReportResponse]:
    """
    Retrieves reproducible model evaluation benchmarks across walk-forward splits.
    Includes validation selection winners and held-out test generalization metrics.
    """
    report = service.get_benchmarks(
        dataset_name=dataset_name,
        target_column=target_column,
        horizon=horizon,
    )
    return SuccessResponse(data=report)


@router.get(
    "/runs",
    response_model=SuccessResponse[list[ExperimentRunSummary]],
    status_code=status.HTTP_200_OK,
    summary="List historical experiment runs",
)
async def list_runs(
    current_user: Annotated[UserDocument, Depends(require_permission("predictions.read"))],
    service: Annotated[ForecastService, Depends(get_forecast_service)],
    dataset_name: str | None = Query(None, description="Filter by dataset"),
    target_column: str | None = Query(None, description="Filter by target"),
    model_type: str | None = Query(None, description="Filter by model type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> SuccessResponse[list[ExperimentRunSummary]]:
    """Lists saved experiment runs with pagination and filters."""
    skip = (page - 1) * page_size
    runs, total = service.list_saved_runs(
        dataset_name=dataset_name,
        target_column=target_column,
        model_type=model_type,
        skip=skip,
        limit=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    pagination = PaginationMeta(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )
    return SuccessResponse(data=runs, meta=ResponseMeta(pagination=pagination))


@router.get(
    "/runs/{run_id}",
    response_model=SuccessResponse[ExperimentRun],
    status_code=status.HTTP_200_OK,
    summary="Get detailed experiment run artifact",
)
async def get_run_by_id(
    run_id: Annotated[str, Path(description="Experiment run identifier")],
    current_user: Annotated[UserDocument, Depends(require_permission("predictions.read"))],
    service: Annotated[ForecastService, Depends(get_forecast_service)],
) -> SuccessResponse[ExperimentRun]:
    """Retrieves full details of a specific experiment run."""
    run = service.get_saved_run_by_id(run_id)
    return SuccessResponse(data=run)
