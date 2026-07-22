"""
Application entry point.

Wires together all routers, middleware, and startup/shutdown lifecycle events.
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1 import (
    auth,
    datasets,
    files,
    health,
    insights,
    queries,
    reports,
    visualizations,
)
from app.config import settings
from app.core.rate_limit import limiter
from app.db.session import create_tables
from app.middleware.error_handler import register_exception_handlers
from app.middleware.request_logger import RequestLoggingMiddleware
from app.utils.logger import configure_logging

logger = structlog.get_logger(__name__)


# ──────────────────────────────────────────────────────────────────
# Startup / Shutdown lifecycle
# ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup tasks before serving and cleanup on shutdown."""
    configure_logging(settings.log_level)
    logger.info("Starting AI BI Dashboard API", env=settings.app_env)

    # Dev/test: create tables directly from ORM metadata for convenience.
    # Production: schema is managed by versioned Alembic migrations, run
    # explicitly before the app starts (see docker-compose.yml / deploy
    # step and docs/GUIDE.md) — never auto-created here.
    if settings.app_env != "production":
        await create_tables()
        logger.info("Database ready (create_all, dev/test)")
    else:
        logger.info("Production mode — schema assumed managed by Alembic migrations")

    yield  # Application runs here

    logger.info("Shutting down AI BI Dashboard API")


# ──────────────────────────────────────────────────────────────────
# FastAPI application
# ──────────────────────────────────────────────────────────────────
def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="AI-powered Business Intelligence Dashboard API",
        version="1.0.0",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan,
    )

    # ── Rate limiting ──────────────────────────────────────────────
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # ── CORS ──────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request logging ───────────────────────────────────────────
    app.add_middleware(RequestLoggingMiddleware)

    # ── Custom exception handlers ─────────────────────────────────
    register_exception_handlers(app)

    # ── Root endpoint ─────────────────────────────────────────────
    @app.get("/")
    async def root():
        return {
            "service": settings.app_name,
            "status": "operational",
            "version": "1.0.0",
            "docs": "/docs" if settings.is_development else None,
            "health": "/api/v1/health",
        }

    # ── Routers ───────────────────────────────────────────────────
    prefix = settings.api_prefix
    app.include_router(health.router, prefix=prefix, tags=["Health"])
    app.include_router(auth.router, prefix=f"{prefix}/auth", tags=["Auth"])
    app.include_router(files.router, prefix=f"{prefix}/files", tags=["Files"])
    app.include_router(datasets.router, prefix=f"{prefix}/datasets", tags=["Datasets"])
    app.include_router(queries.router, prefix=f"{prefix}/queries", tags=["Queries"])
    app.include_router(
        visualizations.router,
        prefix=f"{prefix}/visualizations",
        tags=["Visualizations"],
    )
    app.include_router(reports.router, prefix=f"{prefix}/reports", tags=["Reports"])
    app.include_router(insights.router, prefix=f"{prefix}/insights", tags=["Insights"])

    return app


app = create_app()
