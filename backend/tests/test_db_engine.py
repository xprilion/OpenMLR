"""Tests for database engine factory and configuration."""

import pytest


class TestEngineConfig:
    def test_database_url_exists(self):
        from openmlr.db.engine import DATABASE_URL

        assert DATABASE_URL is not None
        assert len(DATABASE_URL) > 0

    def test_engine_created(self):
        from openmlr.db.engine import engine

        assert engine is not None

    def test_async_session_created(self):
        from openmlr.db.engine import async_session

        assert async_session is not None

    def test_worker_engine_context_var(self):
        from contextvars import ContextVar

        from openmlr.db.engine import _worker_engine

        assert isinstance(_worker_engine, ContextVar)


@pytest.mark.asyncio
class TestGetWorkerSession:
    async def test_returns_sessionmaker(self):
        from openmlr.db.engine import get_worker_session

        result = get_worker_session()
        from sqlalchemy.ext.asyncio import async_sessionmaker

        assert isinstance(result, async_sessionmaker)


@pytest.mark.asyncio
class TestGetDB:
    async def test_yields_session(self):
        from openmlr.db.engine import get_db

        sessions = []
        async for s in get_db():
            sessions.append(s)
            break
        assert len(sessions) == 1
