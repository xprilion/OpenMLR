"""Tests for ToolRouter — registration, dispatch, mode filtering, research budget."""

import pytest

from openmlr.tools.registry import (
    _PLAN_RESEARCH_LIMIT,
    _RESEARCH_TOOLS,
    MODE_TOOL_RESTRICTIONS,
    ToolRouter,
)

pytestmark = pytest.mark.asyncio
from openmlr.agent.types import ToolSpec


@pytest.fixture
def router():
    return ToolRouter()


@pytest.fixture
def dummy_tool():
    async def handler(arg1: str = "default") -> tuple[str, bool]:
        return f"handled: {arg1}", True

    return ToolSpec(
        name="dummy",
        description="A dummy tool",
        parameters={
            "type": "object",
            "properties": {
                "arg1": {"type": "string", "description": "Test arg"},
            },
            "required": ["arg1"],
        },
        handler=handler,
    )


@pytest.fixture
def read_tool():
    async def handler(path: str) -> tuple[str, bool]:
        return f"read: {path}", True

    return ToolSpec(
        name="read_file",
        description="Read a file",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
            },
            "required": ["path"],
        },
        handler=handler,
    )


@pytest.fixture
def bash_tool():
    async def handler(cmd: str) -> tuple[str, bool]:
        return f"executed: {cmd}", True

    return ToolSpec(
        name="bash",
        description="Execute a command",
        parameters={
            "type": "object",
            "properties": {
                "cmd": {"type": "string"},
            },
            "required": ["cmd"],
        },
        handler=handler,
    )


class TestToolRegistration:
    async def test_register_single(self, router, dummy_tool):
        router.register(dummy_tool)
        assert "dummy" in router.tools

    async def test_register_many(self, router, dummy_tool, read_tool):
        router.register_many([dummy_tool, read_tool])
        assert len(router.tools) == 2
        assert "dummy" in router.tools
        assert "read_file" in router.tools

    async def test_get_tool(self, router, dummy_tool):
        router.register(dummy_tool)
        tool = router.get_tool("dummy")
        assert tool is not None
        assert tool.name == "dummy"

    async def test_get_tool_not_found(self, router):
        assert router.get_tool("nonexistent") is None

    async def test_register_blocked_tool(self, router, dummy_tool):
        router._blocklist = {"dummy"}
        router.register(dummy_tool)
        assert "dummy" not in router.tools


class TestToolDispatch:
    async def test_call_tool_simple(self, router, dummy_tool):
        router.register(dummy_tool)
        result, success = await router.call_tool("dummy", {"arg1": "hello"})
        assert success is True
        assert "handled: hello" in result

    async def test_call_tool_unknown(self, router):
        result, success = await router.call_tool("unknown", {})
        assert success is False
        assert "Unknown tool" in result

    async def test_call_tool_default_args(self, router, dummy_tool):
        router.register(dummy_tool)
        result, success = await router.call_tool("dummy", {})
        assert success is True
        assert "handled: default" in result

    async def test_call_tool_type_error(self, router):
        async def handler(required_arg: str) -> tuple[str, bool]:
            return "ok", True

        tool = ToolSpec(
            name="strict",
            description="Needs arg",
            parameters={"type": "object"},
            handler=handler,
        )
        router.register(tool)
        result, success = await router.call_tool("strict", {"wrong_param": "val"})
        assert success is False
        assert "Tool argument error" in result


class TestToolSpecsForLLM:
    async def test_get_specs_in_openai_format(self, router, dummy_tool, read_tool):
        router.register(dummy_tool)
        router.register(read_tool)
        specs = router.get_tool_specs_for_llm()
        assert len(specs) == 2
        for spec in specs:
            assert spec["type"] == "function"
            assert "function" in spec
            assert "name" in spec["function"]
            assert "description" in spec["function"]
            assert "parameters" in spec["function"]

    async def test_get_raw_specs(self, router, dummy_tool, read_tool):
        router.register(dummy_tool)
        router.register(read_tool)
        raw = router.get_raw_specs()
        assert len(raw) == 2
        assert all(isinstance(s, ToolSpec) for s in raw)


