"""
HospitalOps AI — Operational Event Consumer & Evaluation Engine (Milestone 6, Chunk 6.2).

Orchestrates:
- Claiming batches of persisted operational events with worker leases
- Recovering expired leases from crashed workers
- Matching eligible declarative operational rules
- Single-event and time-window evaluation
- Atomic, idempotent persistence of rule evaluation findings
- Retry handling, backoff, and quarantine of permanently failing records
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import timedelta
from typing import TYPE_CHECKING

from app.events.contracts import OperationalEvent
from app.repositories.events import EventQueryFilter
from app.rules.contracts import (
    OperationalRule,
    RuleEvaluationRecord,
)
from app.rules.evaluator import evaluate_rule_against_event, evaluate_rule_against_window

if TYPE_CHECKING:
    from app.repositories.events import OperationalEventRepository
    from app.repositories.rules import (
        EventProcessingRepository,
        OperationalRuleRepository,
        RuleEvaluationRepository,
    )

logger = logging.getLogger(__name__)


class OperationalEventConsumer:
    """
    Durable event consumer that polls persisted operational events, claims worker leases,
    evaluates active rules, and records findings with evidence traceability.
    """

    def __init__(
        self,
        event_repo: OperationalEventRepository,
        rule_repo: OperationalRuleRepository,
        evaluation_repo: RuleEvaluationRepository,
        processing_repo: EventProcessingRepository,
        worker_id: str | None = None,
        batch_size: int = 50,
        lease_seconds: int = 60,
    ) -> None:
        self.event_repo = event_repo
        self.rule_repo = rule_repo
        self.evaluation_repo = evaluation_repo
        self.processing_repo = processing_repo
        self.worker_id = worker_id or f"worker_{uuid.uuid4().hex[:8]}"
        self.batch_size = batch_size
        self.lease_seconds = lease_seconds
        self._shutdown_event = asyncio.Event()

    async def register_incoming_events(self, events: list[OperationalEvent]) -> int:
        """Register newly ingested operational events for background consumption."""
        registered_count = 0
        for ev in events:
            await self.processing_repo.register_event(
                event_id=ev.event_id,
                facility_id=ev.facility_id,
                event_type=ev.event_type.value if hasattr(ev.event_type, "value") else str(ev.event_type),
                category=ev.category.value if hasattr(ev.category, "value") else str(ev.category),
            )
            registered_count += 1
        return registered_count

    async def process_single_event(
        self,
        event: OperationalEvent,
        active_rules: list[OperationalRule] | None = None,
    ) -> list[RuleEvaluationRecord]:
        """
        Evaluate all eligible active rules against a single operational event.
        Persists evaluations atomically with duplicate prevention.
        """
        if active_rules is None:
            rules, _ = await self.rule_repo.list_rules(
                facility_id=event.facility_id,
                is_active=True,
                limit=100,
            )
        else:
            rules = active_rules

        evaluations: list[RuleEvaluationRecord] = []
        for rule in rules:
            # Check event-type compatibility
            if event.event_type not in rule.supported_event_types:
                continue

            # Time-window evaluation
            if rule.time_window is not None:
                window_duration = timedelta(seconds=rule.time_window.window_seconds)
                window_start = event.occurred_at - window_duration
                # Query windowed historical events
                window_filter = EventQueryFilter(
                    facility_id=event.facility_id,
                    event_types=[event.event_type],
                    start_time=window_start,
                    end_time=event.occurred_at,
                    limit=100,
                )
                window_events, _ = await self.event_repo.query_events(window_filter)
                eval_record = evaluate_rule_against_window(
                    rule=rule,
                    events=window_events,
                    worker_id=self.worker_id,
                )
            else:
                eval_record = evaluate_rule_against_event(
                    rule=rule,
                    event=event,
                    worker_id=self.worker_id,
                )

            # Persist evaluation record idempotently
            persisted_eval, is_dup = await self.evaluation_repo.save_evaluation(eval_record)
            evaluations.append(persisted_eval)
            if eval_record.matched:
                logger.info(
                    "Rule MATCHED | rule_id=%s version=%d event_id=%s severity=%s is_dup=%s",
                    rule.rule_id,
                    rule.version,
                    event.event_id,
                    rule.severity.value if hasattr(rule.severity, "value") else str(rule.severity),
                    is_dup,
                )

        return evaluations

    async def process_batch(
        self,
        facility_id: str | None = None,
    ) -> dict[str, int]:
        """
        Execute one complete batch cycle:
        1. Claim a batch of eligible event processing records with worker lease.
        2. Retrieve corresponding operational events from event store.
        3. Evaluate active operational rules.
        4. Complete or fail each record.
        """
        claimed = await self.processing_repo.claim_batch(
            worker_id=self.worker_id,
            batch_size=self.batch_size,
            lease_seconds=self.lease_seconds,
            facility_id=facility_id,
        )
        if not claimed:
            return {"claimed": 0, "completed": 0, "failed": 0, "matched": 0}

        # Cache active rules for this batch run
        active_rules, _ = await self.rule_repo.list_rules(
            facility_id=facility_id,
            is_active=True,
            limit=200,
        )

        completed_count = 0
        failed_count = 0
        matched_count = 0

        for rec in claimed:
            try:
                # Retrieve the full authoritative OperationalEvent
                event = await self.event_repo.get_by_id(rec.event_id)
                if not event:
                    logger.warning(
                        "Claimed event not found in event store | event_id=%s", rec.event_id
                    )
                    await self.processing_repo.mark_failed(
                        rec.event_id, "Event not found in operational_events store"
                    )
                    failed_count += 1
                    continue

                evals = await self.process_single_event(event, active_rules=active_rules)
                matched_in_event = sum(1 for e in evals if e.matched)
                matched_count += matched_in_event

                await self.processing_repo.mark_completed(
                    event_id=rec.event_id,
                    rules_evaluated=len(evals),
                    rules_matched=matched_in_event,
                )
                completed_count += 1
            except Exception as exc:
                logger.error(
                    "Error processing event | event_id=%s worker=%s error=%s",
                    rec.event_id,
                    self.worker_id,
                    exc,
                )
                await self.processing_repo.mark_failed(rec.event_id, str(exc))
                failed_count += 1

        return {
            "claimed": len(claimed),
            "completed": completed_count,
            "failed": failed_count,
            "matched": matched_count,
        }

    async def run_loop(self, poll_interval_seconds: float = 2.0) -> None:
        """Run consumer polling loop until shutdown is signaled."""
        logger.info("OperationalEventConsumer started | worker_id=%s", self.worker_id)
        while not self._shutdown_event.is_set():
            try:
                result = await self.process_batch()
                if result["claimed"] == 0:
                    # Sleep when no work is available
                    try:
                        await asyncio.wait_for(
                            self._shutdown_event.wait(), timeout=poll_interval_seconds
                        )
                    except TimeoutError:
                        pass
            except Exception as exc:
                logger.error("Consumer loop encountered error: %s", exc)
                await asyncio.sleep(poll_interval_seconds)

        logger.info("OperationalEventConsumer gracefully stopped | worker_id=%s", self.worker_id)

    def stop(self) -> None:
        """Signal consumer to stop gracefully."""
        self._shutdown_event.set()
