"""
HospitalOps AI — Operational Rules & Evaluation REST Endpoints (Milestone 6, Chunk 6.2).

Exposes secured, audited REST endpoints for:
- Managing declarative operational rules (CRUD, versioning, activation toggle)
- Querying and retrieving immutable rule evaluation findings (evidence provenance, anti-IDOR)
- Event consumer queue telemetry and on-demand batch evaluation dispatch

Safety & Security Rules:
- Server-side JWT authentication & RBAC permissions required (rules.read, rules.manage).
- Non-admin users are strictly pinned to their assigned facility_id (anti-IDOR / zero cross-tenant leakage).
- All operational rule evaluations output operational findings only (requires_human_review = True).
- Zero mutation of hospital operational records (patients, admissions, beds, resources).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.dependencies import get_rule_service, require_permission
from app.events.contracts import EventType
from app.models.user import UserDocument
from app.rules.contracts import (
    OperationalRule,
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
from app.rules.service import OperationalRuleService
from app.schemas.common import ResponseMeta, SuccessResponse

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Request / Response DTOs ───────────────────────────────────────────────────


class RuleListResponse(BaseModel):
    """Paginated collection of operational rules."""

    items: list[OperationalRule]
    total: int
    limit: int
    offset: int


class EvaluationListResponse(BaseModel):
    """Paginated collection of rule evaluation records."""

    items: list[RuleEvaluationRecord]
    total: int
    limit: int
    offset: int


class RuleStatusToggleRequest(BaseModel):
    """Request payload to toggle active status of a rule."""

    is_active: bool


class RuleEngineHealthResponse(BaseModel):
    """Health and queue telemetry status of the rule engine and consumer."""

    status: str
    is_durable: bool
    total_rules: int
    active_rules: int
    consumer: dict[str, Any]
    processing_queue: dict[str, Any]


class BatchProcessResponse(BaseModel):
    """Result of an on-demand batch event evaluation cycle."""

    claimed: int
    completed: int
    failed: int
    matched: int


# ── Health & Observability ────────────────────────────────────────────────────


@router.get(
    "/consumer/health",
    response_model=SuccessResponse[RuleEngineHealthResponse],
    summary="Inspect rule engine and event consumer health telemetry",
)
async def get_rule_engine_health(
    service: Annotated[OperationalRuleService, Depends(get_rule_service)],
    current_user: Annotated[UserDocument, Depends(require_permission("rules.read"))],
) -> SuccessResponse[RuleEngineHealthResponse]:
    """Retrieve health and processing queue telemetry for the rule engine subsystem."""
    health_data = await service.get_health_status()
    return SuccessResponse(
        data=RuleEngineHealthResponse(**health_data),
        meta=ResponseMeta(),
    )


@router.post(
    "/consumer/process-batch",
    response_model=SuccessResponse[BatchProcessResponse],
    summary="Trigger an on-demand event consumption and rule evaluation batch",
)
async def process_event_batch(
    service: Annotated[OperationalRuleService, Depends(get_rule_service)],
    current_user: Annotated[UserDocument, Depends(require_permission("rules.manage"))],
    facility_id: Annotated[str | None, Query(description="Target facility ID")] = None,
) -> SuccessResponse[BatchProcessResponse]:
    """Execute an on-demand batch cycle to evaluate eligible unconsumed events against active rules."""
    try:
        result = await service.process_batch(current_user=current_user, facility_id=facility_id)
        return SuccessResponse(
            data=BatchProcessResponse(**result),
            meta=ResponseMeta(),
        )
    except RuleValidationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except RulePersistenceError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


# ── Operational Rule Management ───────────────────────────────────────────────


@router.post(
    "",
    response_model=SuccessResponse[OperationalRule],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new declarative operational rule",
)
async def create_rule(
    rule: OperationalRule,
    service: Annotated[OperationalRuleService, Depends(get_rule_service)],
    current_user: Annotated[UserDocument, Depends(require_permission("rules.manage"))],
) -> SuccessResponse[OperationalRule]:
    """Create a new declarative operational rule with validated conditions and author metadata."""
    try:
        created = await service.create_rule(rule=rule, current_user=current_user)
        return SuccessResponse(data=created, meta=ResponseMeta())
    except RuleValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except RuleConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except RulePersistenceError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.get(
    "",
    response_model=SuccessResponse[RuleListResponse],
    summary="List operational rules with facility isolation",
)
async def list_rules(
    service: Annotated[OperationalRuleService, Depends(get_rule_service)],
    current_user: Annotated[UserDocument, Depends(require_permission("rules.read"))],
    facility_id: Annotated[str | None, Query(description="Filter by facility ID")] = None,
    domain: Annotated[RuleDomain | None, Query(description="Filter by operational domain")] = None,
    is_active: Annotated[bool | None, Query(description="Filter by active status")] = None,
    event_type: Annotated[EventType | None, Query(description="Filter by supported event type")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 50,
    offset: Annotated[int, Query(ge=0, description="Pagination offset")] = 0,
) -> SuccessResponse[RuleListResponse]:
    """Query operational rules with multi-tenant facility boundaries."""
    try:
        rules, total = await service.list_rules(
            current_user=current_user,
            facility_id=facility_id,
            domain=domain,
            is_active=is_active,
            event_type=event_type,
            limit=limit,
            offset=offset,
        )
        return SuccessResponse(
            data=RuleListResponse(items=rules, total=total, limit=limit, offset=offset),
            meta=ResponseMeta(),
        )
    except RuleValidationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except RulePersistenceError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.get(
    "/evaluations",
    response_model=SuccessResponse[EvaluationListResponse],
    summary="Query rule evaluation records with evidence provenance",
)
async def query_evaluations(
    service: Annotated[OperationalRuleService, Depends(get_rule_service)],
    current_user: Annotated[UserDocument, Depends(require_permission("rules.read"))],
    facility_id: Annotated[str | None, Query(description="Filter by facility ID")] = None,
    rule_id: Annotated[str | None, Query(description="Filter by rule ID")] = None,
    domain: Annotated[RuleDomain | None, Query(description="Filter by domain")] = None,
    severity: Annotated[RuleSeverity | None, Query(description="Filter by severity")] = None,
    status_filter: Annotated[
        RuleEvaluationStatus | None, Query(alias="status", description="Filter by evaluation status")
    ] = None,
    matched_only: Annotated[bool, Query(description="Return only matched evaluations")] = False,
    start_time: Annotated[datetime | None, Query(description="Start time (UTC)")] = None,
    end_time: Annotated[datetime | None, Query(description="End time (UTC)")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 50,
    offset: Annotated[int, Query(ge=0, description="Pagination offset")] = 0,
) -> SuccessResponse[EvaluationListResponse]:
    """Query evaluation findings with time window filtering and anti-IDOR isolation."""
    if start_time and end_time and start_time > end_time:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_time cannot be after end_time in evaluation search.",
        )

    try:
        evals, total = await service.query_evaluations(
            current_user=current_user,
            facility_id=facility_id,
            rule_id=rule_id,
            domain=domain,
            severity=severity,
            status=status_filter,
            matched_only=matched_only,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )
        return SuccessResponse(
            data=EvaluationListResponse(items=evals, total=total, limit=limit, offset=offset),
            meta=ResponseMeta(),
        )
    except RuleValidationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except RulePersistenceError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.get(
    "/evaluations/{evaluation_id}",
    response_model=SuccessResponse[RuleEvaluationRecord],
    summary="Retrieve an individual rule evaluation finding by ID",
)
async def get_evaluation_by_id(
    evaluation_id: str,
    service: Annotated[OperationalRuleService, Depends(get_rule_service)],
    current_user: Annotated[UserDocument, Depends(require_permission("rules.read"))],
) -> SuccessResponse[RuleEvaluationRecord]:
    """Retrieve full evaluation details and evidence references (anti-IDOR protected)."""
    try:
        eval_record = await service.get_evaluation(evaluation_id=evaluation_id, current_user=current_user)
        return SuccessResponse(data=eval_record, meta=ResponseMeta())
    except RuleNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule evaluation with ID '{evaluation_id}' was not found.",
        ) from None
    except RulePersistenceError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.get(
    "/{rule_id}",
    response_model=SuccessResponse[OperationalRule],
    summary="Retrieve an operational rule definition by ID",
)
async def get_rule_by_id(
    rule_id: str,
    service: Annotated[OperationalRuleService, Depends(get_rule_service)],
    current_user: Annotated[UserDocument, Depends(require_permission("rules.read"))],
    version: Annotated[int | None, Query(ge=1, description="Specific historical version")] = None,
) -> SuccessResponse[OperationalRule]:
    """Retrieve operational rule definition (anti-IDOR protected)."""
    try:
        rule = await service.get_rule(rule_id=rule_id, current_user=current_user, version=version)
        return SuccessResponse(data=rule, meta=ResponseMeta())
    except RuleNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule with ID '{rule_id}' was not found.",
        ) from None
    except RulePersistenceError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.put(
    "/{rule_id}",
    response_model=SuccessResponse[OperationalRule],
    summary="Create a new version of an operational rule",
)
async def update_rule(
    rule_id: str,
    updated_rule: OperationalRule,
    service: Annotated[OperationalRuleService, Depends(get_rule_service)],
    current_user: Annotated[UserDocument, Depends(require_permission("rules.manage"))],
) -> SuccessResponse[OperationalRule]:
    """Update rule definition, bumping version and archiving previous version."""
    try:
        versioned = await service.update_rule(
            rule_id=rule_id,
            updated_rule=updated_rule,
            current_user=current_user,
        )
        return SuccessResponse(data=versioned, meta=ResponseMeta())
    except RuleNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule with ID '{rule_id}' was not found.",
        ) from None
    except RuleValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except RulePersistenceError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.patch(
    "/{rule_id}/status",
    response_model=SuccessResponse[OperationalRule],
    summary="Enable or disable an operational rule",
)
async def set_rule_status(
    rule_id: str,
    request: RuleStatusToggleRequest,
    service: Annotated[OperationalRuleService, Depends(get_rule_service)],
    current_user: Annotated[UserDocument, Depends(require_permission("rules.manage"))],
) -> SuccessResponse[OperationalRule]:
    """Toggle operational rule active status."""
    try:
        updated = await service.set_rule_active(
            rule_id=rule_id,
            is_active=request.is_active,
            current_user=current_user,
        )
        return SuccessResponse(data=updated, meta=ResponseMeta())
    except RuleNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule with ID '{rule_id}' was not found.",
        ) from None
    except RuleValidationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except RulePersistenceError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.get(
    "/{rule_id}/versions",
    response_model=SuccessResponse[list[OperationalRule]],
    summary="View historical versions of an operational rule",
)
async def list_rule_versions(
    rule_id: str,
    service: Annotated[OperationalRuleService, Depends(get_rule_service)],
    current_user: Annotated[UserDocument, Depends(require_permission("rules.read"))],
) -> SuccessResponse[list[OperationalRule]]:
    """Retrieve full version history for an operational rule."""
    try:
        versions = await service.list_rule_versions(rule_id=rule_id, current_user=current_user)
        return SuccessResponse(data=versions, meta=ResponseMeta())
    except RuleNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule with ID '{rule_id}' was not found.",
        ) from None
    except RulePersistenceError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
