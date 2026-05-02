"""Tests for papers tool — helper functions and tool spec."""

import os
from unittest.mock import MagicMock, patch

import pytest

from openmlr.tools.papers import (
    _check_budget,
    _extract_arxiv_id,
    _get_budget_info,
    _get_paperclip_headers,
    _increment_budget,
    _paperclip_lookup,
    _paperclip_search,
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

    def test_paperclip_operations_in_enum(self):
        tool = create_papers_tool()
        ops = tool.parameters["properties"]["operation"]["enum"]
        assert "paperclip_search" in ops
        assert "paperclip_lookup" in ops

    def test_paperclip_source_parameter(self):
        tool = create_papers_tool()
        props = tool.parameters["properties"]
        assert "paperclip_source" in props
        assert "biorxiv" in props["paperclip_source"]["enum"]
        assert "medrxiv" in props["paperclip_source"]["enum"]
        assert "pmc" in props["paperclip_source"]["enum"]
        assert "all" in props["paperclip_source"]["enum"]


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


class TestPaperclipHeaders:
    def test_returns_none_without_key(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("PAPERCLIP_API_KEY", None)
            assert _get_paperclip_headers() is None

    def test_returns_headers_with_key(self):
        with patch.dict(os.environ, {"PAPERCLIP_API_KEY": "gxl_test123"}):
            headers = _get_paperclip_headers()
            assert headers is not None
            assert headers["X-API-Key"] == "gxl_test123"
            assert headers["Content-Type"] == "application/json"


class TestPaperclipSearch:
    async def test_no_query_returns_error(self):
        result, ok = await _paperclip_search("")
        assert ok is False
        assert "query" in result.lower()

    async def test_no_api_key_returns_error(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("PAPERCLIP_API_KEY", None)
            result, ok = await _paperclip_search("CRISPR")
            assert ok is False
            assert "PAPERCLIP_API_KEY" in result

    @patch("openmlr.tools.papers.fetch_with_retry")
    async def test_successful_search(self, mock_fetch):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "output": "  1. CRISPR gene editing in vivo\n     doi:10.1101/2024.01.01\n",
            "elapsed_ms": 150,
            "result_id": "s_abc123",
        }
        mock_fetch.return_value = mock_resp

        with patch.dict(os.environ, {"PAPERCLIP_API_KEY": "gxl_test123"}):
            result, ok = await _paperclip_search("CRISPR", limit=5)

        assert ok is True
        assert "Paperclip" in result
        assert "CRISPR" in result

        # Verify the API call
        mock_fetch.assert_called_once()
        call_kwargs = mock_fetch.call_args
        assert call_kwargs.kwargs["method"] == "POST"
        assert "/api/cli/execute" in call_kwargs.args[0]
        body = call_kwargs.kwargs["json"]
        assert body["command"] == "search"
        assert "-n 5" in body["raw"]

    @patch("openmlr.tools.papers.fetch_with_retry")
    async def test_search_with_source_filter(self, mock_fetch):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"output": "results", "elapsed_ms": 100}
        mock_fetch.return_value = mock_resp

        with patch.dict(os.environ, {"PAPERCLIP_API_KEY": "gxl_test123"}):
            await _paperclip_search("CRISPR", paperclip_source="pmc")

        body = mock_fetch.call_args.kwargs["json"]
        assert "--source pmc" in body["raw"]

    @patch("openmlr.tools.papers.fetch_with_retry")
    async def test_search_with_year_filter(self, mock_fetch):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"output": "results", "elapsed_ms": 100}
        mock_fetch.return_value = mock_resp

        with patch.dict(os.environ, {"PAPERCLIP_API_KEY": "gxl_test123"}):
            await _paperclip_search("CRISPR", year_from=2024)

        body = mock_fetch.call_args.kwargs["json"]
        assert "--year 2024" in body["raw"]

    @patch("openmlr.tools.papers.fetch_with_retry")
    async def test_auth_error(self, mock_fetch):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_fetch.return_value = mock_resp

        with patch.dict(os.environ, {"PAPERCLIP_API_KEY": "gxl_bad_key"}):
            result, ok = await _paperclip_search("CRISPR")

        assert ok is False
        assert "invalid" in result.lower() or "expired" in result.lower()


class TestPaperclipLookup:
    async def test_no_paper_id_returns_error(self):
        result, ok = await _paperclip_lookup("")
        assert ok is False
        assert "paper_id" in result.lower()

    async def test_no_api_key_returns_error(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("PAPERCLIP_API_KEY", None)
            result, ok = await _paperclip_lookup("10.1101/2024.01.01")
            assert ok is False
            assert "PAPERCLIP_API_KEY" in result

    @patch("openmlr.tools.papers.fetch_with_retry")
    async def test_doi_lookup(self, mock_fetch):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "output": "Title: CRISPR Paper\nDOI: 10.1101/2024.01.01\n",
        }
        mock_fetch.return_value = mock_resp

        with patch.dict(os.environ, {"PAPERCLIP_API_KEY": "gxl_test123"}):
            _, ok = await _paperclip_lookup("10.1101/2024.01.01")

        assert ok is True
        body = mock_fetch.call_args.kwargs["json"]
        assert body["command"] == "lookup"
        assert "doi" in body["raw"]

    @patch("openmlr.tools.papers.fetch_with_retry")
    async def test_pmid_lookup(self, mock_fetch):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"output": "Paper details"}
        mock_fetch.return_value = mock_resp

        with patch.dict(os.environ, {"PAPERCLIP_API_KEY": "gxl_test123"}):
            await _paperclip_lookup("12345678")

        body = mock_fetch.call_args.kwargs["json"]
        assert body["command"] == "lookup"
        assert "pmid" in body["raw"]
