"""Tests for web search tool — tool spec validation."""

import pytest

from openmlr.tools.search import create_search_tools

pytestmark = pytest.mark.asyncio


class TestCreateSearchTools:
    async def test_creates_tool(self):
        tools = create_search_tools()
        assert len(tools) == 1
        assert tools[0].name == "web_search"

    async def test_handler_configured(self):
        tools = create_search_tools()
        assert tools[0].handler is not None

    async def test_query_required(self):
        tools = create_search_tools()
        assert "query" in tools[0].parameters["required"]

    async def test_count_parameter(self):
        tools = create_search_tools()
        props = tools[0].parameters["properties"]
        assert "count" in props
        assert props["count"]["type"] == "integer"
