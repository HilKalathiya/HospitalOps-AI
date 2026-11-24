"""
HospitalOps AI — Operational Rule Service (Milestone 6, Chunk 6.2).

High-level application service orchestrating rule authoring, versioning,
facility-isolated querying, evaluation retrieval, and consumer health reporting.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from app.events.contracts import EventType
from app.models.user import Role, UserDocument
from app.rules.consumer import OperationalEventConsumer
from app.rules.contracts import (
    OperationalRule,
    RuleDomain,
    RuleEvaluationRecord,
    RuleEvaluationStatus,
    RuleSeverity,
)
from app.rules.exceptions import (
    RuleNotFoundError,
    RuleValidationError,
)

if TYPE_CHECKING:
    from app.repositories.events import OperationalEventRepository
    from app.repositories.rules import (
        EventProcessingRepository,
        OperationalRuleRepository,
        RuleEvaluationRepository,
    )

logger = logging.getLogger(__name__)


class OperationalRuleService:
    """Domain service for managing operational rules and inspecting evaluation findings."""

    def __init__(
        self,
        rule_repo: OperationalRuleRepository,
        evaluation_repo: RuleEvaluationRepository,
        processing_repo: EventProcessingRepository,
        event_repo: OperationalEventRepository,
    ) -> None:
        self.rule_repo = rule_repo
        self.evaluation_repo = evaluation_repo
        self.processing_repo = processing_repo
        self.event_repo = event_repo
        self.consumer = OperationalEventConsumer(
            event_repo=self.event_repo,
            rule_repo=self.rule_repo,
            evaluation_repo=self.evaluation_repo,
            processing_repo=self.processing_repo,
        )

    def _resolve_facility_scope(self, current_user: UserDocument, requested_facility: str | None) -> str | None:
        """Enforce non-admin facility isolation."""
        if current_user.role == Role.ADMIN:
            return requested_facility
        # Non-admins are strictly pinned to their user facility
        user_facility = getattr(current_user, "facility_id", None) or "facility_default"
        if requested_facility is not None and requested_facility != user_facility:
            raise RuleValidationError(
                f"Unauthorized facility access: cannot query or operate on facility '{requested_facility}'."
            )
        return user_facility

    async def create_rule(
        self,
        rule: OperationalRule,
        current_user: UserDocument,
    ) -> OperationalRule:
        """Create a new operational rule with server-side author and facility validation."""
        effective_facility = self._resolve_facility_scope(current_user, rule.facility_id)
        rule_dict = rule.model_dump(mode="python")
        rule_dict["facility_id"] = effective_facility
        rule_dict["owner"] = current_user.email
        validated_rule = OperationalRule(**rule_dict)

        created = await self.rule_repo.create_rule(validated_rule)
        logger.info(
            "Operational rule created | rule_id=%s version=%d user=%s",
            created.rule_id,
            created.version,
            current_user.email,
        )
        return created

    async def update_rule(
        self,
        rule_id: str,
        updated_rule: OperationalRule,
        current_user: UserDocument,
    ) -> OperationalRule:
        """Create a new version of an existing operational rule."""
        existing = await self.rule_repo.get_rule(rule_id)
        if not existing:
            raise RuleNotFoundError(f"Rule with ID '{rule_id}' not found.")

        # Non-admins cannot modify rules belonging to other facilities
        if current_user.role != Role.ADMIN and existing.facility_id:
            user_facility = getattr(current_user, "facility_id", None) or "facility_default"
            if existing.facility_id != user_facility:
                raise RuleValidationError("Unauthorized facility access: cannot modify rule from another facility.")

        effective_facility = self._resolve_facility_scope(current_user, updated_rule.facility_id)
        rule_dict = updated_rule.model_dump(mode="python")
        rule_dict["rule_id"] = rule_id
        rule_dict["facility_id"] = effective_facility
        rule_dict["owner"] = current_user.email
        validated_rule = OperationalRule(**rule_dict)

        new_version = await self.rule_repo.update_rule(rule_id, validated_rule)
        logger.info(
            "Operational rule updated to version %d | rule_id=%s user=%s",
            new_version.version,
            rule_id,
            current_user.email,
        )
        return new_version

    async def set_rule_active(
        self,
        rule_id: str,
        is_active: bool,
        current_user: UserDocument,
    ) -> OperationalRule:
        """Toggle active state of a rule."""
        existing = await self.rule_repo.get_rule(rule_id)
        if not existing:
            raise RuleNotFoundError(f"Rule with ID '{rule_id}' not found.")

        if current_user.role != Role.ADMIN and existing.facility_id:
            user_facility = getattr(current_user, "facility_id", None) or "facility_default"
            if existing.facility_id != user_facility:
                raise RuleValidationError("Unauthorized facility access.")

        updated = await self.rule_repo.set_rule_active(rule_id, is_active)
        logger.info("Rule '%s' active status set to %s by %s", rule_id, is_active, current_user.email)
        return updated

    async def get_rule(
        self,
        rule_id: str,
        current_user: UserDocument,
        version: int | None = None,
    ) -> OperationalRule:
        """Retrieve rule by ID with facility isolation."""
        rule = await self.rule_repo.get_rule(rule_id, version=version)
        if not rule:
            raise RuleNotFoundError(f"Rule '{rule_id}' (version={version}) not found.")

        if current_user.role != Role.ADMIN and rule.facility_id:
            user_facility = getattr(current_user, "facility_id", None) or "facility_default"
            if rule.facility_id != user_facility:
                raise RuleNotFoundError(f"Rule '{rule_id}' not found.")
        return rule

    async def list_rules(
        self,
        current_user: UserDocument,
        facility_id: str | None = None,
        domain: RuleDomain | None = None,
        is_active: bool | None = None,
        event_type: EventType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[OperationalRule], int]:
        """List rules scoped to user's authorized facility."""
        scoped_facility = self._resolve_facility_scope(current_user, facility_id)
        return await self.rule_repo.list_rules(
            facility_id=scoped_facility,
            domain=domain,
            is_active=is_active,
            event_type=event_type,
            limit=limit,
            offset=offset,
        )

    async def list_rule_versions(
        self,
        rule_id: str,
        current_user: UserDocument,
    ) -> list[OperationalRule]:
        """List all historical versions of a rule."""
        rule = await self.get_rule(rule_id, current_user)  # verifies existence and access
        return await self.rule_repo.list_rule_versions(rule.rule_id)

    async def query_evaluations(
        self,
        current_user: UserDocument,
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
        """Query evaluation findings with facility boundary enforcement."""
        scoped_facility = self._resolve_facility_scope(current_user, facility_id)
        return await self.evaluation_repo.query_evaluations(
            facility_id=scoped_facility,
            rule_id=rule_id,
            domain=domain,
            severity=severity,
            status=status,
            matched_only=matched_only,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )

    async def get_evaluation(
        self,
        evaluation_id: str,
        current_user: UserDocument,
    ) -> RuleEvaluationRecord:
        """Fetch evaluation record by ID with anti-IDOR protection."""
        scoped_facility = self._resolve_facility_scope(current_user, None)
        record = await self.evaluation_repo.get_evaluation(evaluation_id, facility_id=scoped_facility)
        if not record:
            raise RuleNotFoundError(f"Evaluation '{evaluation_id}' not found.")
        return record

    async def process_batch(
        self,
        current_user: UserDocument,
        facility_id: str | None = None,
    ) -> dict[str, int]:
        """Trigger an on-demand batch consumption cycle."""
        scoped_facility = self._resolve_facility_scope(current_user, facility_id)
        return await self.consumer.process_batch(facility_id=scoped_facility)

    async def get_health_status(self) -> dict[str, Any]:
        """Provide observability and queue telemetry for the rule engine."""
        stats = await self.processing_repo.get_stats()
        all_rules, total_rules = await self.rule_repo.list_rules(limit=200)
        active_count = sum(1 for r in all_rules if r.is_active)

        return {
            "status": "HEALTHY",
            "is_durable": self.rule_repo.is_durable,
            "total_rules": total_rules,
            "active_rules": active_count,
            "consumer": {
                "worker_id": self.consumer.worker_id,
                "batch_size": self.consumer.batch_size,
                "lease_seconds": self.consumer.lease_seconds,
            },
            "processing_queue": stats,
        }
