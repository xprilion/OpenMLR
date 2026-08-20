"""Tests for paper search engine and multi-source academic providers."""

from unittest.mock import MagicMock, patch

import pytest

from openmlr.services.arxiv_client import extract_arxiv_id, find_section
from openmlr.services.paper_cache import paper_cache
from openmlr.services.paper_search_engine import get_crossref_details, search_papers_parallel


@pytest.mark.asyncio
class TestPaperSearchEngine:
    async def test_search_parallel_empty_query(self):
        res, ok = await search_papers_parallel("")
        assert ok is False
        assert "Provide a 'query'" in res

    @patch("openmlr.services.paper_search_engine.openalex_search")
    async def test_search_parallel_openalex_mode(self, mock_oa):
        mock_oa.return_value = ("Found 1 paper: Title", True)
        paper_cache.clear()

        res, ok = await search_papers_parallel("transformers", source="openalex")
        assert ok is True
        assert "Title" in res
        mock_oa.assert_called_once()

    @patch("openmlr.services.paper_search_engine.openalex_search")
    @patch("openmlr.services.paper_search_engine.semantic_scholar_search")
    async def test_search_parallel_auto_mode(self, mock_s2, mock_oa):
        mock_oa.return_value = ("Found OpenAlex paper", True)
        mock_s2.return_value = ("Found S2 paper", True)
        paper_cache.clear()

        res, ok = await search_papers_parallel("reinforcement learning", source="auto")
        assert ok is True
        assert "OpenAlex" in res

    @patch("openmlr.services.paper_search_engine.fetch_with_retry")
    async def test_crossref_details_success(self, mock_fetch):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "message": {
                "title": ["Attention Is All You Need"],
                "author": [{"given": "Ashish", "family": "Vaswani"}],
                "published-online": {"date-parts": [[2017]]},
                "reference-count": 40,
                "is-referenced-by-count": 100000,
            }
        }
        mock_fetch.return_value = mock_resp

        res, ok = await get_crossref_details("10.1234/5678")
        assert ok is True
        assert "Attention Is All You Need" in res
        assert "Ashish Vaswani" in res
        assert "2017" in res


class TestArxivClientHelpers:
    def test_extract_arxiv_id(self):
        assert extract_arxiv_id("2301.12345") == "2301.12345"
        assert extract_arxiv_id("https://arxiv.org/abs/2301.12345v2") == "2301.12345v2"
        assert extract_arxiv_id("nothing here") is None

    def test_find_section(self):
        sections = [
            {"title": "Introduction", "text": "Intro text", "level": 2},
            {"title": "Methods", "text": "Method text", "level": 2},
        ]
        sec = find_section(sections, "0")
        assert sec is not None
        assert sec["title"] == "Introduction"

        sec_by_name = find_section(sections, "methods")
        assert sec_by_name is not None
        assert sec_by_name["text"] == "Method text"
