"""Tests for FastAPI dependencies — get_config, get_current_user."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestGetConfig:
    async def test_get_config_returns_agent_config(self):
        from openmlr.dependencies import get_config

        config = get_config()
        assert config is not None
        assert hasattr(config, "model_name")
        assert hasattr(config, "max_iterations")

    async def test_get_config_is_cached(self):
        from openmlr.dependencies import get_config

        config1 = get_config()
        config2 = get_config()
        assert config1 is config2


class TestGetCurrentUser:
    async def test_valid_token_returns_user(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "testuser"

    async def test_no_token_returns_401(self, client: AsyncClient):
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 401

    async def test_invalid_token_returns_401(self, client: AsyncClient):
        client.headers["Authorization"] = "Bearer invalid.token.here"
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 401


class TestGetDB:
    async def test_db_session_yielded(self, client: AsyncClient):
        from openmlr.dependencies import get_db

        sessions = []
        async for s in get_db():
            sessions.append(s)
            break
        assert len(sessions) == 1
