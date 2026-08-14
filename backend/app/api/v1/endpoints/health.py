"""
HospitalOps AI — /health endpoint.

Returns the operational status of the application and its dependencies.
This endpoint is used by Docker health checks, load balancers, and monitoring.
"""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter

from app.schemas.common import HealthResponse, ServiceStatus

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=HealthResponse,
    summary="Application health check",
    description=(
        "Returns the current health status of HospitalOps AI and its dependencies. "
        "A 200 response indicates the application is running. "
        "Dependency health checks are advisory and do not affect the HTTP status code."
    ),
)
async def health_check() -> HealthResponse:
    """Return application health status."""
    logger.debug("Health check requested")

    return HealthResponse(
        status=ServiceStatus.OK,
        app_name="HospitalOps AI",
        version="0.1.0",
        timestamp=datetime.now(tz=UTC),
        chunk="0.1 — Foundation",
    )
