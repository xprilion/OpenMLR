"""Database engine and async session factory with high-concurrency connection pooling."""

from __future__ import annotations

import logging
import os
import time
from contextvars import ContextVar
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

load_dotenv()

log = logging.getLogger(__name__)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/openmlr",
)

# Ensure the URL uses the asyncpg driver for PostgreSQL and clean sslmode query param
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Configurable Pool Parameters
DEFAULT_POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", "30"))
DEFAULT_MAX_OVERFLOW = int(os.environ.get("DB_MAX_OVERFLOW", "20"))
DEFAULT_POOL_RECYCLE = int(os.environ.get("DB_POOL_RECYCLE", "1800"))
DEFAULT_POOL_TIMEOUT = int(os.environ.get("DB_POOL_TIMEOUT", "30"))
DEFAULT_POOL_PRE_PING = os.environ.get("DB_POOL_PRE_PING", "true").lower() in ("true", "1", "yes")
DEFAULT_STATEMENT_CACHE_SIZE = int(os.environ.get("DB_STATEMENT_CACHE_SIZE", "1200"))
DEFAULT_ECHO = os.environ.get("DB_ECHO", "false").lower() in ("true", "1", "yes")


def create_database_engine(
    url: str | None = None,
    is_worker: bool = False,
    pool_size: int | None = None,
    max_overflow: int | None = None,
    echo: bool | None = None,
) -> AsyncEngine:
    """Create a configured async SQLAlchemy engine with connection pooling and query caching."""
    db_url = url or DATABASE_URL

    is_sqlite = db_url.startswith("sqlite")
    engine_echo = DEFAULT_ECHO if echo is None else echo

    if is_sqlite:
        return create_async_engine(
            db_url,
            echo=engine_echo,
            query_cache_size=DEFAULT_STATEMENT_CACHE_SIZE,
        )

    # High-concurrency pooling for PostgreSQL / asyncpg
    p_size = (pool_size or 5) if is_worker else (pool_size or DEFAULT_POOL_SIZE)
    m_overflow = (max_overflow or 10) if is_worker else (max_overflow or DEFAULT_MAX_OVERFLOW)

    connect_args: dict[str, Any] = {}
    if "asyncpg" in db_url:
        connect_args["statement_cache_size"] = DEFAULT_STATEMENT_CACHE_SIZE
        # Parse and sanitize query string if sslmode or other incompatible query args are present
        parsed = urlparse(db_url)
        if parsed.query:
            params = parse_qs(parsed.query)
            ssl_val = params.pop("sslmode", [None])[0] or params.pop("ssl", [None])[0]
            if ssl_val and ssl_val.lower() in ("require", "verify-ca", "verify-full", "true", "1"):
                connect_args["ssl"] = True
            elif ssl_val and ssl_val.lower() in ("disable", "false", "0"):
                connect_args["ssl"] = False
            new_query = urlencode({k: v[0] for k, v in params.items()})
            db_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment,
            ))

    return create_async_engine(
        db_url,
        echo=engine_echo,
        pool_size=p_size,
        max_overflow=m_overflow,
        pool_recycle=DEFAULT_POOL_RECYCLE,
        pool_timeout=DEFAULT_POOL_TIMEOUT,
        pool_pre_ping=DEFAULT_POOL_PRE_PING,
        query_cache_size=DEFAULT_STATEMENT_CACHE_SIZE,
        connect_args=connect_args,
    )


# Main engine for FastAPI (shared across requests)
engine: AsyncEngine = create_database_engine()

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Context variable for worker-specific engines
_worker_engine: ContextVar = ContextVar("worker_engine", default=None)


def get_worker_session() -> async_sessionmaker:
    """Get or create an engine/session factory for the current worker context.

    This ensures Celery workers get their own engine instance to avoid
    conflicts with asyncpg connection pool across event loops.
    """
    eng = _worker_engine.get()
    if eng is None:
        eng = create_database_engine(is_worker=True)
        _worker_engine.set(eng)
    return async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    """FastAPI dependency: yields an async database session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


def get_async_session():
    """Get an async session as a context manager (for non-dependency use like WebSockets)."""
    return async_session()


def get_db_pool_status() -> dict[str, Any]:
    """Retrieve runtime database connection pool metrics."""
    pool = getattr(engine, "pool", None)
    if pool is None:
        return {"status": "no_pool", "pool_size": 0, "checked_out": 0, "overflow": 0}

    checked_in = getattr(pool, "checkedin", lambda: 0)()
    checked_out = getattr(pool, "checkedout", lambda: 0)()
    overflow = getattr(pool, "overflow", lambda: 0)()
    size = getattr(pool, "size", lambda: 0)()

    return {
        "status": "active",
        "pool_size": size,
        "checked_in": checked_in,
        "checked_out": checked_out,
        "overflow": overflow,
        "total_connections": checked_in + checked_out,
    }


async def check_db_health(session: AsyncSession | None = None) -> dict[str, Any]:
    """Perform a ping query on the database and measure latency in milliseconds."""
    start_time = time.perf_counter()
    driver = "sqlite" if DATABASE_URL.startswith("sqlite") else "postgresql"

    try:
        if session:
            await session.execute(text("SELECT 1"))
        else:
            async with async_session() as s:
                await s.execute(text("SELECT 1"))

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "status": "healthy",
            "latency_ms": elapsed_ms,
            "driver": driver,
            "pool": get_db_pool_status(),
        }
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        log.error("Database health check failed: %s", exc)
        return {
            "status": "unhealthy",
            "latency_ms": elapsed_ms,
            "driver": driver,
            "error": str(exc),
        }
