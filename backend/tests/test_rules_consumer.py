"""
HospitalOps AI — Operational Event Consumer & Lease Recovery Tests (Milestone 6, Chunk 6.2).

Tests:
- Bounded batch event consumption and evaluation
- Worker lease expiration and crash recovery
- Retry scheduling and failure transition to RETRY_PENDING
- Retry exhaustion transitioning to QUARANTINED
- Idempotent evaluation persistence on re-delivery
- Rule versioning and historical evaluation preservation
- Graceful consumer shutdown
"""

from datetime import timedelta

import pytest

from app.events.contracts import (
    CapacityUpdatedPayload,
    EntityType,
    EventCategory,
    EventType,
    OperationalEvent,
)
from app.models.base import utc_now
from app.repositories.events import InMemoryOperationalEventRepository
from app.repositories.rules import (
    InMemoryEventProcessingRepository,
    InMemoryOperationalRuleRepository,
    InMemoryRuleEvaluationRepository,
)
from app.rules.consumer import OperationalEventConsumer
from app.rules.contracts import (
    OperationalRule,
    ProcessingStatus,
    RuleDomain,
    RuleOperator,
    RuleSeverity,
    SingleCondition,
)


def _make_capacity_event(
    event_id: str = "evt_cons_01",
    facility_id: str = "facility_main",
    occupancy_rate: float = 0.92,
) -> OperationalEvent:
    payload = CapacityUpdatedPayload(
        department_id="ICU",
        total_beds=50,
        occupied_beds=46,
        available_beds=4,
        operational_occupancy_rate=occupancy_rate,
    )
    return OperationalEvent(
        event_id=event_id,
        event_type=EventType.OPERATIONS_CAPACITY_UPDATED,
        category=EventCategory.OBSERVED_OPERATIONAL,
        facility_id=facility_id,
        source="hospitalops.capacity_service",
        entity_type=EntityType.DEPARTMENT,
        entity_id="ICU",
        correlation_id="corr_cons_01",
        payload=payload.model_dump(),
    )


def _make_high_occupancy_rule(
    rule_id: str = "rule_occ_90",
    threshold: float = 0.90,
    facility_id: str | None = None,
) -> OperationalRule:
    return OperationalRule(
        rule_id=rule_id,
        name="High Occupancy Warning",
        description="Warns when operational occupancy rate exceeds threshold",
        domain=RuleDomain.CAPACITY,
        supported_event_types=[EventType.OPERATIONS_CAPACITY_UPDATED],
        allowed_categories=[EventCategory.OBSERVED_OPERATIONAL],
        facility_id=facility_id,
        severity=RuleSeverity.HIGH,
        condition=SingleCondition(
            field="payload.operational_occupancy_rate",
            operator=RuleOperator.GREATER_THAN,
            value=threshold,
        ),
    )


