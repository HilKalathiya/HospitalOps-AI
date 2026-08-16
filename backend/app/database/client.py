"""
HospitalOps AI — MongoDB async client lifecycle.

Provides:
  - Motor (async) client initialisation and teardown
  - get_database() dependency for FastAPI injection
  - init_indexes() to create all collection indexes at startup

Design:
  - One Motor client per application process.
  - Client is held in module-level state (initialised once at startup).
  - All database access goes through get_database(); never import the client directly.
  - Index creation is idempotent — safe to run on every startup.

Usage in FastAPI lifespan:
    from app.database.client import init_db, close_db, init_indexes
    await init_db(settings)
    await init_indexes()
    yield
    await close_db()

Usage as FastAPI dependency:
    from app.database.client import get_database
    db: AsyncIOMotorDatabase = Depends(get_database)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, IndexModel

from app.core.config import Settings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ── Module-level state ────────────────────────────────────────────────────────
# Holds the single Motor client instance for the lifetime of the process.
# Initialised by init_db() at application startup.

_client: AsyncIOMotorClient | None = None  # type: ignore[type-arg]
_database: AsyncIOMotorDatabase | None = None  # type: ignore[type-arg]


# ── Lifecycle ─────────────────────────────────────────────────────────────────


async def init_db(settings: Settings) -> None:
    """
    Create the Motor client and select the working database.
    Called once at application startup via FastAPI lifespan.
    """
    global _client, _database  # noqa: PLW0603

    logger.info(
        "Connecting to MongoDB | uri=%s db=%s",
        _redact_uri(settings.mongodb_uri),
        settings.mongodb_database,
    )

    _client = AsyncIOMotorClient(
        settings.mongodb_uri,
        serverSelectionTimeoutMS=5_000,
        connectTimeoutMS=5_000,
        socketTimeoutMS=10_000,
    )
    _database = _client[settings.mongodb_database]

    # Verify connectivity eagerly at startup so the application fails fast
    # rather than serving requests with a broken database connection.
    await _database.command("ping")
    logger.info("MongoDB connection established | db=%s", settings.mongodb_database)


async def close_db() -> None:
    """
    Close the Motor client.
    Called once at application shutdown via FastAPI lifespan.
    """
    global _client, _database  # noqa: PLW0603

    if _client is not None:
        _client.close()
        _client = None
        _database = None
        logger.info("MongoDB connection closed")


async def get_database() -> AsyncIOMotorDatabase:  # type: ignore[type-arg]
    """
    FastAPI dependency — returns the active Motor database instance.

    Usage:
        db: AsyncIOMotorDatabase = Depends(get_database)
    """
    if _database is None:
        msg = "Database not initialised. " "Ensure init_db() is called during application startup."
        raise RuntimeError(msg)
    return _database


# ── Index initialisation ──────────────────────────────────────────────────────


async def init_indexes() -> None:
    """
    Create all collection indexes.

    This function is idempotent — MongoDB ignores index creation if an identical
    index already exists. Safe to call on every startup.

    Indexes are grouped by collection. See each block for the rationale.
    """
    if _database is None:
        msg = "Cannot initialise indexes: database not connected."
        raise RuntimeError(msg)

    db = _database

    # ── departments ───────────────────────────────────────────────────────────
    # Unique code: departments have a short business code (e.g. "ICU", "ER").
    # name: human-readable lookup.
    # is_active: filter active departments in list queries.
    await db["departments"].create_indexes(
        [
            IndexModel([("code", ASCENDING)], unique=True, name="departments_code_unique"),
            IndexModel([("name", ASCENDING)], name="departments_name"),
            IndexModel([("is_active", ASCENDING)], name="departments_is_active"),
        ]
    )

    # ── patients ──────────────────────────────────────────────────────────────
    # Unique external_patient_id: hospital's own MRN/patient number.
    # department_id + admission_status: find active patients in a department.
    # admitted_at desc: time-ordered patient list.
    await db["patients"].create_indexes(
        [
            IndexModel(
                [("external_patient_id", ASCENDING)],
                unique=True,
                sparse=True,  # not every patient may have an external ID yet
                name="patients_external_id_unique",
            ),
            IndexModel(
                [("department_id", ASCENDING), ("admission_status", ASCENDING)],
                name="patients_dept_status",
            ),
            IndexModel([("admitted_at", DESCENDING)], name="patients_admitted_at"),
        ]
    )

    # ── admissions ────────────────────────────────────────────────────────────
    # status + admitted_at: list active admissions ordered by time (primary query).
    # department_id + status: beds-by-department queries.
    # patient_id: look up all admissions for a patient.
    # icu_required: ICU demand queries (needed by forecasting layer later).
    # discharged_at: duration / throughput calculations.
    await db["admissions"].create_indexes(
        [
            IndexModel(
                [("status", ASCENDING), ("admitted_at", DESCENDING)],
                name="admissions_status_admitted_at",
            ),
            IndexModel(
                [("department_id", ASCENDING), ("status", ASCENDING)],
                name="admissions_dept_status",
            ),
            IndexModel([("patient_id", ASCENDING)], name="admissions_patient_id"),
            IndexModel([("icu_required", ASCENDING)], name="admissions_icu_required"),
            IndexModel([("discharged_at", DESCENDING)], name="admissions_discharged_at"),
        ]
    )

    # ── beds ──────────────────────────────────────────────────────────────────
    # department_id + status: available beds in a department (most common query).
    # is_icu: ICU capacity queries.
    # patient_id: find which bed a patient is in.
    await db["beds"].create_indexes(
        [
            IndexModel(
                [("department_id", ASCENDING), ("status", ASCENDING)],
                name="beds_dept_status",
            ),
            IndexModel([("is_icu", ASCENDING)], name="beds_is_icu"),
            IndexModel(
                [("patient_id", ASCENDING)],
                sparse=True,  # only occupied beds have a patient_id
                name="beds_patient_id",
            ),
        ]
    )

    # ── resources ─────────────────────────────────────────────────────────────
    # department_id + resource_type: resources of a type in a department.
    # status: filter by operational status.
    # criticality: surface high-criticality shortages first.
    await db["resources"].create_indexes(
        [
            IndexModel(
                [("department_id", ASCENDING), ("resource_type", ASCENDING)],
                name="resources_dept_type",
            ),
            IndexModel([("status", ASCENDING)], name="resources_status"),
            IndexModel([("criticality", ASCENDING)], name="resources_criticality"),
        ]
    )

    # ── predictions ───────────────────────────────────────────────────────────
    # prediction_type + generated_at desc: latest forecast of a given type.
    # model_version: allow querying predictions from a specific model version.
    await db["predictions"].create_indexes(
        [
            IndexModel(
                [("prediction_type", ASCENDING), ("generated_at", DESCENDING)],
                name="predictions_type_generated_at",
            ),
            IndexModel([("model_version", ASCENDING)], name="predictions_model_version"),
        ]
    )

    # ── alerts ────────────────────────────────────────────────────────────────
    # severity + status: open alerts by severity (dashboard / triage queries).
    # triggered_at desc: chronological alert history.
    # department_id: department-scoped alert views.
    await db["alerts"].create_indexes(
        [
            IndexModel(
                [("severity", ASCENDING), ("status", ASCENDING)],
                name="alerts_severity_status",
            ),
            IndexModel([("triggered_at", DESCENDING)], name="alerts_triggered_at"),
            IndexModel(
                [("department_id", ASCENDING)],
                sparse=True,
                name="alerts_department_id",
            ),
        ]
    )

    # ── users ─────────────────────────────────────────────────────────────────
    # email: authentication lookup.
    # user_id: internal stable identifier.
    await db["users"].create_indexes(
        [
            IndexModel([("email", ASCENDING)], unique=True, name="users_email_unique"),
            IndexModel([("user_id", ASCENDING)], unique=True, name="users_user_id_unique"),
        ]
    )

    # ── audit_logs ────────────────────────────────────────────────────────────
    # entity_type + entity_id + timestamp: full audit trail for any entity.
    # actor_type + actor_id: all actions by a specific actor.
    # request_id: correlate audit entries with an API request.
    # timestamp desc: chronological audit log view.
    await db["audit_logs"].create_indexes(
        [
            IndexModel(
                [("entity_type", ASCENDING), ("entity_id", ASCENDING), ("timestamp", DESCENDING)],
                name="audit_logs_entity",
            ),
            IndexModel(
                [("actor_type", ASCENDING), ("actor_id", ASCENDING)],
                name="audit_logs_actor",
            ),
            IndexModel([("request_id", ASCENDING)], name="audit_logs_request_id"),
            IndexModel([("timestamp", DESCENDING)], name="audit_logs_timestamp"),
        ]
    )

    # ── data_ingestion_runs ───────────────────────────────────────────────────
    # run_id: unique identifier for an ingestion run.
    # source_hash: support idempotency checks.
    # dataset_name: querying runs by type.
    await db["data_ingestion_runs"].create_indexes(
        [
            IndexModel([("run_id", ASCENDING)], unique=True, name="ingestion_run_id_unique"),
            IndexModel([("source_hash", ASCENDING)], name="ingestion_source_hash"),
            IndexModel([("dataset_name", ASCENDING)], name="ingestion_dataset_name"),
        ]
    )

    # ── historical_admissions ─────────────────────────────────────────────────
    # source_record_id: unique lookup for idempotency.
    # admission_date: filtering by time.
    await db["historical_admissions"].create_indexes(
        [
            IndexModel([("source_record_id", ASCENDING)], unique=True, name="hist_adm_source_record_id_unique"),
            IndexModel([("admission_date", ASCENDING)], name="hist_adm_date"),
        ]
    )

    # ── historical_hospital_capacity ──────────────────────────────────────────
    # week_ending_date + geographic_aggregation: unique natural key.
    await db["historical_hospital_capacity"].create_indexes(
        [
            IndexModel(
                [("week_ending_date", ASCENDING), ("geographic_aggregation", ASCENDING)],
                unique=True,
                name="hist_cap_week_geo_unique",
            ),
            IndexModel([("week_ending_date", ASCENDING)], name="hist_cap_week"),
        ]
    )

    logger.info("MongoDB indexes initialised for all core collections")


# ── Helpers ───────────────────────────────────────────────────────────────────


def _redact_uri(uri: str) -> str:
    """
    Return a safe version of the MongoDB URI for logging.
    Replaces password (if present) with *****.
    """
    try:
        from urllib.parse import urlparse, urlunparse

        parsed = urlparse(uri)
        if parsed.password:
            netloc = parsed.netloc.replace(parsed.password, "*****")
            return urlunparse(parsed._replace(netloc=netloc))
    except Exception:  # noqa: BLE001
        return "<redacted>"
    return uri
