"""Tests for database engine factory, connection pooling, and health checks."""

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from openmlr.db.engine import (
    DATABASE_URL,
    _worker_engine,
    async_session,
    check_db_health,
    create_database_engine,
    engine,
    get_async_session,
    get_db,
    get_db_pool_status,
    get_worker_session,
)


class TestEngineConfig:
    def test_database_url_exists(self):
        assert DATABASE_URL is not None
        assert len(DATABASE_URL) > 0

    def test_engine_created(self):
        assert engine is not None
        assert isinstance(engine, AsyncEngine)

    def test_async_session_created(self):
        assert async_session is not None
        assert isinstance(async_session, async_sessionmaker)

    def test_create_database_engine_custom_sqlite(self):
        eng = create_database_engine("sqlite+aiosqlite:///:memory:")
        assert isinstance(eng, AsyncEngine)

    def test_create_database_engine_worker_mode(self):
        eng = create_database_engine("postgresql+asyncpg://localhost:5432/testdb", is_worker=True)
        assert isinstance(eng, AsyncEngine)

    def test_pool_status_structure(self):
        status = get_db_pool_status()
        assert isinstance(status, dict)
        assert "status" in status
        assert "pool_size" in status

    def test_worker_engine_context_var(self):
        from contextvars import ContextVar

        assert isinstance(_worker_engine, ContextVar)


@pytest.mark.asyncio
class TestGetWorkerSession:
    async def test_returns_sessionmaker(self):
        result = get_worker_session()
        assert isinstance(result, async_sessionmaker)


@pytest.mark.asyncio
class TestGetDB:
    async def test_yields_session(self):
        sessions = []
        async for s in get_db():
            sessions.append(s)
            break
        assert len(sessions) == 1

    async def test_get_async_session_context(self):
        sess = get_async_session()
        assert isinstance(sess, AsyncSession)
        await sess.close()


@pytest.mark.asyncio
class TestCheckDbHealth:
    async def test_health_check_returns_status(self, db_session: AsyncSession):
        res = await check_db_health(session=db_session)
        assert isinstance(res, dict)
        assert res["status"] == "healthy"
        assert "latency_ms" in res
        assert res["latency_ms"] >= 0.0
