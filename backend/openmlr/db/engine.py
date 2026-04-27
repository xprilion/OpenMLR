"""Database engine and async session factory."""

import os
from contextvars import ContextVar

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

load_dotenv()

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/openmlr",
)

# Ensure the URL uses the asyncpg driver
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Main engine for FastAPI (shared across requests)
engine = create_async_engine(DATABASE_URL, echo=False, pool_size=10, max_overflow=20)

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
        # Create a new engine for this worker context
        eng = create_async_engine(
            DATABASE_URL,
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,  # Verify connections before use
        )
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
