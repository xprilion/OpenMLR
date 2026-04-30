"""Tests for settings API routes."""

import os

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from openmlr.db import operations as ops


class TestAgentSettings:
    async def test_get_all_settings_empty(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert "settings" in data

    async def test_get_all_settings_after_set(
        self, auth_client: AsyncClient, db_session: AsyncSession, test_user
    ):
        await ops.set_user_setting(db_session, test_user.id, "agent", "default_model", "claude")
        resp = await auth_client.get("/api/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert "agent" in data["settings"]
        assert data["settings"]["agent"]["default_model"] == "claude"

    async def test_get_settings_category(
        self, auth_client: AsyncClient, db_session: AsyncSession, test_user
    ):
        await ops.set_user_setting(db_session, test_user.id, "agent", "yolo_mode", True)
        resp = await auth_client.get("/api/settings/agent")
        assert resp.status_code == 200
        data = resp.json()
        assert "settings" in data
        assert data["settings"]["yolo_mode"] is True

    async def test_update_setting(
        self, auth_client: AsyncClient, db_session: AsyncSession, test_user
    ):
        resp = await auth_client.put(
            "/api/settings/agent/test_key",
            json={"value": "test_value"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

    async def test_update_setting_missing_value(self, auth_client: AsyncClient):
        resp = await auth_client.put(
            "/api/settings/agent/test_key",
            json={},
        )
        assert resp.status_code == 400

    async def test_update_setting_with_dict(self, auth_client: AsyncClient):
        resp = await auth_client.put(
            "/api/settings/mcp/config",
            json={"value": {"server": "test", "port": 1234}},
        )
        assert resp.status_code == 200

    async def test_delete_setting(
        self, auth_client: AsyncClient, db_session: AsyncSession, test_user
    ):
        await ops.set_user_setting(db_session, test_user.id, "agent", "remove_me", "yes")
        resp = await auth_client.delete("/api/settings/agent/remove_me")
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

    async def test_update_provider_key_sets_env(
        self, auth_client: AsyncClient, db_session: AsyncSession, test_user
    ):
        resp = await auth_client.put(
            "/api/settings/providers/openai_api_key",
            json={"value": "sk-test-key"},
        )
        assert resp.status_code == 200
        assert os.environ["OPENAI_API_KEY"] == "sk-test-key"

    async def test_settings_require_auth(self, client: AsyncClient):
        resp = await client.get("/api/settings")
        assert resp.status_code == 401


class TestProviders:
    async def test_list_providers(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/providers")
        assert resp.status_code == 200
        data = resp.json()
        assert "providers" in data
        providers = data["providers"]
        assert isinstance(providers, list)
        assert len(providers) > 0
        provider_ids = [p["id"] for p in providers]
        assert "openai" in provider_ids
        assert "anthropic" in provider_ids
        assert "openrouter" in provider_ids

    async def test_provider_has_required_fields(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/providers")
        data = resp.json()
        for p in data["providers"]:
            assert "id" in p
            assert "name" in p
            assert "key_env" in p
            assert "configured" in p

    async def test_huggingface_provider_listed(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/providers")
        data = resp.json()
        provider_ids = [p["id"] for p in data["providers"]]
        assert "huggingface" in provider_ids

    async def test_huggingface_provider_fields(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/providers")
        data = resp.json()
        hf = [p for p in data["providers"] if p["id"] == "huggingface"][0]
        assert hf["name"] == "Hugging Face"
        assert hf["key_env"] == "HF_TOKEN"
        assert "models" in hf["categories"]
        assert "papers" in hf["categories"]
        assert "docs_url" in hf

    async def test_huggingface_token_sets_env(
        self, auth_client: AsyncClient, db_session, test_user
    ):
        resp = await auth_client.put(
            "/api/settings/providers/hf_token",
            json={"value": "hf_test_token_123"},
        )
        assert resp.status_code == 200
        assert os.environ.get("HF_TOKEN") == "hf_test_token_123"

    async def test_huggingface_token_in_config_allowlist(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/config",
            json={"HF_TOKEN": "hf_from_config"},
        )
        assert resp.status_code == 200
        assert os.environ.get("HF_TOKEN") == "hf_from_config"


class TestAppStatus:
    async def test_get_status(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "model" in data
        assert "research_model" in data
        assert "yolo_mode" in data
        assert "needs_onboarding" in data


class TestModels:
    async def test_list_models(self, auth_client: AsyncClient):
        # Configure a provider so models are returned
        await auth_client.put(
            "/api/settings/providers/openai_api_key",
            json={"value": "sk-test-key"},
        )
        resp = await auth_client.get("/api/models")
        assert resp.status_code == 200
        data = resp.json()
        assert "models" in data
        assert "recent_models" in data
        models = data["models"]
        assert isinstance(models, list)
        assert len(models) > 0

    async def test_models_have_required_fields(self, auth_client: AsyncClient):
        # Configure a provider so models are returned
        await auth_client.put(
            "/api/settings/providers/openai_api_key",
            json={"value": "sk-test-key"},
        )
        resp = await auth_client.get("/api/models")
        models = resp.json()["models"]
        for m in models:
            assert "id" in m
            assert "name" in m
            assert "provider" in m
            assert "release_date" in m


class TestConfigEndpoint:
    async def test_save_config(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/config",
            json={"OPENAI_API_KEY": "sk-from-config"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

    async def test_save_config_ignores_non_whitelisted(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/config",
            json={"RANDOM_KEY": "should-be-ignored"},
        )
        assert resp.status_code == 200
        assert "RANDOM_KEY" not in os.environ
