"""Tests for research tool — tool specs and the research sub-agent dispatching."""

import pytest
from openmlr.tools.research import (
    create_research_tool, _get_research_tool_specs, _execute_research_tool,
    RESEARCH_SYSTEM_PROMPT, MAX_RESEARCH_ITERATIONS,
)
from openmlr.agent.types import ToolCall


class TestCreateResearchTool:
    def test_creates_tool(self):
        tool = create_research_tool()
        assert tool.name == "research"
        assert tool.handler is not None
        assert "query" in tool.parameters["required"]

    def test_focus_enum(self):
        tool = create_research_tool()
        focus = tool.parameters["properties"]["focus"]
        assert focus["enum"] == ["papers", "code", "docs", "general"]


class TestGetResearchToolSpecs:
    def test_returns_formatted_tools(self):
        specs = _get_research_tool_specs()
        assert len(specs) > 0
        for spec in specs:
            assert spec["type"] == "function"
            assert "function" in spec
            assert "name" in spec["function"]

    def test_includes_search(self):
        specs = _get_research_tool_specs()
        names = [s["function"]["name"] for s in specs]
        assert "web_search" in names

    def test_includes_papers(self):
        specs = _get_research_tool_specs()
        names = [s["function"]["name"] for s in specs]
        assert "papers" in names

    def test_github_read_included(self):
        specs = _get_research_tool_specs()
        names = [s["function"]["name"] for s in specs]
        assert "github_read_file" in names or "github_find_examples" in names


class TestExecuteResearchTool:
    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        tc = ToolCall(id="tc1", name="unknown_tool", arguments={})
        result, success = await _execute_research_tool(tc)
        assert success is False
        assert "not available" in result

    def test_system_prompt_not_empty(self):
        assert len(RESEARCH_SYSTEM_PROMPT) > 0
        assert "research sub-agent" in RESEARCH_SYSTEM_PROMPT.lower()

    def test_max_iterations(self):
        assert MAX_RESEARCH_ITERATIONS == 60
