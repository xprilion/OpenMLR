"""Tests for ToolRouter — registration, dispatch, mode filtering."""

import pytest

from openmlr.tools.registry import MODE_TOOL_RESTRICTIONS, ToolRouter

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