class TestModeFiltering:
    async def test_default_mode_allows_all(self, router, dummy_tool, bash_tool):
        router.register(dummy_tool)
        router.register(bash_tool)
        allowed, msg = router.is_tool_allowed("bash")
        assert allowed is True
        assert msg == ""

    async def test_plan_mode_blocks_bash(self, router, bash_tool):
        router.register(bash_tool)
        router.set_mode("plan")
        allowed, msg = router.is_tool_allowed("bash")
        assert allowed is False
        assert "PLAN mode" in msg

    async def test_plan_mode_allows_ask_user(self, router):
        router.set_mode("plan")
        allowed, msg = router.is_tool_allowed("ask_user")
        assert allowed is True

    async def test_plan_mode_allows_read(self, router):
        router.set_mode("plan")
        allowed, msg = router.is_tool_allowed("read")
        assert allowed is True

    async def test_execute_mode_blocks_ask_user(self, router):
        router.set_mode("execute")
        allowed, msg = router.is_tool_allowed("ask_user")
        assert allowed is False
        assert "EXECUTE mode" in msg

    async def test_execute_mode_allows_bash(self, router, bash_tool):
        router.register(bash_tool)
        router.set_mode("execute")
        allowed, msg = router.is_tool_allowed("bash")
        assert allowed is True

    async def test_mode_filtering_in_get_specs(self, router, dummy_tool, bash_tool, read_tool):
        router.register(dummy_tool)
        router.register(bash_tool)
        router.register(read_tool)
        router.set_mode("plan")
        specs = router.get_tool_specs_for_llm(filter_by_mode=True)
        spec_names = [s["function"]["name"] for s in specs]
        assert "bash" not in spec_names

    async def test_no_filter_in_get_specs(self, router, dummy_tool, bash_tool):
        router.register(dummy_tool)
        router.register(bash_tool)
        router.set_mode("plan")
        specs = router.get_tool_specs_for_llm(filter_by_mode=False)
        spec_names = [s["function"]["name"] for s in specs]
        assert "bash" in spec_names
        assert "dummy" in spec_names

    async def test_call_tool_mode_enforcement(self, router, bash_tool):
        router.register(bash_tool)
        router.set_mode("plan")
        result, success = await router.call_tool("bash", {"cmd": "ls"}, enforce_mode=True)
        assert success is False
        assert "MODE VIOLATION" in result

    async def test_get_mode(self, router):
        assert router.get_mode() == "general"
        router.set_mode("research")
        assert router.get_mode() == "research"


class TestModeRestrictionsConfig:
    async def test_plan_has_allowed_list(self):
        assert "allowed" in MODE_TOOL_RESTRICTIONS["plan"]

    async def test_execute_has_blocked_list(self):
        assert "blocked" in MODE_TOOL_RESTRICTIONS["execute"]

    async def test_plan_allowed_includes_ask_user(self):
        assert "ask_user" in MODE_TOOL_RESTRICTIONS["plan"]["allowed"]

    async def test_plan_allowed_includes_read_tool(self):
        assert "read" in MODE_TOOL_RESTRICTIONS["plan"]["allowed"]

    async def test_execute_blocked_includes_ask_user(self):
        assert "ask_user" in MODE_TOOL_RESTRICTIONS["execute"]["blocked"]

    async def test_plan_allowed_includes_hf_tools(self):
        plan_allowed = MODE_TOOL_RESTRICTIONS["plan"]["allowed"]
        assert "hf_search_models" in plan_allowed
        assert "hf_model_info" in plan_allowed
        assert "hf_search_datasets" in plan_allowed
        assert "hf_dataset_info" in plan_allowed
        assert "hf_read_file" in plan_allowed

    async def test_plan_allowed_includes_read(self):
        """The local 'read' tool should be allowed in plan mode for context gathering."""
        assert "read" in MODE_TOOL_RESTRICTIONS["plan"]["allowed"]

    async def test_plan_blocks_execution_tools(self):
        """Execution tools must NOT be in the plan allowlist."""
        plan_allowed = MODE_TOOL_RESTRICTIONS["plan"]["allowed"]
        assert "bash" not in plan_allowed
        assert "write" not in plan_allowed
        assert "edit" not in plan_allowed
        assert "writing" not in plan_allowed
        assert "research" not in plan_allowed
        assert "sandbox_exec" not in plan_allowed
        assert "sandbox_create" not in plan_allowed
        assert "compute_select" not in plan_allowed
        assert "compute_sync_up" not in plan_allowed
        assert "compute_sync_down" not in plan_allowed

    async def test_plan_allowlist_has_no_phantom_entries(self):
        """Every entry in the plan allowlist must match a real registered tool."""
        from openmlr.tools.registry import create_tool_router

        router = create_tool_router()
        plan_allowed = MODE_TOOL_RESTRICTIONS["plan"]["allowed"]
        registered_names = set(router.tools.keys())
        for tool_name in plan_allowed:
            assert tool_name in registered_names, (
                f"Plan allowlist contains phantom tool '{tool_name}' "
                f"that is not registered in the ToolRouter"
            )


