"""Tests for papers tool — helper functions and tool spec."""

import pytest

from openmlr.tools.papers import (
    _check_budget,
    _extract_arxiv_id,
    _get_budget_info,
    _increment_budget,
    _reconstruct_abstract,
    _to_openalex_id,
    create_papers_tool,
)

pytestmark = pytest.mark.asyncio


class TestCreatePapersTool:
    async def test_creates_tool(self):
        tool = create_papers_tool()
        assert tool.name == "papers"
        assert tool.handler is not None
        assert "operation" in tool.parameters["required"]
        ops = tool.parameters["properties"]["operation"]["enum"]
        assert "search" in ops
        assert "trending" in ops
        assert "details" in ops
        assert "read_paper" in ops
        assert "citations" in ops
        assert "recommend" in ops
        assert "find_code" in ops
        assert "find_datasets" in ops


class TestExtractArxivId:
    async def test_standard_format(self):
        assert _extract_arxiv_id("2301.12345") == "2301.12345"

    async def test_with_version(self):
        assert _extract_arxiv_id("2301.12345v2") == "2301.12345v2"

    async def test_from_url(self):
        assert _extract_arxiv_id("https://arxiv.org/abs/2301.12345") == "2301.12345"

    async def test_from_pdf_url(self):
        assert _extract_arxiv_id("https://arxiv.org/pdf/2301.12345.pdf") == "2301.12345"

    async def test_no_arxiv_id(self):
        assert _extract_arxiv_id("some text without id") is None

    async def test_from_doi_with_arxiv(self):
        assert _extract_arxiv_id("10.48550/arXiv.2301.12345") == "2301.12345"


class TestToOpenAlexId:
    async def test_openalex_id(self):
        assert _to_openalex_id("W123456") == "W123456"

    async def test_openalex_url(self):
        assert _to_openalex_id("https://openalex.org/W123456") == "https://openalex.org/W123456"

    async def test_doi(self):
        assert _to_openalex_id("10.1234/foo.bar") == "https://doi.org/10.1234/foo.bar"

    async def test_arxiv_id(self):
        result = _to_openalex_id("2301.12345")
        assert "doi.org" in result
        assert "arXiv" in result


class TestReconstructAbstract:
    async def test_simple(self):
        inv = {"hello": [0], "world": [1]}
        assert _reconstruct_abstract(inv) == "hello world"

    async def test_empty(self):
        assert _reconstruct_abstract({}) is None
        assert _reconstruct_abstract(None) is None

    async def test_multiple_positions(self):
        inv = {"the": [0, 3], "cat": [1], "sat": [2], "mat": [4]}
        result = _reconstruct_abstract(inv)
        assert result == "the cat sat the mat"


class TestBudgetFunctions:
    async def test_check_budget_allows_first_call(self):
        ok, msg = _check_budget()
        assert ok is True
        assert msg == ""

    async def test_get_budget_info(self):
        info = _get_budget_info()
        assert "used" in info
        assert "max" in info

    async def test_increment_and_check(self):
        from openmlr.tools.papers import _search_counts

        _search_counts.clear()
        _increment_budget()
        info = _get_budget_info()
        assert info["used"] >= 1
        _search_counts.clear()
