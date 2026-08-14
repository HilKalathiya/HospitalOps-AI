"""
HospitalOps AI — FastAPI application entry point.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import v1_router
from app.core.config import get_settings
from app.core.exceptions import HospitalOpsError
from app.core.logging import configure_logging
from app.database.client import close_db, init_db, init_indexes
from app.database.redis_client import close_redis, init_redis

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    configure_logging(settings.log_level)

    import logging

    logger = logging.getLogger(__name__)
    logger.info(
        "HospitalOps AI starting | env=%s version=0.1.0",
        settings.app_env,
    )

    # ── Database & Redis startup ──────────────────────────────────────────────
    try:
        await init_db(settings)
        await init_indexes()
        await init_redis(settings)
    except Exception as exc:
        logger.critical(
            "Database/Redis initialization failed during startup. "
            "Database-dependent endpoints will fail: %s",
            exc,
        )

    yield

    # ── Database & Redis shutdown ─────────────────────────────────────────────
    try:
        await close_redis()
        await close_db()
    except Exception as exc:
        logger.error("Error closing database/redis connection: %s", exc)
    logger.info("HospitalOps AI shutting down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        description="Agentic AI-powered hospital operations intelligence platform.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Allow configured origins only. In production, CORS_ORIGINS should be
    # restricted to the actual frontend domain.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # ── Request ID Middleware ─────────────────────────────────────────────────
    import uuid

    from starlette.middleware.base import BaseHTTPMiddleware

    from app.core.request_context import request_id_ctx_var

    class RequestIdMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            request_id = request.headers.get("X-Request-ID")
            if not request_id:
                request_id = str(uuid.uuid4())

            # Set the context variable
            token = request_id_ctx_var.set(request_id)

            try:
                response = await call_next(request)
                response.headers["X-Request-ID"] = request_id
                return response
            finally:
                request_id_ctx_var.reset(token)

    app.add_middleware(RequestIdMiddleware)

    # ── Exception handlers ────────────────────────────────────────────────────
    @app.exception_handler(HospitalOpsError)
    async def hospitalops_error_handler(request: Request, exc: HospitalOpsError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "message": exc.message,
                "detail": exc.detail,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        import logging

        logging.getLogger(__name__).exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred.",
                "detail": None,
            },
        )

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(v1_router, prefix=settings.api_prefix)

    return app


app = create_app()
