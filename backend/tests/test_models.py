"""
HospitalOps AI — Domain model validation tests.

Tests Pydantic model construction and validation for all 8 core domain models.
These are pure unit tests — no database or network dependencies.

Coverage:
  - Valid construction of all model types
  - Invalid enum values rejected
  - Invalid field constraints rejected (negative numbers, etc.)
  - Timestamp UTC-awareness
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.models.admission import (
    AdmissionCreate,
    AdmissionSeverity,
    AdmissionStatus,
    AdmissionType,
    AdmissionUpdate,
)
from app.models.alert import (
    AlertCreate,
    AlertSeverity,
    AlertStatus,
    AlertType,
    AlertUpdate,
)
from app.models.audit_log import ActorType, AuditLogCreate
from app.models.bed import BedCreate, BedStatus, BedType, BedUpdate
from app.models.department import DepartmentCreate, DepartmentType, DepartmentUpdate
from app.models.patient import (
    Gender,
    PatientAdmissionStatus,
    PatientCreate,
    PatientUpdate,
    Severity,
)
from app.models.prediction import PredictionCreate, PredictionPoint, PredictionType
from app.models.resource import (
    ResourceCreate,
    ResourceCriticality,
    ResourceStatus,
    ResourceType,
    ResourceUpdate,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def utc() -> datetime:
    """Return current UTC datetime for use in tests."""
    return datetime.now(tz=UTC)


# ── Department ────────────────────────────────────────────────────────────────


class TestDepartmentModel:
    """Tests for the Department Pydantic models."""

    def test_valid_department_create(self) -> None:
        dept = DepartmentCreate(
            name="Intensive Care Unit",
            code="ICU",
            department_type=DepartmentType.ICU,
            capacity=20,
        )
        assert dept.name == "Intensive Care Unit"
        assert dept.code == "ICU"
        assert dept.department_type == DepartmentType.ICU
        assert dept.capacity == 20
        assert dept.is_active is True  # default

    def test_department_with_optional_fields(self) -> None:
        dept = DepartmentCreate(
            name="Emergency Department",
            code="ER",
            department_type=DepartmentType.EMERGENCY,
            description="24/7 emergency care",
            location="Block A, Ground Floor",
        )
        assert dept.description == "24/7 emergency care"
        assert dept.location == "Block A, Ground Floor"

    def test_department_invalid_type(self) -> None:
        with pytest.raises(ValidationError):
            DepartmentCreate(
                name="Test",
                code="T",
                department_type="INVALID_TYPE",  # type: ignore[arg-type]
            )

    def test_department_negative_capacity_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DepartmentCreate(
                name="Test",
                code="T",
                department_type=DepartmentType.OTHER,
                capacity=-1,
            )

    def test_department_zero_capacity_allowed(self) -> None:
        dept = DepartmentCreate(
            name="Test",
            code="T",
            department_type=DepartmentType.OTHER,
            capacity=0,
        )
        assert dept.capacity == 0

    def test_department_update_partial(self) -> None:
        update = DepartmentUpdate(name="Updated Name")
        assert update.name == "Updated Name"
        assert update.is_active is None  # not provided

    def test_department_all_types_valid(self) -> None:
        for dept_type in DepartmentType:
            dept = DepartmentCreate(
                name=f"Dept {dept_type.value}",
                code=dept_type.value[:5],
                department_type=dept_type,
            )
            assert dept.department_type == dept_type


# ── Patient ───────────────────────────────────────────────────────────────────


class TestPatientModel:
    """Tests for the Patient Pydantic models."""

    def test_valid_patient_create(self) -> None:
        patient = PatientCreate(name="John Smith")
        assert patient.name == "John Smith"
        assert patient.gender == Gender.UNKNOWN  # default
        assert patient.icu_required is False  # default

    def test_patient_with_all_fields(self) -> None:
        patient = PatientCreate(
            name="Jane Doe",
            external_patient_id="MRN-001",
            date_of_birth="1980-05-15",
            gender=Gender.FEMALE,
            diagnosis_category="Cardiac",
            severity=Severity.HIGH,
            department_id="dept-icu-001",
            icu_required=True,
        )
        assert patient.external_patient_id == "MRN-001"
        assert patient.gender == Gender.FEMALE
        assert patient.severity == Severity.HIGH
        assert patient.icu_required is True

    def test_patient_invalid_gender(self) -> None:
        with pytest.raises(ValidationError):
            PatientCreate(
                name="Test",
                gender="NONBINARY",  # type: ignore[arg-type] — not in enum
            )

    def test_patient_invalid_severity(self) -> None:
        with pytest.raises(ValidationError):
            PatientCreate(
                name="Test",
                severity="EXTREME",  # type: ignore[arg-type]
            )

    def test_all_genders_valid(self) -> None:
        for gender in Gender:
            p = PatientCreate(name="Test", gender=gender)
            assert p.gender == gender

    def test_all_severities_valid(self) -> None:
        for severity in Severity:
            p = PatientCreate(name="Test", severity=severity)
            assert p.severity == severity

    def test_all_admission_statuses_valid(self) -> None:
        for status in PatientAdmissionStatus:
            u = PatientUpdate(admission_status=status)
            assert u.admission_status == status


# ── Admission ─────────────────────────────────────────────────────────────────


class TestAdmissionModel:
    """Tests for the Admission Pydantic models."""

    def test_valid_admission_create(self) -> None:
        admission = AdmissionCreate(
            patient_id="pat-001",
            department_id="dept-icu-001",
            admission_type=AdmissionType.EMERGENCY,
            severity=AdmissionSeverity.CRITICAL,
            icu_required=True,
            admitted_at=utc(),
        )
        assert admission.patient_id == "pat-001"
        assert admission.admission_type == AdmissionType.EMERGENCY
        assert admission.severity == AdmissionSeverity.CRITICAL
        assert admission.icu_required is True

    def test_admission_default_admitted_at_is_utc(self) -> None:
        admission = AdmissionCreate(
            patient_id="pat-001",
            department_id="dept-001",
            admission_type=AdmissionType.ELECTIVE,
            severity=AdmissionSeverity.LOW,
        )
        assert admission.admitted_at.tzinfo is not None

    def test_admission_invalid_type(self) -> None:
        with pytest.raises(ValidationError):
            AdmissionCreate(
                patient_id="pat-001",
                department_id="dept-001",
                admission_type="WALK_IN",  # type: ignore[arg-type]
                severity=AdmissionSeverity.LOW,
            )

    def test_all_admission_types_valid(self) -> None:
        for atype in AdmissionType:
            a = AdmissionCreate(
                patient_id="p", department_id="d",
                admission_type=atype, severity=AdmissionSeverity.MEDIUM,
            )
            assert a.admission_type == atype

    def test_all_admission_statuses_valid(self) -> None:
        for status in AdmissionStatus:
            u = AdmissionUpdate(status=status)
            assert u.status == status


# ── Bed ───────────────────────────────────────────────────────────────────────


class TestBedModel:
    """Tests for the Bed Pydantic models."""

    def test_valid_bed_create(self) -> None:
        bed = BedCreate(
            department_id="dept-icu-001",
            bed_type=BedType.ICU,
            room="ICU-01",
            floor="3",
        )
        assert bed.bed_type == BedType.ICU
        assert bed.room == "ICU-01"

    def test_bed_invalid_type(self) -> None:
        with pytest.raises(ValidationError):
            BedCreate(
                department_id="dept-001",
                bed_type="LUXURY",  # type: ignore[arg-type]
            )

    def test_all_bed_statuses_valid(self) -> None:
        for status in BedStatus:
            u = BedUpdate(status=status)
            assert u.status == status

    def test_all_bed_types_valid(self) -> None:
        for bed_type in BedType:
            b = BedCreate(department_id="dept-001", bed_type=bed_type)
            assert b.bed_type == bed_type


# ── Resource ──────────────────────────────────────────────────────────────────


class TestResourceModel:
    """Tests for the Resource Pydantic models."""

    def test_valid_resource_create(self) -> None:
        resource = ResourceCreate(
            name="Ventilator A",
            resource_type=ResourceType.VENTILATOR,
            quantity_total=10,
            quantity_available=8,
            quantity_reserved=2,
        )
        assert resource.name == "Ventilator A"
        assert resource.quantity_total == 10

    def test_resource_quantity_constraint_violated(self) -> None:
        """available + reserved > total should be rejected."""
        with pytest.raises(ValidationError):
            ResourceCreate(
                name="Test",
                resource_type=ResourceType.MONITOR,
                quantity_total=5,
                quantity_available=4,
                quantity_reserved=3,  # 4 + 3 = 7 > 5
            )

    def test_resource_negative_quantity_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ResourceCreate(
                name="Test",
                resource_type=ResourceType.OXYGEN,
                quantity_total=-1,
                quantity_available=0,
            )

    def test_resource_zero_quantities_valid(self) -> None:
        r = ResourceCreate(
            name="Test",
            resource_type=ResourceType.OTHER,
            quantity_total=0,
            quantity_available=0,
        )
        assert r.quantity_total == 0

    def test_all_resource_types_valid(self) -> None:
        for rtype in ResourceType:
            r = ResourceCreate(
                name="Test", resource_type=rtype,
                quantity_total=1, quantity_available=1,
            )
            assert r.resource_type == rtype

    def test_all_criticality_levels_valid(self) -> None:
        for criticality in ResourceCriticality:
            u = ResourceUpdate(criticality=criticality)
            assert u.criticality == criticality

    def test_all_resource_statuses_valid(self) -> None:
        for status in ResourceStatus:
            u = ResourceUpdate(status=status)
            assert u.status == status


# ── Prediction ────────────────────────────────────────────────────────────────


class TestPredictionModel:
    """Tests for the Prediction Pydantic models."""

    def test_valid_prediction_point(self) -> None:
        point = PredictionPoint(
            timestamp=utc(),
            value=87.5,
            lower_bound=82.0,
            upper_bound=93.0,
            confidence=0.95,
        )
        assert point.value == 87.5
        assert point.confidence == 0.95

    def test_confidence_out_of_range_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PredictionPoint(
                timestamp=utc(),
                value=50.0,
                lower_bound=45.0,
                upper_bound=55.0,
                confidence=1.5,  # > 1.0 — invalid
            )

    def test_negative_confidence_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PredictionPoint(
                timestamp=utc(),
                value=50.0,
                lower_bound=45.0,
                upper_bound=55.0,
                confidence=-0.1,  # < 0.0 — invalid
            )

    def test_valid_prediction_create(self) -> None:
        now = utc()
        prediction = PredictionCreate(
            prediction_type=PredictionType.ICU_DEMAND,
            forecast_start=now,
            forecast_end=now,
            generated_at=now,
            model_name="LSTM_v1",
            model_version="1.0.0",
            predictions=[
                PredictionPoint(
                    timestamp=now, value=15.0,
                    lower_bound=12.0, upper_bound=18.0,
                    confidence=0.9,
                ),
            ],
        )
        assert prediction.prediction_type == PredictionType.ICU_DEMAND
        assert len(prediction.predictions) == 1

    def test_all_prediction_types_valid(self) -> None:
        now = utc()
        for ptype in PredictionType:
            p = PredictionCreate(
                prediction_type=ptype,
                forecast_start=now, forecast_end=now, generated_at=now,
                model_name="test", model_version="1.0",
            )
            assert p.prediction_type == ptype


# ── Alert ─────────────────────────────────────────────────────────────────────


class TestAlertModel:
    """Tests for the Alert Pydantic models."""

    def test_valid_alert_create(self) -> None:
        alert = AlertCreate(
            alert_type=AlertType.BED_SHORTAGE,
            severity=AlertSeverity.HIGH,
            title="ICU Bed Shortage",
            message="ICU occupancy has reached 90%",
            triggered_at=utc(),
        )
        assert alert.alert_type == AlertType.BED_SHORTAGE
        assert alert.severity == AlertSeverity.HIGH

    def test_alert_default_triggered_at_is_utc(self) -> None:
        alert = AlertCreate(
            alert_type=AlertType.SYSTEM,
            severity=AlertSeverity.INFO,
            title="Test",
            message="Test message",
        )
        assert alert.triggered_at.tzinfo is not None

    def test_alert_invalid_severity(self) -> None:
        with pytest.raises(ValidationError):
            AlertCreate(
                alert_type=AlertType.SYSTEM,
                severity="EXTREME",  # type: ignore[arg-type]
                title="Test",
                message="Test",
            )

    def test_all_alert_statuses_valid(self) -> None:
        for status in AlertStatus:
            u = AlertUpdate(status=status)
            assert u.status == status

    def test_all_alert_types_valid(self) -> None:
        for atype in AlertType:
            a = AlertCreate(
                alert_type=atype,
                severity=AlertSeverity.INFO,
                title="Test",
                message="Test",
            )
            assert a.alert_type == atype


# ── Audit Log ─────────────────────────────────────────────────────────────────


class TestAuditLogModel:
    """Tests for the AuditLog Pydantic models."""

    def test_valid_audit_log_create(self) -> None:
        entry = AuditLogCreate(
            actor_type=ActorType.SYSTEM,
            actor_id="system",
            action="ADMISSION_CREATED",
            entity_type="admission",
            entity_id="adm-001",
            timestamp=utc(),
        )
        assert entry.actor_type == ActorType.SYSTEM
        assert entry.action == "ADMISSION_CREATED"

    def test_audit_log_with_details(self) -> None:
        entry = AuditLogCreate(
            actor_type=ActorType.AGENT,
            actor_id="agent-run-abc123",
            action="RECOMMENDATION_CREATED",
            entity_type="recommendation",
            entity_id="rec-001",
            request_id="550e8400-e29b-41d4-a716-446655440000",
            details={"beds_available": 3, "threshold": 5},
            timestamp=utc(),
        )
        assert entry.actor_type == ActorType.AGENT
        assert entry.details is not None
        assert entry.details["beds_available"] == 3

    def test_all_actor_types_valid(self) -> None:
        for actor_type in ActorType:
            entry = AuditLogCreate(
                actor_type=actor_type,
                actor_id="test-actor",
                action="TEST_ACTION",
                entity_type="test",
                entity_id="test-001",
                timestamp=utc(),
            )
            assert entry.actor_type == actor_type

    def test_audit_log_invalid_actor_type(self) -> None:
        with pytest.raises(ValidationError):
            AuditLogCreate(
                actor_type="ROBOT",  # type: ignore[arg-type]
                actor_id="r2d2",
                action="TEST",
                entity_type="test",
                entity_id="t-001",
                timestamp=utc(),
            )


# ── Timestamp UTC enforcement ─────────────────────────────────────────────────


class TestTimestampBehaviour:
    """Verify that auto-generated timestamps are always UTC-aware."""

    def test_department_update_has_utc_timestamp(self) -> None:
        update = DepartmentUpdate(name="Test")
        assert update.updated_at.tzinfo is not None
        assert update.updated_at.tzinfo == UTC

    def test_admission_create_default_admitted_at_utc(self) -> None:
        admission = AdmissionCreate(
            patient_id="p", department_id="d",
            admission_type=AdmissionType.OTHER,
            severity=AdmissionSeverity.LOW,
        )
        assert admission.admitted_at.tzinfo is not None

    def test_alert_create_default_triggered_at_utc(self) -> None:
        alert = AlertCreate(
            alert_type=AlertType.SYSTEM,
            severity=AlertSeverity.INFO,
            title="T", message="M",
        )
        assert alert.triggered_at.tzinfo is not None
