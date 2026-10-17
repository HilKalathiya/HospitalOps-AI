"""
HospitalOps AI — API Dependencies.

Provides reusable dependencies for:
- Authentication (get_current_user)
- Authorization (require_role, require_permission)
- Database/Services injection
"""

import logging
from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis

from app.core.security import decode_access_token, get_permissions_for_role
from app.data_ingestion.repositories import (
    DataIngestionRunRepository,
    HistoricalAdmissionsRepository,
    HistoricalHospitalCapacityRepository,
)
from app.database.client import get_database
from app.database.redis_client import get_redis
from app.models.user import Role, UserDocument
from app.repositories.admissions import AdmissionsRepository
from app.repositories.audit_logs import AuditLogsRepository
from app.repositories.beds import BedsRepository
from app.repositories.departments import DepartmentsRepository
from app.repositories.optimizations import OptimizationsRepository
from app.repositories.patients import PatientsRepository
from app.repositories.resources import ResourcesRepository
from app.repositories.simulations import SimulationsRepository
from app.repositories.users import UserRepository
from app.services.admissions import AdmissionService
from app.services.auth import AuthService
from app.services.beds import BedService
from app.services.forecast import ForecastService
from app.services.optimization import OptimizationService
from app.services.patients import PatientService
from app.services.resources import ResourceService
from app.services.simulation import SimulationService

logger = logging.getLogger(__name__)

# We use HTTPBearer to automatically extract the token from the Authorization header.
# auto_error=False allows us to handle missing tokens manually to return custom 401s.
security = HTTPBearer(auto_error=False)


# ── Repositories & Services ───────────────────────────────────────────────────


def get_user_repository(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],  # type: ignore[type-arg]
) -> UserRepository:
    return UserRepository(db)


def get_patient_repository(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],  # type: ignore[type-arg]
) -> PatientsRepository:
    return PatientsRepository(db)


def get_admission_repository(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],  # type: ignore[type-arg]
) -> AdmissionsRepository:
    return AdmissionsRepository(db)


def get_audit_log_repository(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],  # type: ignore[type-arg]
) -> AuditLogsRepository:
    return AuditLogsRepository(db)


def get_beds_repository(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],  # type: ignore[type-arg]
) -> BedsRepository:
    return BedsRepository(db)


def get_resources_repository(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],  # type: ignore[type-arg]
) -> ResourcesRepository:
    return ResourcesRepository(db)


def get_data_ingestion_run_repository(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],  # type: ignore[type-arg]
) -> DataIngestionRunRepository:
    return DataIngestionRunRepository(db)


def get_historical_admissions_repository(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],  # type: ignore[type-arg]
) -> HistoricalAdmissionsRepository:
    return HistoricalAdmissionsRepository(db)


def get_historical_capacity_repository(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],  # type: ignore[type-arg]
) -> HistoricalHospitalCapacityRepository:
    return HistoricalHospitalCapacityRepository(db)


def get_auth_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
    redis: Annotated[Redis, Depends(get_redis)],  # type: ignore[type-arg]
) -> AuthService:
    return AuthService(user_repo, redis)


def get_patient_service(
    patient_repo: Annotated[PatientsRepository, Depends(get_patient_repository)],
    audit_repo: Annotated[AuditLogsRepository, Depends(get_audit_log_repository)],
) -> PatientService:
    return PatientService(patient_repo, audit_repo)


def get_admission_service(
    admission_repo: Annotated[AdmissionsRepository, Depends(get_admission_repository)],
    patient_repo: Annotated[PatientsRepository, Depends(get_patient_repository)],
    audit_repo: Annotated[AuditLogsRepository, Depends(get_audit_log_repository)],
) -> AdmissionService:
    return AdmissionService(admission_repo, patient_repo, audit_repo)


def get_bed_service(
    beds_repo: Annotated[BedsRepository, Depends(get_beds_repository)],
    patient_repo: Annotated[PatientsRepository, Depends(get_patient_repository)],
    audit_repo: Annotated[AuditLogsRepository, Depends(get_audit_log_repository)],
) -> BedService:
    return BedService(beds_repo, patient_repo, audit_repo)


