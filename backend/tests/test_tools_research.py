"""Tests for research tool — tool specs and the research sub-agent dispatching."""

import pytest

from openmlr.agent.types import ToolCall
from openmlr.tools.research import (
    MAX_RESEARCH_ITERATIONS,
    RESEARCH_SYSTEM_PROMPT,
    _execute_research_tool,
    _get_research_tool_specs,
    create_research_tool,
)


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

    def test_hf_tools_included(self):
        specs = _get_research_tool_specs()
        names = [s["function"]["name"] for s in specs]
        assert "hf_search_models" in names
        assert "hf_read_file" in names

    def test_hf_tools_limited_to_subset(self):
        """Only hf_search_models and hf_read_file should be in research, not all 5."""
        specs = _get_research_tool_specs()
        hf_names = [s["function"]["name"] for s in specs if s["function"]["name"].startswith("hf_")]
        assert set(hf_names) == {"hf_search_models", "hf_read_file"}


class TestExecuteResearchTool:
    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        tc = ToolCall(id="tc1", name="unknown_tool", arguments={})
        result, success = await _execute_research_tool(tc)
        assert success is False
        assert "not available" in result

    @pytest.mark.asyncio
    async def test_hf_search_models_dispatches(self):
        """Verify hf_search_models is a recognized tool in the research dispatcher."""
        from unittest.mock import AsyncMock, patch

        tc = ToolCall(id="tc2", name="hf_search_models", arguments={"query": "test"})
        # Patch the source handler (imported inside _execute_research_tool at call time)
        with patch(
            "openmlr.tools.huggingface._handle_search_models",
            new_callable=AsyncMock,
            return_value=("mocked result", True),
        ):
            result, success = await _execute_research_tool(tc)
            assert success is True
            assert result == "mocked result"

    @pytest.mark.asyncio
    async def test_hf_read_file_dispatches(self):
        """Verify hf_read_file is a recognized tool in the research dispatcher."""
        tc = ToolCall(
            id="tc3", name="hf_read_file", arguments={"repo_id": "test/repo", "path": "config.json"}
        )
        # This will try to actually call the handler which will fail network-wise,
        # but it should NOT return "not available"
        result, _ = await _execute_research_tool(tc)
        assert "not available" not in result

    def test_system_prompt_not_empty(self):
        assert len(RESEARCH_SYSTEM_PROMPT) > 0
        assert "research sub-agent" in RESEARCH_SYSTEM_PROMPT.lower()

    def test_max_iterations(self):
        assert MAX_RESEARCH_ITERATIONS == 60
