"""Tests for MCP tools — env var substitution and config processing."""

import pytest
from openmlr.tools.mcp import substitute_env_vars, process_mcp_config

pytestmark = pytest.mark.asyncio


class TestSubstituteEnvVars:
    async def test_replaces_var(self, monkeypatch):
        monkeypatch.setenv("TEST_KEY", "test-value")
        result = substitute_env_vars("prefix-${TEST_KEY}-suffix")
        assert result == "prefix-test-value-suffix"

    async def test_multiple_vars(self, monkeypatch):
        monkeypatch.setenv("A", "aaa")
        monkeypatch.setenv("B", "bbb")
        result = substitute_env_vars("${A}_${B}")
        assert result == "aaa_bbb"

    async def test_unknown_var_unchanged(self, monkeypatch):
        monkeypatch.delenv("UNKNOWN_VAR", raising=False)
        result = substitute_env_vars("${UNKNOWN_VAR}")
        assert result == "${UNKNOWN_VAR}"

    async def test_no_vars(self):
        result = substitute_env_vars("plain text no vars")
        assert result == "plain text no vars"

    async def test_partial_match(self):
        result = substitute_env_vars("$TEST no match")
        assert result == "$TEST no match"


class TestProcessMCPConfig:
    async def test_simple_dict(self, monkeypatch):
        monkeypatch.setenv("API_KEY", "secret123")
        config = {"url": "https://api.example.com?key=${API_KEY}"}
        result = process_mcp_config(config)
        assert result["url"] == "https://api.example.com?key=secret123"

    async def test_nested_dict(self, monkeypatch):
        monkeypatch.setenv("HOST", "localhost")
        config = {"server": {"host": "${HOST}", "port": 8080}}
        result = process_mcp_config(config)
        assert result["server"]["host"] == "localhost"
        assert result["server"]["port"] == 8080

    async def test_list_values(self, monkeypatch):
        monkeypatch.setenv("ARG1", "value1")
        monkeypatch.setenv("ARG2", "value2")
        config = {"args": ["${ARG1}", "${ARG2}", "literal"]}
        result = process_mcp_config(config)
        assert result["args"] == ["value1", "value2", "literal"]

    async def test_non_string_values(self):
        config = {"timeout": 30, "enabled": True, "null_val": None}
        result = process_mcp_config(config)
        assert result["timeout"] == 30
        assert result["enabled"] is True
        assert result["null_val"] is None

    async def test_empty_config(self):
        assert process_mcp_config({}) == {}