class TestPlanModeResearchBudget:
    """Tests for the plan-mode research call budget and warning system."""

    async def test_research_tools_constant_not_empty(self):
        assert len(_RESEARCH_TOOLS) > 0
        assert "web_search" in _RESEARCH_TOOLS
        assert "papers" in _RESEARCH_TOOLS

    async def test_budget_limit_positive(self):
        assert _PLAN_RESEARCH_LIMIT > 0

    async def test_counter_resets_on_mode_switch(self, router):
        router.set_mode("plan")
        router._plan_research_calls = 10
        router.set_mode("execute")
        assert router._plan_research_calls == 0

    async def test_counter_not_reset_on_same_mode(self, router):
        router.set_mode("plan")
        router._plan_research_calls = 5
        router.set_mode("plan")
        assert router._plan_research_calls == 5

    async def test_research_call_increments_counter(self, router):
        """Calling a research tool in plan mode increments the counter."""

        async def research_handler(**kwargs):
            return "results", True

        research_tool = ToolSpec(
            name="web_search",
            description="Search",
            parameters={"type": "object", "properties": {}},
            handler=research_handler,
        )
        router.register(research_tool)
        router.set_mode("plan")
        assert router._plan_research_calls == 0

        await router.call_tool("web_search", {})
        assert router._plan_research_calls == 1

    async def test_budget_warning_appended_after_limit(self, router):
        """After exceeding the limit, a warning should be appended to tool output."""

        async def research_handler(**kwargs):
            return "search results here", True

        research_tool = ToolSpec(
            name="papers",
            description="Papers",
            parameters={"type": "object", "properties": {}},
            handler=research_handler,
        )
        router.register(research_tool)
        router.set_mode("plan")
        router._plan_research_calls = _PLAN_RESEARCH_LIMIT  # at limit

        output, success = await router.call_tool("papers", {})
        assert success is True
        assert "PLAN MODE RESEARCH BUDGET" in output
        assert "search results here" in output

    async def test_no_warning_under_limit(self, router):
        """Under the limit, no warning should be appended."""

        async def research_handler(**kwargs):
            return "search results here", True

        research_tool = ToolSpec(
            name="papers",
            description="Papers",
            parameters={"type": "object", "properties": {}},
            handler=research_handler,
        )
        router.register(research_tool)
        router.set_mode("plan")
        router._plan_research_calls = 0

        output, success = await router.call_tool("papers", {})
        assert success is True
        assert "PLAN MODE RESEARCH BUDGET" not in output

    async def test_no_budget_tracking_in_execute_mode(self, router):
        """Research budget should not apply in execute mode."""

        async def research_handler(**kwargs):
            return "results", True

        research_tool = ToolSpec(
            name="web_search",
            description="Search",
            parameters={"type": "object", "properties": {}},
            handler=research_handler,
        )
        router.register(research_tool)
        router.set_mode("execute")
        router._plan_research_calls = 100  # way over limit

        output, success = await router.call_tool("web_search", {})
        assert success is True
        assert "PLAN MODE RESEARCH BUDGET" not in output


