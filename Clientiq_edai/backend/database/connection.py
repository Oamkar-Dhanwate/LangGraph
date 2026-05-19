# Database connection
"""
ClientIQ — Database Connection Layer
Manages TiDB (MySQL-compatible) connections via SQLAlchemy async engine.
"""

import asyncio
import ssl
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from backend.utils.config import settings
from backend.utils.logger import logger


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Build async connection URL (aiomysql driver)
ASYNC_DB_URL = settings.tidb_url.replace("mysql+pymysql://", "mysql+aiomysql://")

connect_args = {}
if settings.tidb_ssl:
    connect_args["ssl"] = ssl.create_default_context()

# Create async engine
engine = create_async_engine(
    ASYNC_DB_URL,
    echo=settings.app_debug,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_recycle=3600,
    poolclass=NullPool if settings.app_env == "test" else None,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager that provides a database session with automatic
    commit on success and rollback on error.

    Usage:
        async with get_db_session() as db:
            result = await db.execute(...)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as exc:
            await session.rollback()
            logger.error("Database session error: {}", exc)
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a database session.

    Usage:
        @router.get("/")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with get_db_session() as session:
        yield session


async def check_db_connection() -> bool:
    """Health check: verify database connectivity."""
    from sqlalchemy import text
    try:
        async with get_db_session() as session:
            await session.execute(text("SELECT 1"))
        logger.info("TiDB connection verified ✓")
        return True
    except Exception as exc:
        logger.error("TiDB connection failed: {}", exc)
        return False