class TestRulesConsumer:
    @pytest.mark.asyncio
    async def test_01_successful_event_consumption_and_evaluation(self):
        event_repo = InMemoryOperationalEventRepository()
        rule_repo = InMemoryOperationalRuleRepository()
        eval_repo = InMemoryRuleEvaluationRepository()
        proc_repo = InMemoryEventProcessingRepository()

        # 1. Setup rule
        rule = _make_high_occupancy_rule()
        await rule_repo.create_rule(rule)

        # 2. Ingest event
        ev = _make_capacity_event(occupancy_rate=0.95)
        await event_repo.save_event(ev)

        # 3. Consumer setup & register event
        consumer = OperationalEventConsumer(
            event_repo=event_repo,
            rule_repo=rule_repo,
            evaluation_repo=eval_repo,
            processing_repo=proc_repo,
            worker_id="worker_test_01",
        )
        await consumer.register_incoming_events([ev])

        # 4. Process batch
        stats = await consumer.process_batch()
        assert stats["claimed"] == 1
        assert stats["completed"] == 1
        assert stats["matched"] == 1
        assert stats["failed"] == 0

        # Verify evaluation record
        evals, total = await eval_repo.query_evaluations()
        assert total == 1
        assert evals[0].rule_id == "rule_occ_90"
        assert evals[0].matched is True
        assert evals[0].source_event_ids == [ev.event_id]

        # Verify processing record status
        proc_stats = await proc_repo.get_stats()
        assert proc_stats["counts"][ProcessingStatus.COMPLETED.value] == 1

    @pytest.mark.asyncio
    async def test_02_empty_queue_processing(self):
        consumer = OperationalEventConsumer(
            event_repo=InMemoryOperationalEventRepository(),
            rule_repo=InMemoryOperationalRuleRepository(),
            evaluation_repo=InMemoryRuleEvaluationRepository(),
            processing_repo=InMemoryEventProcessingRepository(),
        )
        stats = await consumer.process_batch()
        assert stats["claimed"] == 0
        assert stats["completed"] == 0

    @pytest.mark.asyncio
    async def test_03_batch_size_limits(self):
        event_repo = InMemoryOperationalEventRepository()
        proc_repo = InMemoryEventProcessingRepository()
        rule_repo = InMemoryOperationalRuleRepository()
        eval_repo = InMemoryRuleEvaluationRepository()

        # Ingest 5 events
        events = [_make_capacity_event(f"evt_batch_{i}") for i in range(5)]
        for ev in events:
            await event_repo.save_event(ev)

        consumer = OperationalEventConsumer(
            event_repo=event_repo,
            rule_repo=rule_repo,
            evaluation_repo=eval_repo,
            processing_repo=proc_repo,
            batch_size=2,  # Bounded to 2
        )
        await consumer.register_incoming_events(events)

        stats = await consumer.process_batch()
        assert stats["claimed"] == 2
        assert stats["completed"] == 2

    @pytest.mark.asyncio
    async def test_04_worker_crash_recovery_expired_lease(self):
        event_repo = InMemoryOperationalEventRepository()
        proc_repo = InMemoryEventProcessingRepository()
        rule_repo = InMemoryOperationalRuleRepository()
        eval_repo = InMemoryRuleEvaluationRepository()

        rule = _make_high_occupancy_rule()
        await rule_repo.create_rule(rule)

        ev = _make_capacity_event("evt_crash_01")
        await event_repo.save_event(ev)

        # Worker 1 claims event
        consumer_1 = OperationalEventConsumer(
            event_repo=event_repo,
            rule_repo=rule_repo,
            evaluation_repo=eval_repo,
            processing_repo=proc_repo,
            worker_id="worker_crashed",
            lease_seconds=1,  # Short lease
        )
        await consumer_1.register_incoming_events([ev])
        claimed = await proc_repo.claim_batch(worker_id="worker_crashed", lease_seconds=1)
        assert len(claimed) == 1
        assert claimed[0].status == ProcessingStatus.PROCESSING
        assert claimed[0].worker_id == "worker_crashed"

        # Worker 1 "crashes" (never completes the work).
        # We manually expire the lease
        async with proc_repo._lock:
            proc_repo._in_memory_records["evt_crash_01"].lease_expires_at = utc_now() - timedelta(seconds=5)

        # Worker 2 wakes up and should reclaim the orphaned event!
        consumer_2 = OperationalEventConsumer(
            event_repo=event_repo,
            rule_repo=rule_repo,
            evaluation_repo=eval_repo,
            processing_repo=proc_repo,
            worker_id="worker_survivor",
        )
        stats = await consumer_2.process_batch()
        assert stats["claimed"] == 1
        assert stats["completed"] == 1

        # Check that worker_survivor completed it
        async with proc_repo._lock:
            rec = proc_repo._in_memory_records["evt_crash_01"]
            assert rec.status == ProcessingStatus.COMPLETED
            assert rec.attempts == 2

    @pytest.mark.asyncio
    async def test_05_retry_exhaustion_transitions_to_quarantined(self):
        proc_repo = InMemoryEventProcessingRepository()
        await proc_repo.register_event("evt_poison_01", "facility_main", "type_x", "cat_y")

        # Claim 1 -> fail
        await proc_repo.claim_batch(worker_id="w1")
        st1 = await proc_repo.mark_failed("evt_poison_01", "Error 1")
        assert st1 == ProcessingStatus.RETRY_PENDING

        # Claim 2 -> fail
        await proc_repo.claim_batch(worker_id="w2")
        st2 = await proc_repo.mark_failed("evt_poison_01", "Error 2")
        assert st2 == ProcessingStatus.RETRY_PENDING

        # Claim 3 -> fail (max_attempts = 3) -> QUARANTINED!
        await proc_repo.claim_batch(worker_id="w3")
        st3 = await proc_repo.mark_failed("evt_poison_01", "Fatal Error 3")
        assert st3 == ProcessingStatus.QUARANTINED

        # Verify it cannot be claimed anymore
        claimed = await proc_repo.claim_batch(worker_id="w4")
        assert len(claimed) == 0

    @pytest.mark.asyncio
    async def test_06_idempotent_duplicate_processing(self):
        event_repo = InMemoryOperationalEventRepository()
        rule_repo = InMemoryOperationalRuleRepository()
        eval_repo = InMemoryRuleEvaluationRepository()
        proc_repo = InMemoryEventProcessingRepository()

        rule = _make_high_occupancy_rule()
        await rule_repo.create_rule(rule)

        ev = _make_capacity_event("evt_idemp_proc_01", occupancy_rate=0.95)
        await event_repo.save_event(ev)

        consumer = OperationalEventConsumer(
            event_repo=event_repo,
            rule_repo=rule_repo,
            evaluation_repo=eval_repo,
            processing_repo=proc_repo,
        )

        # Process twice
        evals_1 = await consumer.process_single_event(ev)
        evals_2 = await consumer.process_single_event(ev)

        assert len(evals_1) == 1
        assert len(evals_2) == 1
        assert evals_1[0].evaluation_id == evals_2[0].evaluation_id

        # Total evaluation records in DB must still be exactly 1!
        _, total = await eval_repo.query_evaluations()
        assert total == 1

    @pytest.mark.asyncio
    async def test_07_rule_versioning_produces_distinct_evaluations(self):
        event_repo = InMemoryOperationalEventRepository()
        rule_repo = InMemoryOperationalRuleRepository()
        eval_repo = InMemoryRuleEvaluationRepository()
        proc_repo = InMemoryEventProcessingRepository()

        # Rule Version 1: threshold 0.90
        rule_v1 = _make_high_occupancy_rule(rule_id="rule_ver_test", threshold=0.90)
        await rule_repo.create_rule(rule_v1)

        ev = _make_capacity_event("evt_ver_01", occupancy_rate=0.92)
        await event_repo.save_event(ev)

        consumer = OperationalEventConsumer(
            event_repo=event_repo,
            rule_repo=rule_repo,
            evaluation_repo=eval_repo,
            processing_repo=proc_repo,
        )

        # Evaluate against Version 1
        evals_v1 = await consumer.process_single_event(ev)
        assert evals_v1[0].rule_version == 1
        assert evals_v1[0].matched is True

        # Update Rule to Version 2: stricter threshold 0.95
        rule_v2 = _make_high_occupancy_rule(rule_id="rule_ver_test", threshold=0.95)
        updated = await rule_repo.update_rule("rule_ver_test", rule_v2)
        assert updated.version == 2

        # Re-evaluate against Version 2 (occupancy 0.92 is NOT > 0.95 -> NOT_MATCHED)
        evals_v2 = await consumer.process_single_event(ev)
        assert evals_v2[0].rule_version == 2
        assert evals_v2[0].matched is False

        # Both distinct versioned evaluation records exist!
        evals_all, total = await eval_repo.query_evaluations()
        assert total == 2
        versions_recorded = {e.rule_version for e in evals_all}
        assert versions_recorded == {1, 2}

    @pytest.mark.asyncio
    async def test_08_graceful_shutdown(self):
        consumer = OperationalEventConsumer(
            event_repo=InMemoryOperationalEventRepository(),
            rule_repo=InMemoryOperationalRuleRepository(),
            evaluation_repo=InMemoryRuleEvaluationRepository(),
            processing_repo=InMemoryEventProcessingRepository(),
        )
        assert not consumer._shutdown_event.is_set()
        consumer.stop()
        assert consumer._shutdown_event.is_set()
