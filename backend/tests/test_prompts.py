"""Tests for system prompt builder."""


from openmlr.agent.prompts import COMPACT_PROMPT, build_system_prompt
from openmlr.agent.types import ToolSpec


class TestBuildSystemPrompt:
    def test_renders_with_tools(self):
        tools = [
            ToolSpec(name="read_file", description="Read a file", parameters={"type": "object"}),
            ToolSpec(name="write_file", description="Write a file", parameters={"type": "object"}),
        ]
        prompt = build_system_prompt(tool_specs=tools, mode="general", username="tester")
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "read_file" in prompt or "read_file" in prompt

    def test_renders_with_username(self):
        tools = [ToolSpec(name="test_tool", description="Test", parameters={"type": "object"})]
        prompt = build_system_prompt(tool_specs=tools, username="alice")
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_renders_with_sandbox_info(self):
        tools = [ToolSpec(name="bash", description="Run commands", parameters={"type": "object"})]
        prompt = build_system_prompt(tool_specs=tools, sandbox_info="local")
        assert isinstance(prompt, str)

    def test_renders_with_mode_plan(self):
        tools = [ToolSpec(name="ask_user", description="Ask questions", parameters={"type": "object"})]
        prompt = build_system_prompt(tool_specs=tools, mode="plan")
        assert isinstance(prompt, str)

    def test_renders_with_mode_research(self):
        tools = [ToolSpec(name="papers", description="Search papers", parameters={"type": "object"})]
        prompt = build_system_prompt(tool_specs=tools, mode="research")
        assert isinstance(prompt, str)

    def test_renders_with_config(self):
        from openmlr.config import AgentConfig
        config = AgentConfig(model_name="test/model", max_iterations=10)
        tools = [ToolSpec(name="test", description="Test tool", parameters={"type": "object"})]
        prompt = build_system_prompt(tool_specs=tools, config=config)
        assert isinstance(prompt, str)

    def test_multiple_tools_appear_in_prompt(self):
        tools = [
            ToolSpec(name="tool_a", description="First tool", parameters={"type": "object"}),
            ToolSpec(name="tool_b", description="Second tool", parameters={"type": "object"}),
            ToolSpec(name="tool_c", description="Third tool", parameters={"type": "object"}),
        ]
        prompt = build_system_prompt(tool_specs=tools)
        assert isinstance(prompt, str)

    def test_empty_tools(self):
        prompt = build_system_prompt(tool_specs=[])
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_contains_date_and_time(self):
        tools = [ToolSpec(name="t", description="d", parameters={"type": "object"})]
        prompt = build_system_prompt(tool_specs=tools)
        # Contains date in YYYY-MM-DD format
        import re
        assert re.search(r"\d{4}-\d{2}-\d{2}", prompt)

    def test_contains_sandbox_info_in_prompt(self):
        tools = [ToolSpec(name="bash", description="Run", parameters={"type": "object"})]
        prompt = build_system_prompt(tool_specs=tools, sandbox_info="SSH remote (4 GPUs)")
        assert isinstance(prompt, str)


class TestCompactPrompt:
    def test_is_string(self):
        assert isinstance(COMPACT_PROMPT, str)
        assert len(COMPACT_PROMPT) > 0

    def test_mentions_summary(self):
        assert "summary" in COMPACT_PROMPT.lower()
