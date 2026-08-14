"""
HospitalOps AI API v1 — aggregate router.

All v1 endpoint routers are registered here.
This router is mounted at the api_prefix defined in Settings (default: /api/v1).
"""

from fastapi import APIRouter

from app.api.v1.endpoints import admissions, auth, beds, health, patients, resources

v1_router = APIRouter()

v1_router.include_router(
    health.router,
    prefix="/health",
    tags=["health"],
)

v1_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["auth"],
)

v1_router.include_router(
    patients.router,
    prefix="/patients",
    tags=["patients"],
)

v1_router.include_router(
    admissions.router,
    prefix="/admissions",
    tags=["admissions"],
)

v1_router.include_router(
    beds.router,
    prefix="/beds",
    tags=["beds"],
)

v1_router.include_router(
    resources.router,
    prefix="/resources",
    tags=["resources"],
)

# Future endpoint routers will be registered here, for example:
# from app.api.v1.endpoints import beds, admissions, resources, forecast
# v1_router.include_router(beds.router, prefix="/beds", tags=["beds"])
