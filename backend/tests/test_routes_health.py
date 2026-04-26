"""Tests for the health check endpoints."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestHealthEndpoints:
    async def test_api_health_returns_ok(self, client: AsyncClient):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "timestamp" in data
        assert isinstance(data["version"], str)

    async def test_health_returns_ok(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "timestamp" in data

    async def test_both_endpoints_return_same_structure(self, client: AsyncClient):
        resp1 = await client.get("/api/health")
        resp2 = await client.get("/health")
        assert resp1.json()["status"] == resp2.json()["status"]
        assert resp1.json()["version"] == resp2.json()["version"]

    async def test_health_not_require_auth(self, client: AsyncClient):
        resp = await client.get("/api/health")
        assert resp.status_code == 200

    async def test_health_timestamp_is_iso_format(self, client: AsyncClient):
        resp = await client.get("/health")
        data = resp.json()
        import re
        iso_pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
        assert re.search(iso_pattern, data["timestamp"])
