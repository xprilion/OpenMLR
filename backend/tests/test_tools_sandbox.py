"""Tests for sandbox tools — probe, create, exec, read, write."""

import pytest

from openmlr.tools.sandbox_tools import _handle_probe, create_sandbox_tools

pytestmark = pytest.mark.asyncio
from openmlr.sandbox.manager import SandboxManager


class TestCreateSandboxTools:
    async def test_creates_all_tools(self):
        mgr = SandboxManager()
        tools = create_sandbox_tools(mgr)
        names = [t.name for t in tools]
        assert "sandbox_probe" in names
        assert "sandbox_create" in names
        assert "sandbox_exec" in names
        assert "sandbox_read" in names
        assert "sandbox_write" in names
        assert len(tools) == 5

    async def test_sandbox_create_needs_approval(self):
        mgr = SandboxManager()
        tools = create_sandbox_tools(mgr)
        create = [t for t in tools if t.name == "sandbox_create"][0]
        assert create.needs_approval is not None
        assert create.needs_approval({"provider": "modal"}) is True

    async def test_sandbox_exec_requires_command(self):
        mgr = SandboxManager()
        tools = create_sandbox_tools(mgr)
        exec_tool = [t for t in tools if t.name == "sandbox_exec"][0]
        assert "command" in exec_tool.parameters["required"]

    async def test_sandbox_probe_no_params(self):
        mgr = SandboxManager()
        tools = create_sandbox_tools(mgr)
        probe = [t for t in tools if t.name == "sandbox_probe"][0]
        assert probe.parameters["properties"] == {}

    async def test_sandbox_create_provider_enum(self):
        mgr = SandboxManager()
        tools = create_sandbox_tools(mgr)
        create = [t for t in tools if t.name == "sandbox_create"][0]
        providers = create.parameters["properties"]["provider"]["enum"]
        assert "local" in providers
        assert "ssh" in providers
        assert "modal" in providers


class TestHandleProbe:
    async def test_probe_without_sandbox(self):
        mgr = SandboxManager()
        result, success = await _handle_probe(mgr)
        assert success is True
        assert "Using local environment" in result or "OS:" in result

    async def test_probe_with_local_sandbox(self):
        mgr = SandboxManager()
        await mgr.create("local")
        result, success = await _handle_probe(mgr)
        assert success is True
        assert "Sandbox Environment" in result
        await mgr.destroy()
