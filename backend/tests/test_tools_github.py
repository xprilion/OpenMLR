"""Tests for GitHub tools — tool specs and helper functions."""

import pytest
from openmlr.tools.github import create_github_tools, _headers

pytestmark = pytest.mark.asyncio


class TestCreateGithubTools:
    async def test_creates_all_tools(self):
        tools = create_github_tools()
        names = [t.name for t in tools]
        assert "github_read_file" in names
        assert "github_list_repos" in names
        assert "github_find_examples" in names
        assert len(tools) == 3

    async def test_read_file_required_params(self):
        tools = create_github_tools()
        read = [t for t in tools if t.name == "github_read_file"][0]
        required = read.parameters["required"]
        assert "owner" in required
        assert "repo" in required
        assert "path" in required

    async def test_list_repos_required_params(self):
        tools = create_github_tools()
        list_tool = [t for t in tools if t.name == "github_list_repos"][0]
        assert "owner" in list_tool.parameters["required"]

    async def test_find_examples_required_params(self):
        tools = create_github_tools()
        find = [t for t in tools if t.name == "github_find_examples"][0]
        assert "query" in find.parameters["required"]

    async def test_find_examples_language_filter(self):
        tools = create_github_tools()
        find = [t for t in tools if t.name == "github_find_examples"][0]
        assert "language" in find.parameters["properties"]


class TestHeaders:
    async def test_headers_accept(self):
        h = _headers()
        assert h["Accept"] == "application/vnd.github+json"

    async def test_headers_without_token(self, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        h = _headers()
        assert "Authorization" not in h

    async def test_headers_with_token(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test123")
        h = _headers()
        assert h["Authorization"] == "Bearer ghp_test123"