def get_resource_service(
    resources_repo: Annotated[ResourcesRepository, Depends(get_resources_repository)],
    audit_repo: Annotated[AuditLogsRepository, Depends(get_audit_log_repository)],
) -> ResourceService:
    return ResourceService(resources_repo, audit_repo)


def get_simulations_repository(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],  # type: ignore[type-arg]
) -> SimulationsRepository:
    return SimulationsRepository(db)


async def get_optional_database() -> AsyncIOMotorDatabase | None:  # type: ignore[type-arg]
    """Returns database instance if initialised, or None without raising."""
    from app.database.client import _database
    return _database


def get_optional_simulations_repository(
    db: Annotated[AsyncIOMotorDatabase | None, Depends(get_optional_database)] = None,  # type: ignore[type-arg]
) -> SimulationsRepository | None:
    return SimulationsRepository(db) if db is not None else None


def get_optional_beds_repository(
    db: Annotated[AsyncIOMotorDatabase | None, Depends(get_optional_database)] = None,  # type: ignore[type-arg]
) -> BedsRepository | None:
    return BedsRepository(db) if db is not None else None


def get_optional_resources_repository(
    db: Annotated[AsyncIOMotorDatabase | None, Depends(get_optional_database)] = None,  # type: ignore[type-arg]
) -> ResourcesRepository | None:
    return ResourcesRepository(db) if db is not None else None


def get_optional_admission_repository(
    db: Annotated[AsyncIOMotorDatabase | None, Depends(get_optional_database)] = None,  # type: ignore[type-arg]
) -> AdmissionsRepository | None:
    return AdmissionsRepository(db) if db is not None else None


def get_optional_audit_log_repository(
    db: Annotated[AsyncIOMotorDatabase | None, Depends(get_optional_database)] = None,  # type: ignore[type-arg]
) -> AuditLogsRepository | None:
    return AuditLogsRepository(db) if db is not None else None


def get_simulation_service(
    simulations_repo: Annotated[
        SimulationsRepository | None, Depends(get_optional_simulations_repository)
    ] = None,
    beds_repo: Annotated[BedsRepository | None, Depends(get_optional_beds_repository)] = None,
    resources_repo: Annotated[
        ResourcesRepository | None, Depends(get_optional_resources_repository)
    ] = None,
    admissions_repo: Annotated[
        AdmissionsRepository | None, Depends(get_optional_admission_repository)
    ] = None,
    audit_repo: Annotated[
        AuditLogsRepository | None, Depends(get_optional_audit_log_repository)
    ] = None,
) -> SimulationService:
    return SimulationService(
        simulations_repo, beds_repo, resources_repo, admissions_repo, audit_repo
    )


def get_optional_optimizations_repository(
    db: Annotated[AsyncIOMotorDatabase | None, Depends(get_optional_database)] = None,  # type: ignore[type-arg]
) -> OptimizationsRepository | None:
    return OptimizationsRepository(db) if db is not None else None


def get_optional_departments_repository(
    db: Annotated[AsyncIOMotorDatabase | None, Depends(get_optional_database)] = None,  # type: ignore[type-arg]
) -> DepartmentsRepository | None:
    return DepartmentsRepository(db) if db is not None else None


def get_optimization_service(
    optimizations_repo: Annotated[
        OptimizationsRepository | None, Depends(get_optional_optimizations_repository)
    ] = None,
    departments_repo: Annotated[
        DepartmentsRepository | None, Depends(get_optional_departments_repository)
    ] = None,
    beds_repo: Annotated[BedsRepository | None, Depends(get_optional_beds_repository)] = None,
    resources_repo: Annotated[
        ResourcesRepository | None, Depends(get_optional_resources_repository)
    ] = None,
    audit_repo: Annotated[
        AuditLogsRepository | None, Depends(get_optional_audit_log_repository)
    ] = None,
) -> OptimizationService:
    return OptimizationService(
        optimizations_repo,
        departments_repo,
        beds_repo,
        resources_repo,
        audit_repo,
    )


