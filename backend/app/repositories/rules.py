"""
HospitalOps AI — Operational Rules & Evaluation Repositories (Milestone 6, Chunk 6.2).

Provides persistence, indexing, version archiving, and atomic idempotency for:
- operational_rules & operational_rule_versions
- rule_evaluations
- event_processing_records (consumer lease & claim recovery)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

import pymongo
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.events.contracts import EventType
from app.models.base import utc_now
from app.repositories.base import BaseRepository
from app.rules.contracts import (
    EventProcessingRecord,
    OperationalRule,
    ProcessingStatus,
    RuleDomain,
    RuleEvaluationRecord,
    RuleEvaluationStatus,
    RuleSeverity,
)
from app.rules.exceptions import (
    RuleConflictError,
    RuleNotFoundError,
    RulePersistenceError,
    RuleValidationError,
)

logger = logging.getLogger(__name__)


# ── Operational Rule Repository ───────────────────────────────────────────────


class OperationalRuleRepository(BaseRepository):
    """
    Data access layer for the operational_rules and operational_rule_versions collections.
    Supports version archiving, rule activation toggling, and facility scoping.
    """

    COLLECTION = "operational_rules"
    RULES_COLLECTION = "operational_rules"
    VERSIONS_COLLECTION = "operational_rule_versions"

    async def ensure_indexes(self) -> None:
        """Indexes are managed centrally by app/database/client.py."""
        pass

    def __init__(
        self,
        db: AsyncIOMotorDatabase | None = None,  # type: ignore[type-arg]
        allow_in_memory: bool = False,
    ) -> None:
        if db is not None:
            super().__init__(db)
            self._allow_in_memory = False
            self._in_memory_rules: dict[str, OperationalRule] = {}
            self._in_memory_versions: dict[str, list[OperationalRule]] = {}
        elif allow_in_memory:
            self._db = None  # type: ignore[assignment]
            self._allow_in_memory = True
            self._in_memory_rules = {}
            self._in_memory_versions = {}
            self._lock = asyncio.Lock()
            logger.info("OperationalRuleRepository initialized in explicit in-memory test mode.")
        else:
            raise RulePersistenceError(
                "OperationalRuleRepository requires an authoritative MongoDB database connection. "
                "Silent in-memory fallback is prohibited in production."
            )

    @property
    def is_durable(self) -> bool:
        return self._db is not None

    async def create_rule(self, rule: OperationalRule) -> OperationalRule:
        """Create a new rule. Raises RuleConflictError if rule_id already exists."""
        if not self.is_durable:
            async with self._lock:
                if rule.rule_id in self._in_memory_rules:
                    raise RuleConflictError(f"Rule with ID '{rule.rule_id}' already exists.")
                self._in_memory_rules[rule.rule_id] = rule
                self._in_memory_versions[rule.rule_id] = [rule]
                return rule

        doc = rule.model_dump(mode="python")
        try:
            await self._db[self.RULES_COLLECTION].insert_one(doc)
            # Archive version 1
            await self._db[self.VERSIONS_COLLECTION].insert_one(doc)
            return rule
        except pymongo.errors.DuplicateKeyError as exc:
            raise RuleConflictError(f"Rule with ID '{rule.rule_id}' already exists.") from exc
        except Exception as exc:
            raise RulePersistenceError(f"Failed to create rule '{rule.rule_id}': {exc}") from exc

    async def get_rule(self, rule_id: str, version: int | None = None) -> OperationalRule | None:
        """Retrieve rule by rule_id. If version is specified, retrieves that specific version."""
        if not self.is_durable:
            async with self._lock:
                if version is not None:
                    versions = self._in_memory_versions.get(rule_id, [])
                    for r in versions:
                        if r.version == version:
                            return r
                    return None
                return self._in_memory_rules.get(rule_id)

        try:
            if version is not None:
                doc = await self._db[self.VERSIONS_COLLECTION].find_one(
                    {"rule_id": rule_id, "version": version}
                )
            else:
                doc = await self._db[self.RULES_COLLECTION].find_one({"rule_id": rule_id})

            if not doc:
                return None
            doc.pop("_id", None)
            return OperationalRule(**doc)
        except Exception as exc:
            raise RulePersistenceError(f"Failed to fetch rule '{rule_id}': {exc}") from exc

    async def update_rule(
        self,
        rule_id: str,
        updated_rule: OperationalRule,
    ) -> OperationalRule:
        """
        Save a new version of an existing rule.
        Increments rule.version and archives the new version.
        """
        existing = await self.get_rule(rule_id)
        if not existing:
            raise RuleNotFoundError(f"Cannot update non-existent rule '{rule_id}'.")

        new_version = existing.version + 1
        updated_dict = updated_rule.model_dump(mode="python")
        updated_dict["version"] = new_version
        updated_dict["updated_at"] = utc_now()
        versioned_rule = OperationalRule(**updated_dict)

        if not self.is_durable:
            async with self._lock:
                self._in_memory_rules[rule_id] = versioned_rule
                self._in_memory_versions[rule_id].append(versioned_rule)
                return versioned_rule

        doc = versioned_rule.model_dump(mode="python")
        try:
            await self._db[self.RULES_COLLECTION].replace_one(
                {"rule_id": rule_id},
                doc,
                upsert=False,
            )
            await self._db[self.VERSIONS_COLLECTION].insert_one(doc)
            return versioned_rule
        except Exception as exc:
            raise RulePersistenceError(f"Failed to update rule '{rule_id}': {exc}") from exc

    async def set_rule_active(self, rule_id: str, is_active: bool) -> OperationalRule:
        """Toggle active/disabled status for an operational rule without bumping version."""
        existing = await self.get_rule(rule_id)
        if not existing:
            raise RuleNotFoundError(f"Cannot update status for non-existent rule '{rule_id}'.")

        updated_dict = existing.model_dump(mode="python")
        updated_dict["is_active"] = is_active
        updated_dict["updated_at"] = utc_now()
        updated_rule = OperationalRule(**updated_dict)

        if not self.is_durable:
            async with self._lock:
                self._in_memory_rules[rule_id] = updated_rule
                return updated_rule

        try:
            await self._db[self.RULES_COLLECTION].update_one(
                {"rule_id": rule_id},
                {"$set": {"is_active": is_active, "updated_at": updated_rule.updated_at}},
            )
            return updated_rule
        except Exception as exc:
            raise RulePersistenceError(f"Failed to update rule status '{rule_id}': {exc}") from exc

    async def list_rules(
        self,
        facility_id: str | None = None,
        domain: RuleDomain | None = None,
        is_active: bool | None = None,
        event_type: EventType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[OperationalRule], int]:
        """Query rules with multi-tenant facility scoping and pagination."""
        if not self.is_durable:
            async with self._lock:
                all_rules = list(self._in_memory_rules.values())
                filtered = []
                for r in all_rules:
                    if facility_id is not None and r.facility_id is not None and r.facility_id != facility_id:
                        continue
                    if domain is not None and r.domain != domain:
                        continue
                    if is_active is not None and r.is_active != is_active:
                        continue
                    if event_type is not None and event_type not in r.supported_event_types:
                        continue
                    filtered.append(r)
                # Sort deterministically
                filtered.sort(
                    key=lambda x: (
                        x.domain.value if hasattr(x.domain, "value") else str(x.domain),
                        x.rule_id,
                    )
                )
                total = len(filtered)
                return filtered[offset : offset + limit], total

        query: dict[str, Any] = {}
        if facility_id is not None:
            # Match rules scoped to facility OR global rules (facility_id is None)
            query["$or"] = [{"facility_id": facility_id}, {"facility_id": None}]
        if domain is not None:
            query["domain"] = domain.value if hasattr(domain, "value") else str(domain)
        if is_active is not None:
            query["is_active"] = is_active
        if event_type is not None:
            query["supported_event_types"] = (
                event_type.value if hasattr(event_type, "value") else str(event_type)
            )

        try:
            total = await self._db[self.RULES_COLLECTION].count_documents(query)
            cursor = (
                self._db[self.RULES_COLLECTION]
                .find(query)
                .sort([("domain", pymongo.ASCENDING), ("rule_id", pymongo.ASCENDING)])
                .skip(offset)
                .limit(limit)
            )
            rules = []
            async for doc in cursor:
                doc.pop("_id", None)
                rules.append(OperationalRule(**doc))
            return rules, total
        except Exception as exc:
            raise RulePersistenceError(f"Failed to query operational rules: {exc}") from exc

    async def list_rule_versions(self, rule_id: str) -> list[OperationalRule]:
        """Retrieve all historical versions for a given rule_id in descending order."""
        if not self.is_durable:
            async with self._lock:
                versions = self._in_memory_versions.get(rule_id, [])
                return sorted(versions, key=lambda r: r.version, reverse=True)

        try:
            cursor = (
                self._db[self.VERSIONS_COLLECTION]
                .find({"rule_id": rule_id})
                .sort("version", pymongo.DESCENDING)
            )
            versions = []
            async for doc in cursor:
                doc.pop("_id", None)
                versions.append(OperationalRule(**doc))
            return versions
        except Exception as exc:
            raise RulePersistenceError(f"Failed to query versions for rule '{rule_id}': {exc}") from exc


# ── Rule Evaluation Repository ────────────────────────────────────────────────


class RuleEvaluationRepository(BaseRepository):
    """
    Append-only repository for rule evaluation records.
    Enforces atomic duplicate rejection via unique index on evaluation_id.
    """

    COLLECTION = "rule_evaluations"

    async def ensure_indexes(self) -> None:
        """Indexes are managed centrally by app/database/client.py."""
        pass

    def __init__(
        self,
        db: AsyncIOMotorDatabase | None = None,  # type: ignore[type-arg]
        allow_in_memory: bool = False,
    ) -> None:
        if db is not None:
            super().__init__(db)
            self._allow_in_memory = False
            self._in_memory_evaluations: dict[str, RuleEvaluationRecord] = {}
        elif allow_in_memory:
            self._db = None  # type: ignore[assignment]
            self._allow_in_memory = True
            self._in_memory_evaluations = {}
            self._lock = asyncio.Lock()
            logger.info("RuleEvaluationRepository initialized in explicit in-memory test mode.")
        else:
            raise RulePersistenceError(
                "RuleEvaluationRepository requires an authoritative MongoDB database connection."
            )

    @property
    def is_durable(self) -> bool:
        return self._db is not None

    async def save_evaluation(
        self, evaluation: RuleEvaluationRecord
    ) -> tuple[RuleEvaluationRecord, bool]:
        """
        Persist a rule evaluation record.
        Returns:
            tuple[RuleEvaluationRecord, bool]: (persisted_record, is_duplicate)
        """
        if not self.is_durable:
            async with self._lock:
                if evaluation.evaluation_id in self._in_memory_evaluations:
                    return self._in_memory_evaluations[evaluation.evaluation_id], True
                self._in_memory_evaluations[evaluation.evaluation_id] = evaluation
                return evaluation, False

        doc = evaluation.model_dump(mode="python")
        try:
            await self._db[self.COLLECTION].insert_one(doc)
            return evaluation, False
        except pymongo.errors.DuplicateKeyError:
            # Re-fetch existing evaluation record
            existing_doc = await self._db[self.COLLECTION].find_one(
                {"evaluation_id": evaluation.evaluation_id}
            )
            if existing_doc:
                existing_doc.pop("_id", None)
                return RuleEvaluationRecord(**existing_doc), True
            return evaluation, True
        except Exception as exc:
            raise RulePersistenceError(
                f"Failed to save rule evaluation '{evaluation.evaluation_id}': {exc}"
            ) from exc

    async def get_evaluation(
        self, evaluation_id: str, facility_id: str | None = None
    ) -> RuleEvaluationRecord | None:
        """Fetch evaluation by ID with facility boundary check (anti-IDOR)."""
        if not self.is_durable:
            async with self._lock:
                ev = self._in_memory_evaluations.get(evaluation_id)
                if not ev:
                    return None
                if facility_id is not None and ev.facility_id != facility_id:
                    return None
                return ev

        query: dict[str, Any] = {"evaluation_id": evaluation_id}
        if facility_id is not None:
            query["facility_id"] = facility_id

        try:
            doc = await self._db[self.COLLECTION].find_one(query)
            if not doc:
                return None
            doc.pop("_id", None)
            return RuleEvaluationRecord(**doc)
        except Exception as exc:
            raise RulePersistenceError(f"Failed to fetch evaluation '{evaluation_id}': {exc}") from exc

    async def query_evaluations(
        self,
        facility_id: str | None = None,
        rule_id: str | None = None,
        domain: RuleDomain | None = None,
        severity: RuleSeverity | None = None,
        status: RuleEvaluationStatus | None = None,
        matched_only: bool = False,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[RuleEvaluationRecord], int]:
        """Query evaluation findings with time range and multi-tenant facility boundaries."""
        if start_time and end_time and start_time > end_time:
            raise RuleValidationError("Query start_time cannot be after end_time.")

        if not self.is_durable:
            async with self._lock:
                items = list(self._in_memory_evaluations.values())
                filtered = []
                for ev in items:
                    if facility_id is not None and ev.facility_id != facility_id:
                        continue
                    if rule_id is not None and ev.rule_id != rule_id:
                        continue
                    if domain is not None and ev.domain != domain:
                        continue
                    if severity is not None and ev.severity != severity:
                        continue
                    if status is not None and ev.status != status:
                        continue
                    if matched_only and not ev.matched:
                        continue
                    if start_time is not None and ev.evaluated_at < start_time:
                        continue
                    if end_time is not None and ev.evaluated_at > end_time:
                        continue
                    filtered.append(ev)

                filtered.sort(key=lambda x: (x.evaluated_at, x.evaluation_id), reverse=True)
                total = len(filtered)
                return filtered[offset : offset + limit], total

        query: dict[str, Any] = {}
        if facility_id is not None:
            query["facility_id"] = facility_id
        if rule_id is not None:
            query["rule_id"] = rule_id
        if domain is not None:
            query["domain"] = domain.value if hasattr(domain, "value") else str(domain)
        if severity is not None:
            query["severity"] = severity.value if hasattr(severity, "value") else str(severity)
        if status is not None:
            query["status"] = status.value if hasattr(status, "value") else str(status)
        if matched_only:
            query["matched"] = True

        time_filter: dict[str, Any] = {}
        if start_time is not None:
            time_filter["$gte"] = start_time
        if end_time is not None:
            time_filter["$lte"] = end_time
        if time_filter:
            query["evaluated_at"] = time_filter

        try:
            total = await self._db[self.COLLECTION].count_documents(query)
            cursor = (
                self._db[self.COLLECTION]
                .find(query)
                .sort([("evaluated_at", pymongo.DESCENDING), ("evaluation_id", pymongo.DESCENDING)])
                .skip(offset)
                .limit(limit)
            )
            records = []
            async for doc in cursor:
                doc.pop("_id", None)
                records.append(RuleEvaluationRecord(**doc))
            return records, total
        except Exception as exc:
            raise RulePersistenceError(f"Failed to query rule evaluations: {exc}") from exc


# ── Event Consumer Processing State Repository ───────────────────────────────


class EventProcessingRepository(BaseRepository):
    """
    Manages durable event consumption checkpoints, worker leases, retries, and quarantines.
    Collection: event_processing_records
    """

    COLLECTION = "event_processing_records"

    async def ensure_indexes(self) -> None:
        """Indexes are managed centrally by app/database/client.py."""
        pass

    def __init__(
        self,
        db: AsyncIOMotorDatabase | None = None,  # type: ignore[type-arg]
        allow_in_memory: bool = False,
    ) -> None:
        if db is not None:
            super().__init__(db)
            self._allow_in_memory = False
            self._in_memory_records: dict[str, EventProcessingRecord] = {}
        elif allow_in_memory:
            self._db = None  # type: ignore[assignment]
            self._allow_in_memory = True
            self._in_memory_records = {}
            self._lock = asyncio.Lock()
            logger.info("EventProcessingRepository initialized in explicit in-memory test mode.")
        else:
            raise RulePersistenceError(
                "EventProcessingRepository requires an authoritative MongoDB database connection."
            )

    @property
    def is_durable(self) -> bool:
        return self._db is not None

    async def register_event(
        self,
        event_id: str,
        facility_id: str,
        event_type: str,
        category: str,
    ) -> EventProcessingRecord:
        """Register an event for processing if not already present."""
        now = utc_now()
        record = EventProcessingRecord(
            event_id=event_id,
            facility_id=facility_id,
            event_type=event_type,
            category=category,
            status=ProcessingStatus.PENDING,
            created_at=now,
            updated_at=now,
        )

        if not self.is_durable:
            async with self._lock:
                if event_id not in self._in_memory_records:
                    self._in_memory_records[event_id] = record
                return self._in_memory_records[event_id]

        doc = record.model_dump(mode="python")
        try:
            await self._db[self.COLLECTION].update_one(
                {"event_id": event_id},
                {"$setOnInsert": doc},
                upsert=True,
            )
            stored = await self._db[self.COLLECTION].find_one({"event_id": event_id})
            stored.pop("_id", None)
            return EventProcessingRecord(**stored)
        except Exception as exc:
            raise RulePersistenceError(f"Failed to register event processing record: {exc}") from exc

    async def claim_batch(
        self,
        worker_id: str,
        batch_size: int = 50,
        lease_seconds: int = 60,
        facility_id: str | None = None,
    ) -> list[EventProcessingRecord]:
        """
        Atomically claim a batch of eligible events for processing.
        Eligible events are:
        - status == PENDING
        - status == RETRY_PENDING
        - status == PROCESSING and lease_expires_at < now (worker crash recovery!)
        """
        now = utc_now()
        lease_expires = now + timedelta(seconds=lease_seconds)

        if not self.is_durable:
            async with self._lock:
                claimed = []
                for rec in self._in_memory_records.values():
                    if facility_id is not None and rec.facility_id != facility_id:
                        continue

                    # Check eligibility
                    is_eligible = (
                        rec.status in (ProcessingStatus.PENDING, ProcessingStatus.RETRY_PENDING)
                        or (
                            rec.status == ProcessingStatus.PROCESSING
                            and rec.lease_expires_at is not None
                            and rec.lease_expires_at < now
                        )
                    )
                    if is_eligible and rec.attempts < rec.max_attempts:
                        rec.status = ProcessingStatus.PROCESSING
                        rec.worker_id = worker_id
                        rec.lease_expires_at = lease_expires
                        rec.attempts += 1
                        if rec.first_attempted_at is None:
                            rec.first_attempted_at = now
                        rec.last_attempted_at = now
                        rec.updated_at = now
                        claimed.append(rec)
                        if len(claimed) >= batch_size:
                            break
                return claimed

        # MongoDB atomic claim loop
        query: dict[str, Any] = {
            "$and": [
                {
                    "$or": [
                        {"status": ProcessingStatus.PENDING.value},
                        {"status": ProcessingStatus.RETRY_PENDING.value},
                        {
                            "status": ProcessingStatus.PROCESSING.value,
                            "lease_expires_at": {"$lt": now},
                        },
                    ]
                },
                {"$expr": {"$lt": ["$attempts", "$max_attempts"]}},
            ]
        }
        if facility_id is not None:
            query["facility_id"] = facility_id

        claimed = []
        try:
            # We fetch IDs of eligible records sorted by created_at
            cursor = (
                self._db[self.COLLECTION]
                .find(query, {"event_id": 1})
                .sort([("created_at", pymongo.ASCENDING)])
                .limit(batch_size)
            )
            candidate_ids = [doc["event_id"] async for doc in cursor]

            for ev_id in candidate_ids:
                # Atomically claim each candidate
                doc = await self._db[self.COLLECTION].find_one_and_update(
                    {
                        "event_id": ev_id,
                        "$or": [
                            {"status": ProcessingStatus.PENDING.value},
                            {"status": ProcessingStatus.RETRY_PENDING.value},
                            {
                                "status": ProcessingStatus.PROCESSING.value,
                                "lease_expires_at": {"$lt": now},
                            },
                        ],
                    },
                    {
                        "$set": {
                            "status": ProcessingStatus.PROCESSING.value,
                            "worker_id": worker_id,
                            "lease_expires_at": lease_expires,
                            "last_attempted_at": now,
                            "updated_at": now,
                        },
                        "$inc": {"attempts": 1},
                        "$setOnInsert": {"first_attempted_at": now},
                    },
                    return_document=pymongo.ReturnDocument.AFTER,
                )
                if doc:
                    doc.pop("_id", None)
                    claimed.append(EventProcessingRecord(**doc))
            return claimed
        except Exception as exc:
            raise RulePersistenceError(f"Failed to claim event batch: {exc}") from exc

    async def mark_completed(
        self,
        event_id: str,
        rules_evaluated: int,
        rules_matched: int,
    ) -> None:
        """Mark event processing as successfully completed."""
        now = utc_now()
        if not self.is_durable:
            async with self._lock:
                rec = self._in_memory_records.get(event_id)
                if rec:
                    rec.status = ProcessingStatus.COMPLETED
                    rec.lease_expires_at = None
                    rec.completed_at = now
                    rec.rules_evaluated_count = rules_evaluated
                    rec.rules_matched_count = rules_matched
                    rec.updated_at = now
            return

        try:
            await self._db[self.COLLECTION].update_one(
                {"event_id": event_id},
                {
                    "$set": {
                        "status": ProcessingStatus.COMPLETED.value,
                        "lease_expires_at": None,
                        "completed_at": now,
                        "rules_evaluated_count": rules_evaluated,
                        "rules_matched_count": rules_matched,
                        "updated_at": now,
                    }
                },
            )
        except Exception as exc:
            raise RulePersistenceError(f"Failed to mark event '{event_id}' completed: {exc}") from exc

    async def mark_failed(
        self,
        event_id: str,
        error_message: str,
    ) -> ProcessingStatus:
        """
        Record failure for an event.
        If attempts >= max_attempts, transitions to QUARANTINED.
        Otherwise transitions to RETRY_PENDING.
        """
        now = utc_now()
        if not self.is_durable:
            async with self._lock:
                rec = self._in_memory_records.get(event_id)
                if rec:
                    new_status = (
                        ProcessingStatus.QUARANTINED
                        if rec.attempts >= rec.max_attempts
                        else ProcessingStatus.RETRY_PENDING
                    )
                    rec.status = new_status
                    rec.lease_expires_at = None
                    rec.error_message = error_message
                    rec.updated_at = now
                    return new_status
                return ProcessingStatus.QUARANTINED

        try:
            doc = await self._db[self.COLLECTION].find_one({"event_id": event_id})
            if not doc:
                return ProcessingStatus.QUARANTINED

            attempts = doc.get("attempts", 1)
            max_attempts = doc.get("max_attempts", 3)
            new_status = (
                ProcessingStatus.QUARANTINED.value
                if attempts >= max_attempts
                else ProcessingStatus.RETRY_PENDING.value
            )

            await self._db[self.COLLECTION].update_one(
                {"event_id": event_id},
                {
                    "$set": {
                        "status": new_status,
                        "lease_expires_at": None,
                        "error_message": error_message,
                        "updated_at": now,
                    }
                },
            )
            return ProcessingStatus(new_status)
        except Exception as exc:
            raise RulePersistenceError(f"Failed to mark event '{event_id}' failed: {exc}") from exc

    async def get_stats(self, facility_id: str | None = None) -> dict[str, Any]:
        """Aggregate counts by processing status for health monitoring."""
        if not self.is_durable:
            async with self._lock:
                counts = {st.value: 0 for st in ProcessingStatus}
                for rec in self._in_memory_records.values():
                    if facility_id is None or rec.facility_id == facility_id:
                        st_key = rec.status.value if hasattr(rec.status, "value") else str(rec.status)
                        counts[st_key] = counts.get(st_key, 0) + 1
                return {"counts": counts, "total": sum(counts.values()), "is_durable": False}

        query: dict[str, Any] = {}
        if facility_id is not None:
            query["facility_id"] = facility_id

        try:
            pipeline = [
                {"$match": query} if query else {"$match": {}},
                {"$group": {"_id": "$status", "count": {"$sum": 1}}},
            ]
            counts = {st.value: 0 for st in ProcessingStatus}
            async for doc in self._db[self.COLLECTION].aggregate(pipeline):
                status_val = doc["_id"]
                if status_val in counts:
                    counts[status_val] = doc["count"]
            return {"counts": counts, "total": sum(counts.values()), "is_durable": True}
        except Exception as exc:
            raise RulePersistenceError(f"Failed to get event processing stats: {exc}") from exc


# ── Explicit In-Memory Test Repositories ──────────────────────────────────────


class InMemoryOperationalRuleRepository(OperationalRuleRepository):
    """Explicit in-memory operational rule repository for isolated testing."""

    def __init__(self) -> None:
        super().__init__(db=None, allow_in_memory=True)


class InMemoryRuleEvaluationRepository(RuleEvaluationRepository):
    """Explicit in-memory rule evaluation repository for isolated testing."""

    def __init__(self) -> None:
        super().__init__(db=None, allow_in_memory=True)


class InMemoryEventProcessingRepository(EventProcessingRepository):
    """Explicit in-memory event processing repository for isolated testing."""

    def __init__(self) -> None:
        super().__init__(db=None, allow_in_memory=True)
