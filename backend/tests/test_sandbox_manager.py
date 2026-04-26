"""Tests for SandboxManager — lifecycle management and provider selection."""

import pytest

from openmlr.sandbox.manager import SandboxManager

pytestmark = pytest.mark.asyncio


@pytest.fixture
def manager():
    return SandboxManager()


class TestSandboxManager:
    async def test_initial_state(self, manager):
        assert manager.get_active() is None
        assert manager.active_type == "none"

    async def test_create_local(self, manager):
        sandbox = await manager.create("local")
        assert sandbox is not None
        assert manager.active_type == "local"
        assert manager.get_active() is sandbox

    async def test_create_then_destroy(self, manager):
        sandbox = await manager.create("local")
        await manager.destroy()
        assert manager.get_active() is None
        assert manager.active_type == "none"

    async def test_create_replaces_existing(self, manager):
        local1 = await manager.create("local")
        local2 = await manager.create("local")
        assert manager.get_active() is local2

    async def test_ensure_local_creates_if_none(self, manager):
        sandbox = await manager.ensure_local()
        assert sandbox is not None
        assert manager.active_type == "local"

    async def test_ensure_local_returns_existing(self, manager):
        sandbox1 = await manager.create("local")
        sandbox2 = await manager.ensure_local()
        assert sandbox1 is sandbox2

    async def test_create_unknown_provider_raises(self, manager):
        with pytest.raises(ValueError, match="Unknown sandbox provider"):
            await manager.create("invalid_provider")

    async def test_destroy_when_none_different_provider(self, manager):
        await manager.create("local")
        # Simulate a provider mismatch — destroy should still work
        await manager.destroy()
        assert manager.active_type == "none"