def get_optional_user_repository(
    db: Annotated[AsyncIOMotorDatabase | None, Depends(get_optional_database)] = None,  # type: ignore[type-arg]
) -> UserRepository | None:
    return UserRepository(db) if db is not None else None


def get_optional_admissions_repository(
    db: Annotated[AsyncIOMotorDatabase | None, Depends(get_optional_database)] = None,  # type: ignore[type-arg]
) -> HistoricalAdmissionsRepository | None:
    return HistoricalAdmissionsRepository(db) if db is not None else None


def get_optional_capacity_repository(
    db: Annotated[AsyncIOMotorDatabase | None, Depends(get_optional_database)] = None,  # type: ignore[type-arg]
) -> HistoricalHospitalCapacityRepository | None:
    return HistoricalHospitalCapacityRepository(db) if db is not None else None


def get_forecast_service(
    admissions_repo: Annotated[
        HistoricalAdmissionsRepository | None, Depends(get_optional_admissions_repository)
    ] = None,
    capacity_repo: Annotated[
        HistoricalHospitalCapacityRepository | None, Depends(get_optional_capacity_repository)
    ] = None,
) -> ForecastService:
    return ForecastService(
        admissions_repo=admissions_repo,
        capacity_repo=capacity_repo,
    )



# ── Authentication ────────────────────────────────────────────────────────────


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    user_repo: Annotated[UserRepository | None, Depends(get_optional_user_repository)] = None,
) -> UserDocument:
    """
    Validate the JWT access token and retrieve the current user.
    Returns 401 if unauthenticated, token is invalid, or user is inactive.
    Supports demo session tokens and offline-database development gracefully.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Bearer token missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Local development demo session token support
    if credentials.credentials == "demo_token":
        return UserDocument(
            user_id="usr_admin",
            email="admin@hospitalops.local",
            name="System Administrator",
            role=Role.ADMIN,
            password_hash="demo_hash",
            is_active=True,
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err
    except jwt.InvalidTokenError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user_repo is not None:
        user = await user_repo.find_by_user_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User no longer exists.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user

    # Stateless fallback for local development when database is offline
    role_str = payload.get("role", "ADMIN")
    role_enum = Role(role_str) if role_str in Role.__members__.values() else Role.ADMIN
    return UserDocument(
        user_id=user_id,
        email=f"{user_id}@hospitalops.local",
        name=f"User {user_id}",
        role=role_enum,
        password_hash="stateless_hash",
        is_active=True,
    )


# ── Authorization ─────────────────────────────────────────────────────────────


def require_role(required_role: Role) -> Callable[[UserDocument], UserDocument]:
    """
    Dependency factory to restrict an endpoint to a specific role.
    Usage: Depends(require_role(Role.ADMIN))
    """

    def role_checker(
        current_user: Annotated[UserDocument, Depends(get_current_user)],
    ) -> UserDocument:
        if current_user.role != required_role:
            logger.warning(
                "Access denied: User %s (Role %s) attempted to access route requiring %s",
                current_user.user_id,
                current_user.role,
                required_role,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires {required_role.value} role.",
            )
        return current_user

    return role_checker


def require_permission(required_permission: str) -> Callable[[UserDocument], UserDocument]:
    """
    Dependency factory to restrict an endpoint to a specific granular permission.
    Usage: Depends(require_permission("beds.manage"))

    This abstracts role checks away from endpoint logic, allowing flexible RBAC updates.
    """

    def permission_checker(
        current_user: Annotated[UserDocument, Depends(get_current_user)],
    ) -> UserDocument:
        permissions = get_permissions_for_role(current_user.role)
        if required_permission not in permissions:
            logger.warning(
                "Access denied: User %s (Role %s) attempted to access route requiring permission %s",
                current_user.user_id,
                current_user.role,
                required_permission,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires '{required_permission}' permission.",
            )
        return current_user

    return permission_checker
