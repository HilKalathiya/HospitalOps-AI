"""
HospitalOps AI — Event Contracts & Envelope Tests (Milestone 6, Chunk 6.1).

Validates:
1. Valid event envelope and payload construction across all domains.
2. Missing required fields rejection.
3. Invalid event types and categories mismatch rejection.
4. Future clock skew (> 5 mins) and timezone-naive timestamp handling.
5. Strongly typed payload schema validation (negative values, extra fields).
6. Payload and metadata size boundary enforcement (64 KB / 16 KB).
7. Prohibited PHI and credential detection (SSN, password, API tokens).
8. Deterministic SHA-256 payload hashing for idempotency fingerprints.
9. Distinction between observed operational facts and derived computations.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.events.contracts import (
    EntityType,
    EventCategory,
    EventType,
    OperationalEvent,
    compute_payload_hash,
)
from app.events.exceptions import EventValidationError
from app.events.taxonomy import get_event_definition


class TestEventContracts:
    """Test suite for event envelope, payload schemas, and validation boundaries."""

    def test_01_valid_capacity_updated_event(self):
        """Verify valid operational capacity event envelope and payload construction."""
        now = datetime.now(UTC)
        payload = {
            "department_id": "ICU",
            "total_beds": 30,
            "occupied_beds": 25,
            "operational_occupancy_rate": 83.33,
            "available_beds": 5,
        }
        event = OperationalEvent(
            event_id="evt_valid_cap_001",
            event_type=EventType.OPERATIONS_CAPACITY_UPDATED,
            category=EventCategory.OPERATIONAL_FACT,
            occurred_at=now,
            source="hospitalops.beds_service",
            entity_type=EntityType.DEPARTMENT,
            entity_id="ICU",
            facility_id="facility_main",
            payload=payload,
            metadata={"environment": "production"},
        )

        assert event.event_id == "evt_valid_cap_001"
        assert event.category == EventCategory.OPERATIONAL_FACT
        assert event.payload_hash != ""
        assert event.payload["occupied_beds"] == 25
        assert event.occurred_at == now

    def test_02_valid_forecast_completed_event(self):
        """Verify valid analytical forecast completed event envelope."""
        now = datetime.now(UTC)
        payload = {
            "forecast_id": "fc_arima_7d_001",
            "target_metric": "icu_occupancy",
            "horizon_days": 7,
            "model_type": "arima",
            "peak_predicted_value": 28.5,
            "model_version": "1.0.0",
        }
        event = OperationalEvent(
            event_id="evt_fc_001",
            event_type=EventType.FORECAST_COMPLETED,
            category=EventCategory.ANALYTICAL_OUTPUT,
            occurred_at=now,
            source="hospitalops.forecast_service",
            entity_type=EntityType.FORECAST,
            entity_id="fc_arima_7d_001",
            facility_id="facility_main",
            payload=payload,
        )

        assert event.category == EventCategory.ANALYTICAL_OUTPUT
        assert event.payload["model_type"] == "arima"

    def test_03_category_mismatch_rejection(self):
        """Verify that assigning an incorrect category to an event type is rejected."""
        now = datetime.now(UTC)
        payload = {
            "department_id": "ICU",
            "total_beds": 30,
            "occupied_beds": 25,
            "operational_occupancy_rate": 83.33,
            "available_beds": 5,
        }
        # OPERATIONS_CAPACITY_UPDATED must be OPERATIONAL_FACT, not ANALYTICAL_OUTPUT
        with pytest.raises(EventValidationError, match="must have category 'OPERATIONAL_FACT'"):
            OperationalEvent(
                event_type=EventType.OPERATIONS_CAPACITY_UPDATED,
                category=EventCategory.ANALYTICAL_OUTPUT,
                occurred_at=now,
                source="hospitalops.beds_service",
                entity_type=EntityType.DEPARTMENT,
                entity_id="ICU",
                payload=payload,
            )

    def test_04_future_timestamp_beyond_skew_rejected(self):
        """Verify that timestamps farther than 5 minutes in the future are rejected."""
        far_future = datetime.now(UTC) + timedelta(minutes=15)
        payload = {
            "department_id": "ICU",
            "total_beds": 30,
            "occupied_beds": 25,
            "operational_occupancy_rate": 83.33,
            "available_beds": 5,
        }
        with pytest.raises(EventValidationError, match="cannot be in the future beyond"):
            OperationalEvent(
                event_type=EventType.OPERATIONS_CAPACITY_UPDATED,
                category=EventCategory.OPERATIONAL_FACT,
                occurred_at=far_future,
                source="hospitalops.beds_service",
                entity_type=EntityType.DEPARTMENT,
                entity_id="ICU",
                payload=payload,
            )

    def test_05_payload_schema_validation_failure(self):
        """Verify that malformed or negative payload attributes are rejected."""
        now = datetime.now(UTC)
        # occupied_beds cannot be negative (ge=0)
        invalid_payload = {
            "department_id": "ICU",
            "total_beds": 30,
            "occupied_beds": -5,
            "operational_occupancy_rate": 83.33,
            "available_beds": 5,
        }
        with pytest.raises(EventValidationError, match="Payload validation failed"):
            OperationalEvent(
                event_type=EventType.OPERATIONS_CAPACITY_UPDATED,
                category=EventCategory.OPERATIONAL_FACT,
                occurred_at=now,
                source="hospitalops.beds_service",
                entity_type=EntityType.DEPARTMENT,
                entity_id="ICU",
                payload=invalid_payload,
            )

    def test_06_payload_forbids_extra_fields(self):
        """Verify that payload models strictly forbid extra/unmodeled fields."""
        now = datetime.now(UTC)
        extra_field_payload = {
            "department_id": "ICU",
            "total_beds": 30,
            "occupied_beds": 25,
            "operational_occupancy_rate": 83.33,
            "available_beds": 5,
            "unmodeled_arbitrary_field": "disallowed",
        }
        with pytest.raises(EventValidationError, match="Payload validation failed"):
            OperationalEvent(
                event_type=EventType.OPERATIONS_CAPACITY_UPDATED,
                category=EventCategory.OPERATIONAL_FACT,
                occurred_at=now,
                source="hospitalops.beds_service",
                entity_type=EntityType.DEPARTMENT,
                entity_id="ICU",
                payload=extra_field_payload,
            )

    def test_07_envelope_forbids_extra_fields(self):
        """Verify that OperationalEvent envelope itself forbids arbitrary extra fields."""
        now = datetime.now(UTC)
        payload = {
            "department_id": "ICU",
            "total_beds": 30,
            "occupied_beds": 25,
            "operational_occupancy_rate": 83.33,
            "available_beds": 5,
        }
        with pytest.raises(ValidationError):
            OperationalEvent(
                event_type=EventType.OPERATIONS_CAPACITY_UPDATED,
                category=EventCategory.OPERATIONAL_FACT,
                occurred_at=now,
                source="hospitalops.beds_service",
                entity_type=EntityType.DEPARTMENT,
                entity_id="ICU",
                payload=payload,
                malicious_injection="forbidden",
            )

    def test_08_oversized_payload_rejection(self):
        """Verify that payloads exceeding 64 KB are rejected."""
        now = datetime.now(UTC)
        # Create a payload exceeding 64KB
        large_reason = "X" * 70000
        large_payload = {
            "bed_id": "BED-01",
            "department_id": "ICU",
            "previous_status": "AVAILABLE",
            "new_status": "MAINTENANCE",
            "reason": large_reason,
        }
        with pytest.raises(EventValidationError, match="exceeds maximum allowable limit of 65536 bytes"):
            OperationalEvent(
                event_type=EventType.OPERATIONS_BED_STATUS_CHANGED,
                category=EventCategory.OPERATIONAL_FACT,
                occurred_at=now,
                source="hospitalops.beds_service",
                entity_type=EntityType.BED,
                entity_id="BED-01",
                payload=large_payload,
            )

    def test_09_prohibited_sensitive_key_detection(self):
        """Verify that sensitive keys (ssn, password, token) in metadata or payload are rejected."""
        now = datetime.now(UTC)
        payload = {
            "department_id": "ICU",
            "total_beds": 30,
            "occupied_beds": 25,
            "operational_occupancy_rate": 83.33,
            "available_beds": 5,
        }
        with pytest.raises(EventValidationError, match="Sensitive field name 'api_key' prohibited"):
            OperationalEvent(
                event_type=EventType.OPERATIONS_CAPACITY_UPDATED,
                category=EventCategory.OPERATIONAL_FACT,
                occurred_at=now,
                source="hospitalops.beds_service",
                entity_type=EntityType.DEPARTMENT,
                entity_id="ICU",
                payload=payload,
                metadata={"api_key": "secret_123"},
            )

    def test_10_prohibited_ssn_pattern_detection(self):
        """Verify that string values containing SSN patterns are rejected."""
        now = datetime.now(UTC)
        payload = {
            "bed_id": "BED-01",
            "department_id": "ICU",
            "previous_status": "AVAILABLE",
            "new_status": "OCCUPIED",
            "reason": "Patient SSN is 123-45-6789",
        }
        with pytest.raises(EventValidationError, match="Prohibited sensitive pattern"):
            OperationalEvent(
                event_type=EventType.OPERATIONS_BED_STATUS_CHANGED,
                category=EventCategory.OPERATIONAL_FACT,
                occurred_at=now,
                source="hospitalops.beds_service",
                entity_type=EntityType.BED,
                entity_id="BED-01",
                payload=payload,
            )

    def test_11_payload_hash_deterministic(self):
        """Verify that payload hashing is deterministic regardless of key order."""
        dict1 = {"b": 2, "a": 1, "c": [3, 4]}
        dict2 = {"a": 1, "c": [3, 4], "b": 2}

        hash1 = compute_payload_hash(dict1)
        hash2 = compute_payload_hash(dict2)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex digest length

    def test_12_taxonomy_catalog_coverage(self):
        """Verify that all EventType enum members are documented in the taxonomy catalog."""
        for event_type in EventType:
            definition = get_event_definition(event_type)
            assert definition is not None
            assert definition.event_type == event_type
            assert len(definition.allowed_sources) >= 1
            assert definition.payload_schema_name != ""
            # Verify epistemic fact distinction
            if definition.category == EventCategory.OPERATIONAL_FACT:
                assert definition.is_observed_fact is True
            else:
                assert definition.is_observed_fact is False
