"""
HospitalOps AI — Forecasting API Tests (Milestone 2, Chunk 2.7).

Verifies forecast generation, validation-based model selection resolution,
ICU capacity projections, occupancy guardrails, benchmark retrieval,
RBAC security, and numerical robustness.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user, get_forecast_service, get_user_repository
from app.main import app
from app.ml.contracts.config import FeatureConfig, ForecastConfig, SplitConfig
from app.ml.contracts.evaluation import EvaluationMetrics
from app.ml.contracts.experiment import ExperimentRun
from app.ml.contracts.forecast import ForecastResult
from app.models.user import Role, UserDocument
from app.services.forecast import ForecastService

# ── Mock Users & Fixtures ─────────────────────────────────────────────────────


def _get_mock_admin() -> UserDocument:
    return UserDocument(
        user_id="admin_fc_test",
        email="admin@hospitalops.local",
        name="Admin User",
        password_hash="argon2id$mock",
        role=Role.ADMIN,
    )


def _get_mock_doctor() -> UserDocument:
    return UserDocument(
        user_id="doc_fc_test",
        email="doc@hospitalops.local",
        name="Dr. Doctor",
        password_hash="argon2id$mock",
        role=Role.DOCTOR,
        department_id="DEPT-EMERGENCY",
    )


@pytest.fixture
def mock_forecast_service():
    """Provides a ForecastService pointing to genuine existing runs & benchmark report."""
    service = ForecastService(
        admissions_repo=AsyncMock(),
        capacity_repo=AsyncMock(),
        runs_dirs=["backend/ml/runs", "backend/backend/ml/runs", "ml/runs"],
        evaluations_dir="backend/ml/evaluations",
    )
    return service


@pytest.fixture(autouse=True)
def setup_test_dependencies(mock_forecast_service):
    """Ensures forecast service and mock repos are injected and overrides are cleared after each test."""
    app.dependency_overrides[get_forecast_service] = lambda: mock_forecast_service
    app.dependency_overrides[get_user_repository] = lambda: AsyncMock()
    yield
    app.dependency_overrides.clear()


# ── 1. Admissions Forecast Tests ──────────────────────────────────────────────


def test_get_admissions_forecast_default_winner():
    """Tests GET /api/v1/forecast/admissions resolves validation winner and returns daily points."""
    app.dependency_overrides[get_current_user] = _get_mock_admin

    client = TestClient(app)
    response = client.get("/api/v1/forecast/admissions?horizon=7")

    assert response.status_code == 200
    payload = response.json()
    assert "data" in payload
    assert "meta" in payload
    data = payload["data"]

    assert data["status"] == "SUCCESS"
    assert data["metadata"]["dataset_name"] == "hero_dmc"
    assert data["metadata"]["target_column"] == "daily_admissions"
    assert data["metadata"]["target_units"] == "admissions"
    assert data["metadata"]["frequency"] == "D"
    assert data["metadata"]["horizon"] == 7
    assert data["metadata"]["horizon_unit"] == "d"
    assert data["metadata"]["selection_criterion"] == "val_mae"
    assert data["metadata"]["validation_mae"] is not None

    # Length of predictions must match requested horizon
    assert len(data["predictions"]) == 7
    for pt in data["predictions"]:
        assert "timestamp" in pt
        assert isinstance(pt["value"], int | float)
        # Non-MC models do not fabricate confidence bounds
        assert pt["lower_bound"] is None
        assert pt["upper_bound"] is None


def test_get_admissions_forecast_model_override():
    """Tests GET /api/v1/forecast/admissions with explicit model_type override."""
    app.dependency_overrides[get_current_user] = _get_mock_doctor

    client = TestClient(app)
    response = client.get("/api/v1/forecast/admissions?horizon=1&model_type=baseline")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["metadata"]["model_type"] == "baseline"
    assert len(data["predictions"]) == 1


def test_get_admissions_forecast_invalid_horizon():
    """Verifies horizon boundaries (must be between 1 and 30 days)."""
    app.dependency_overrides[get_current_user] = _get_mock_admin

    client = TestClient(app)
    resp_zero = client.get("/api/v1/forecast/admissions?horizon=0")
    assert resp_zero.status_code == 422

    resp_over = client.get("/api/v1/forecast/admissions?horizon=31")
    assert resp_over.status_code == 422


def test_get_admissions_forecast_invalid_model_type():
    """Verifies that arbitrary unsupported model types are rejected with 422."""
    app.dependency_overrides[get_current_user] = _get_mock_admin

    client = TestClient(app)
    response = client.get("/api/v1/forecast/admissions?horizon=7&model_type=xgboost_unsupported")
    assert response.status_code == 422
    assert "is invalid" in response.json()["detail"]


# ── 2. ICU Capacity Forecast Tests ────────────────────────────────────────────


def test_get_icu_forecast_weekly_cadence():
    """Tests GET /api/v1/forecast/icu returns weekly cadence in physical bed units."""
    app.dependency_overrides[get_current_user] = _get_mock_admin

    client = TestClient(app)
    response = client.get("/api/v1/forecast/icu?horizon=2")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["metadata"]["dataset_name"] == "nhsn_hrd"
    assert data["metadata"]["target_column"] == "icu_beds_occupied"
    assert data["metadata"]["target_units"] == "beds"
    assert data["metadata"]["frequency"] == "W"
    assert data["metadata"]["horizon"] == 2
    assert data["metadata"]["horizon_unit"] == "w"
    assert len(data["predictions"]) == 2

    for pt in data["predictions"]:
        assert isinstance(pt["value"], int | float)


def test_get_icu_forecast_horizon_boundaries():
    """Verifies ICU horizon boundaries (1 to 8 weeks)."""
    app.dependency_overrides[get_current_user] = _get_mock_admin

    client = TestClient(app)
    resp_under = client.get("/api/v1/forecast/icu?horizon=0")
    assert resp_under.status_code == 422

    resp_over = client.get("/api/v1/forecast/icu?horizon=9")
    assert resp_over.status_code == 422


# ── 3. Occupancy Forecast Guardrail Tests ──────────────────────────────────────


def test_get_occupancy_forecast_returns_unsupported():
    """Verifies GET /api/v1/forecast/occupancy rejects requests without fabricating synthetic numbers."""
    app.dependency_overrides[get_current_user] = _get_mock_admin

    client = TestClient(app)
    response = client.get("/api/v1/forecast/occupancy?horizon=7")

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "Occupancy rate forecasting is currently unsupported" in detail
    assert "A reliable occupancy forecast requires concurrent occupied beds" in detail


# ── 4. Benchmarks & Evaluation Reports Tests ──────────────────────────────────


def test_get_benchmarks_all_comparisons():
    """Tests GET /api/v1/forecast/benchmarks retrieves comparisons and leaderboards."""
    app.dependency_overrides[get_current_user] = _get_mock_admin

    client = TestClient(app)
    response = client.get("/api/v1/forecast/benchmarks")

    assert response.status_code == 200
    report = response.json()["data"]
    assert "report_id" in report
    assert "comparisons" in report
    assert len(report["comparisons"]) > 0

    first_comp = report["comparisons"][0]
    assert "winner" in first_comp
    assert "leaderboard" in first_comp
    assert first_comp["winner"]["val_metrics"]["mae"] is not None

    # Verify split separation: both val_metrics and test_metrics are present
    assert "val_metrics" in first_comp["winner"]
    assert "test_metrics" in first_comp["winner"]


def test_get_benchmarks_filter_by_dataset():
    """Tests GET /api/v1/forecast/benchmarks?dataset_name=nhsn_hrd filters correctly."""
    app.dependency_overrides[get_current_user] = _get_mock_admin

    client = TestClient(app)
    response = client.get("/api/v1/forecast/benchmarks?dataset_name=nhsn_hrd")

    assert response.status_code == 200
    report = response.json()["data"]
    for comp in report["comparisons"]:
        assert comp["dataset_name"] == "nhsn_hrd"


def test_get_benchmarks_filter_no_match():
    """Tests filtering with non-existent criteria returns empty comparisons cleanly."""
    app.dependency_overrides[get_current_user] = _get_mock_admin

    client = TestClient(app)
    response = client.get("/api/v1/forecast/benchmarks?dataset_name=non_existent_dataset")

    assert response.status_code == 200
    report = response.json()["data"]
    assert len(report["comparisons"]) == 0


# ── 5. Saved Runs List & Detail Tests ─────────────────────────────────────────


def test_list_saved_runs_with_pagination():
    """Tests GET /api/v1/forecast/runs lists historical runs with pagination."""
    app.dependency_overrides[get_current_user] = _get_mock_admin

    client = TestClient(app)
    response = client.get("/api/v1/forecast/runs?page=1&page_size=5")

    assert response.status_code == 200
    payload = response.json()
    assert "data" in payload
    assert len(payload["data"]) <= 5
    assert "pagination" in payload["meta"]
    assert payload["meta"]["pagination"]["page"] == 1
    assert payload["meta"]["pagination"]["page_size"] == 5


def test_get_saved_run_by_id():
    """Tests GET /api/v1/forecast/runs/{run_id} returns exact experiment run details."""
    app.dependency_overrides[get_current_user] = _get_mock_admin

    client = TestClient(app)
    list_resp = client.get("/api/v1/forecast/runs?page=1&page_size=1")
    runs = list_resp.json()["data"]
    if runs:
        run_id = runs[0]["run_id"]
        detail_resp = client.get(f"/api/v1/forecast/runs/{run_id}")
        assert detail_resp.status_code == 200
        run_data = detail_resp.json()["data"]
        assert run_data["run_id"] == run_id
        assert "config" in run_data

    # Test unknown run ID
    unknown_resp = client.get("/api/v1/forecast/runs/non-existent-run-id-999")
    assert unknown_resp.status_code == 404


# ── 6. Authentication & RBAC Security Tests ───────────────────────────────────


def test_forecast_endpoints_require_authentication():
    """Verifies that requests without authentication headers return 401."""
    client = TestClient(app)
    resp_admissions = client.get("/api/v1/forecast/admissions")
    assert resp_admissions.status_code == 401

    resp_icu = client.get("/api/v1/forecast/icu")
    assert resp_icu.status_code == 401

    resp_benchmarks = client.get("/api/v1/forecast/benchmarks")
    assert resp_benchmarks.status_code == 401


def test_forecast_endpoints_require_permission_predictions_read():
    """Verifies that users without 'predictions.read' permission are rejected with 403."""
    from app.core.security import ROLE_PERMISSIONS

    original_perms = ROLE_PERMISSIONS[Role.DOCTOR]
    ROLE_PERMISSIONS[Role.DOCTOR] = [p for p in original_perms if p != "predictions.read"]

    try:
        app.dependency_overrides[get_current_user] = _get_mock_doctor
        client = TestClient(app)
        response = client.get("/api/v1/forecast/admissions?horizon=7")
        assert response.status_code == 403
        assert "predictions.read" in response.json()["detail"]
    finally:
        ROLE_PERMISSIONS[Role.DOCTOR] = original_perms


# ── 7. Numerical Robustness & No-Leak Guardrail ───────────────────────────────


def test_numerical_robustness_non_finite_handling(mock_forecast_service):
    """Verifies non-finite numbers (NaN/Inf) are handled without crashes or corrupted serialization."""
    now_dt = datetime.now(UTC)
    bad_run = ExperimentRun(
        run_id="bad-run-nan",
        dataset_name="hero_dmc",
        config=ForecastConfig(
            dataset_name="hero_dmc",
            target_column="daily_admissions",
            horizon=2,
            baseline_model_type="naive",
            features=FeatureConfig(),
            split=SplitConfig(),
        ),
        forecasts=[
            ForecastResult(
                dataset_name="hero_dmc",
                target="daily_admissions",
                model_name="naive",
                split_name="test",
                horizon=2,
                metrics=EvaluationMetrics(mae=1.0, rmse=1.0),
                forecast_timestamps=["2025-01-01", "2025-01-02"],
                predictions=[float("nan"), float("inf")],
            )
        ],
        created_at=now_dt,
    )

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        mock_forecast_service._build_forecast_response_from_run(
            run=bad_run,
            dataset_name="hero_dmc",
            target_column="daily_admissions",
            target_units="admissions",
            frequency="D",
            horizon=2,
            horizon_unit="d",
        )

    assert exc_info.value.status_code == 502
    assert "non-finite prediction value" in exc_info.value.detail


def test_forecast_includes_verified_historical_points():
    """Verifies that forecast responses include real historical points leading up to origin."""
    app.dependency_overrides[get_current_user] = _get_mock_admin

    client = TestClient(app)
    response = client.get("/api/v1/forecast/admissions?horizon=7")

    assert response.status_code == 200
    data = response.json()["data"]

    assert "historical_points" in data
    assert len(data["historical_points"]) > 0
    # Every point has valid timestamp and numerical value
    for pt in data["historical_points"]:
        assert "timestamp" in pt
        assert isinstance(pt["value"], int | float)
        assert pt["value"] >= 0
