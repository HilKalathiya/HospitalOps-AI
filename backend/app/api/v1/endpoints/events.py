"""
HospitalOps AI — Operational Events REST Endpoints (Milestone 6, Chunk 6.1).

Exposes secured, audited REST endpoints for publishing and querying operational events:
- POST /api/v1/events/publish : Ingest and record an operational event (idempotent duplicate protected)
- GET  /api/v1/events/        : Query historical operational events with server-side facility isolation
- GET  /api/v1/events/{id}    : Retrieve an individual operational event by ID (Anti-IDOR protected)
- GET  /api/v1/events/taxonomy/catalog : Introspect the registered event taxonomy definitions

Safety & Security Rules:
- Server-side JWT authentication & RBAC permissions required (events.publish, events.read).
- Client cannot spoof organization or facility boundaries; non-admin users are strictly scoped.
- Zero-trust anti-IDOR: queries for unowned/unauthorized events return 404 concealing existence.
- Zero mutation of hospital operational records (patients, admissions, beds, resources).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.dependencies import get_event_service, require_permission
from app.core.request_context import get_request_id
from app.events.contracts import (
    EntityType,
    EventCategory,
    EventType,
    OperationalEvent,
)
from app.events.exceptions import (
    EventConflictError,
    EventPersistenceError,
    EventValidationError,
)
from app.events.service import OperationalEventService
from app.events.taxonomy import EventDefinition, get_all_event_definitions
from app.models.user import Role, UserDocument
from app.repositories.events import EventQueryFilter
from app.schemas.common import ResponseMeta, SuccessResponse

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Response / Request DTOs ───────────────────────────────────────────────────


class EventPublishResponse(BaseModel):
    """Payload returned when an event is published or idempotently re-submitted."""

    event_id: str
    event_type: EventType
    category: EventCategory
    is_duplicate: bool
    recorded_at: datetime
    facility_id: str
    payload_hash: str


class EventListResponse(BaseModel):
    """Paginated collection of operational events."""

    items: list[OperationalEvent]
    total: int
    limit: int
    offset: int


class EventCatalogResponse(BaseModel):
    """Catalog of all documented operational event definitions."""

    definitions: list[EventDefinition]
    total: int


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post(
    "/publish",
    response_model=SuccessResponse[EventPublishResponse],
    status_code=status.HTTP_200_OK,
    summary="Publish an operational event",
)
async def publish_event(
    event: OperationalEvent,
    current_user: Annotated[UserDocument, Depends(require_permission("events.publish"))],
    service: Annotated[OperationalEventService, Depends(get_event_service)],
) -> SuccessResponse[EventPublishResponse]:
    """
    Ingest and record a strongly-typed operational event into the system of record.
    Supports atomic idempotency: identical retries return the existing event.
    """
    # Enforce facility boundary: non-admin users cannot publish under arbitrary facilities
    user_facility = getattr(current_user, "facility_id", None) or getattr(current_user, "department_id", None)
    if current_user.role != Role.ADMIN and user_facility:
        if event.facility_id != user_facility and event.facility_id != "default_facility":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User is restricted to facility '{user_facility}'. Cannot publish to '{event.facility_id}'.",
            )
        # Inherit user's assigned facility
        if event.facility_id == "default_facility":
            event.facility_id = user_facility

    try:
        persisted, is_duplicate = await service.publish_event(event)
    except EventConflictError as exc:
        logger.warning("Event publishing conflict | event_id=%s error=%s", event.event_id, exc)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except EventValidationError as exc:
        logger.warning("Event validation failure | event_id=%s error=%s", event.event_id, exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except EventPersistenceError as exc:
        logger.error("Event persistence failure | event_id=%s error=%s", event.event_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist operational event to store.",
        ) from exc

    return SuccessResponse(
        data=EventPublishResponse(
            event_id=persisted.event_id,
            event_type=persisted.event_type,
            category=persisted.category,
            is_duplicate=is_duplicate,
            recorded_at=persisted.recorded_at,
            facility_id=persisted.facility_id,
            payload_hash=persisted.payload_hash,
        ),
        meta=ResponseMeta(
            request_id=get_request_id(),
            timestamp=datetime.now(UTC),
        ),
    )


@router.get(
    "",
    response_model=SuccessResponse[EventListResponse],
    summary="Query operational events",
)
async def query_events(
    current_user: Annotated[UserDocument, Depends(require_permission("events.read"))],
    service: Annotated[OperationalEventService, Depends(get_event_service)],
    facility_id: str | None = None,
    event_type: EventType | None = None,
    category: EventCategory | None = None,
    entity_type: EntityType | None = None,
    entity_id: str | None = None,
    correlation_id: str | None = None,
    source: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> SuccessResponse[EventListResponse]:
    """
    Retrieve historical operational events with server-side facility isolation and pagination.
    """
    effective_facility = facility_id
    user_facility = getattr(current_user, "facility_id", None) or getattr(current_user, "department_id", None)

    # Scoping constraint: non-admins are strictly locked to their assigned facility
    if current_user.role != Role.ADMIN and user_facility:
        effective_facility = user_facility

    filters = EventQueryFilter(
        facility_id=effective_facility,
        event_types=[event_type] if event_type else None,
        categories=[category] if category else None,
        entity_type=entity_type,
        entity_id=entity_id,
        correlation_id=correlation_id,
        source=source,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )

    items, total = await service.query_events(filters)

    return SuccessResponse(
        data=EventListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        ),
        meta=ResponseMeta(
            request_id=get_request_id(),
            timestamp=datetime.now(UTC),
        ),
    )


@router.get(
    "/taxonomy/catalog",
    response_model=SuccessResponse[EventCatalogResponse],
    summary="List operational event taxonomy catalog",
)
async def get_taxonomy_catalog(
    current_user: Annotated[UserDocument, Depends(require_permission("events.read"))],
) -> SuccessResponse[EventCatalogResponse]:
    """
    Introspect all registered event definitions, permitted sources, and rule eligibility.
    """
    definitions = get_all_event_definitions()
    return SuccessResponse(
        data=EventCatalogResponse(
            definitions=definitions,
            total=len(definitions),
        ),
        meta=ResponseMeta(
            request_id=get_request_id(),
            timestamp=datetime.now(UTC),
        ),
    )


@router.get(
    "/{event_id}",
    response_model=SuccessResponse[OperationalEvent],
    summary="Retrieve operational event by ID",
)
async def get_event_by_id(
    event_id: str,
    current_user: Annotated[UserDocument, Depends(require_permission("events.read"))],
    service: Annotated[OperationalEventService, Depends(get_event_service)],
) -> SuccessResponse[OperationalEvent]:
    """
    Retrieve a single operational event. Unowned/cross-tenant queries conceal existence with 404.
    """
    user_facility = getattr(current_user, "facility_id", None) or getattr(current_user, "department_id", None)
    facility_scope = None if current_user.role == Role.ADMIN else user_facility

    event = await service.get_event(event_id=event_id, facility_id=facility_scope)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Operational event '{event_id}' not found.",
        )

    return SuccessResponse(
        data=event,
        meta=ResponseMeta(
            request_id=get_request_id(),
            timestamp=datetime.now(UTC),
        ),
    )
