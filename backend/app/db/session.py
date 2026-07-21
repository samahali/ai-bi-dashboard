"""
SQLAlchemy async session factory.
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.db.models import Base

# Use asyncpg driver for async PostgreSQL support
_async_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(
    _async_url,
    echo=settings.debug,
    pool_pre_ping=True,
    # Use NullPool in test mode to avoid connection leaks between tests
    poolclass=NullPool if settings.app_env == "test" else None,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def create_tables() -> None:
    """
    Create all tables directly from the ORM metadata.

    Dev/test convenience only — skips the Alembic revision history entirely,
    so it must never run in production (that's what `alembic upgrade head`
    is for; see docs/DEVELOPMENT.md and docs/DEPLOYMENT.md). Callers should
    gate this on settings.is_development / app_env == "test".
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """
    FastAPI dependency that yields a database session per request.
    Always closes the session after the request completes.
    """
    async with AsyncSessionLocal() as session:
        yield session
