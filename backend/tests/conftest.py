"""Shared pytest fixtures for the OpenMLR backend test suite.

Uses an async in-memory SQLite database (via aiosqlite) so tests run fast
and without requiring a running PostgreSQL instance.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio

import asyncio
from typing import AsyncGenerator

import httpx
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from openmlr.db.models import Base, User, ResearchCorpus
from openmlr.auth.security import hash_password, create_access_token

# ---------------------------------------------------------------------------
# SQLite compatibility: replace PostgreSQL-only ARRAY column with JSON
# ---------------------------------------------------------------------------
from sqlalchemy import JSON as _JSON

ResearchCorpus.__table__.c.tags.type = _JSON()

# ---------------------------------------------------------------------------
# Test database engine (SQLite async via aiosqlite)
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite://"  # in-memory

_test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    # SQLite does not support pool_size / max_overflow; use defaults
)

_TestSessionLocal = async_sessionmaker(
    _test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def _setup_db():
    """Create all tables before each test and drop them after.

    This guarantees a clean database for every test function.
    """
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency override that yields a test SQLite session."""
    async with _TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@pytest_asyncio.fixture()
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a raw async SQLite session for direct ORM usage in tests."""
    async with _TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture()
async def client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Unauthenticated ``httpx.AsyncClient`` wired to the FastAPI test app.

    The ``get_db`` dependency is overridden so all requests hit the test
    SQLite database instead of PostgreSQL.  The app lifespan is deliberately
    *not* invoked (no Redis, no production engine) to keep tests lightweight.
    """
    # Import lazily so module-level side-effects (engine creation, dotenv)
    # don't interfere before we apply the override.
    from openmlr.app import app
    from openmlr.db.engine import get_db as engine_get_db
    from openmlr.dependencies import get_db as dep_get_db

    # Override both the canonical get_db *and* the re-export in dependencies
    app.dependency_overrides[engine_get_db] = _override_get_db
    app.dependency_overrides[dep_get_db] = _override_get_db

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def test_user(db_session: AsyncSession) -> User:
    """Insert a test user into the database and return the ORM instance."""
    user = User(
        username="testuser",
        display_name="Test User",
        password_hash=hash_password("testpassword123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture()
async def test_user_token(test_user: User) -> str:
    """Return a valid JWT access token for ``test_user``."""
    return create_access_token(test_user.id, test_user.username)


@pytest_asyncio.fixture()
async def auth_client(
    client: httpx.AsyncClient,
    test_user_token: str,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """``httpx.AsyncClient`` with a valid JWT ``Authorization`` header.

    This fixture composes ``client`` + ``test_user_token`` so every request
    is automatically authenticated as the test user.
    """
    client.headers["Authorization"] = f"Bearer {test_user_token}"
    yield client