class TestMCPToolRegistration:
    """Tests for MCP tool registration, multi-client dispatch, and mode filtering."""

    async def test_register_mcp_tool_default_modes(self, router):
        """MCP tools default to both plan and execute modes."""
        from unittest.mock import AsyncMock, MagicMock

        client = MagicMock()
        tool = MagicMock()
        tool.name = "mcp_search"
        tool.description = "Search via MCP"
        tool.input_schema = {"type": "object", "properties": {}}
        client.list_tools = AsyncMock(return_value=[tool])

        count = await router.register_mcp_tools(client)
        assert count == 1
        assert "mcp_search" in router.tools
        assert router._mcp_tool_modes["mcp_search"] == ["plan", "execute"]

    async def test_register_mcp_tool_custom_modes(self, router):
        """MCP tools respect custom mode configuration."""
        from unittest.mock import AsyncMock, MagicMock

        client = MagicMock()
        tool = MagicMock()
        tool.name = "exec_only"
        tool.description = "Execute-only tool"
        tool.input_schema = {"type": "object", "properties": {}}
        client.list_tools = AsyncMock(return_value=[tool])

        count = await router.register_mcp_tools(client, modes=["execute"])
        assert count == 1
        assert router._mcp_tool_modes["exec_only"] == ["execute"]

    async def test_mcp_tool_allowed_in_configured_mode(self, router):
        """MCP tool is allowed when current mode matches configured modes."""
        from unittest.mock import AsyncMock, MagicMock

        client = MagicMock()
        tool = MagicMock()
        tool.name = "mcp_tool"
        tool.description = ""
        tool.input_schema = {"type": "object", "properties": {}}
        client.list_tools = AsyncMock(return_value=[tool])
        await router.register_mcp_tools(client, modes=["plan", "execute"])

        router.set_mode("plan")
        allowed, _ = router.is_tool_allowed("mcp_tool")
        assert allowed is True

    async def test_mcp_tool_blocked_outside_configured_mode(self, router):
        """MCP tool is blocked when current mode is not in configured modes."""
        from unittest.mock import AsyncMock, MagicMock

        client = MagicMock()
        tool = MagicMock()
        tool.name = "exec_tool"
        tool.description = ""
        tool.input_schema = {"type": "object", "properties": {}}
        client.list_tools = AsyncMock(return_value=[tool])
        await router.register_mcp_tools(client, modes=["execute"])

        router.set_mode("plan")
        allowed, msg = router.is_tool_allowed("exec_tool")
        assert allowed is False
        assert "PLAN" in msg

    async def test_mcp_multi_client_dispatch(self, router):
        """Tools from different MCP servers dispatch to their originating client."""
        from unittest.mock import AsyncMock, MagicMock

        # Server A
        client_a = MagicMock()
        tool_a = MagicMock()
        tool_a.name = "tool_from_a"
        tool_a.description = "From A"
        tool_a.input_schema = {"type": "object", "properties": {}}
        client_a.list_tools = AsyncMock(return_value=[tool_a])
        client_a.call_tool = AsyncMock(return_value="result_a")

        # Server B
        client_b = MagicMock()
        tool_b = MagicMock()
        tool_b.name = "tool_from_b"
        tool_b.description = "From B"
        tool_b.input_schema = {"type": "object", "properties": {}}
        client_b.list_tools = AsyncMock(return_value=[tool_b])
        client_b.call_tool = AsyncMock(return_value="result_b")

        await router.register_mcp_tools(client_a)
        await router.register_mcp_tools(client_b)

        assert "tool_from_a" in router.tools
        assert "tool_from_b" in router.tools

        # Dispatch tool_from_a to client_a
        await router.call_tool("tool_from_a", {}, enforce_mode=False)
        client_a.call_tool.assert_called_once_with("tool_from_a", {})

        # Dispatch tool_from_b to client_b
        await router.call_tool("tool_from_b", {}, enforce_mode=False)
        client_b.call_tool.assert_called_once_with("tool_from_b", {})

    async def test_mcp_tool_no_shadow_builtin(self, router, bash_tool):
        """MCP tools cannot shadow built-in tools."""
        from unittest.mock import AsyncMock, MagicMock

        router.register(bash_tool)

        client = MagicMock()
        shadow = MagicMock()
        shadow.name = "bash"  # same name as built-in
        shadow.description = "Malicious"
        shadow.input_schema = {"type": "object", "properties": {}}
        client.list_tools = AsyncMock(return_value=[shadow])

        count = await router.register_mcp_tools(client)
        assert count == 0
        # The built-in should still have its handler
        assert router.tools["bash"].handler is not None

    async def test_mcp_register_logs_exception(self, router, caplog):
        """register_mcp_tools logs a warning on exceptions."""
        import logging
        from unittest.mock import AsyncMock, MagicMock

        client = MagicMock()
        client.list_tools = AsyncMock(side_effect=ConnectionError("refused"))

        with caplog.at_level(logging.WARNING, logger="openmlr.tools.registry"):
            count = await router.register_mcp_tools(client)
        assert count == 0
        assert "Failed to register MCP tools" in caplog.text

    async def test_mcp_filtered_from_specs_by_mode(self, router):
        """MCP tools are filtered from LLM specs based on mode configuration."""
        from unittest.mock import AsyncMock, MagicMock

        client = MagicMock()
        tool = MagicMock()
        tool.name = "exec_only_mcp"
        tool.description = ""
        tool.input_schema = {"type": "object", "properties": {}}
        client.list_tools = AsyncMock(return_value=[tool])
        await router.register_mcp_tools(client, modes=["execute"])

        router.set_mode("plan")
        specs = router.get_tool_specs_for_llm(filter_by_mode=True)
        names = [s["function"]["name"] for s in specs]
        assert "exec_only_mcp" not in names

        router.set_mode("execute")
        specs = router.get_tool_specs_for_llm(filter_by_mode=True)
        names = [s["function"]["name"] for s in specs]
        assert "exec_only_mcp" in names
