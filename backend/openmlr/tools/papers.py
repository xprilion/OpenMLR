"""Papers tool — OpenAlex, Semantic Scholar, arXiv, CrossRef, Papers With Code.

Multi-source academic paper search with parallel execution, fallback support, and Redis caching.
- OpenAlex: API key optional (polite pool with mailto), key provides higher rate limits
- Semantic Scholar: API key optional but recommended for higher rate limits
- arXiv: Free API, no key required (polite request rate limiting)
- CrossRef/PWC: fully open APIs
- Paperclip: biomedical preprints & papers (bioRxiv, medRxiv, PMC, arXiv)
"""

from __future__ import annotations

import logging
from typing import Any

from ..agent.types import ToolSpec
from ..services.academic_providers import (
    get_paperclip_headers as _get_paperclip_headers,
)
from ..services.academic_providers import (
    openalex_search as _openalex_search,
)
from ..services.academic_providers import (
    paperclip_lookup as _paperclip_lookup,
)
from ..services.academic_providers import (
    paperclip_search as _paperclip_search,
)
from ..services.academic_providers import (
    reconstruct_abstract as _reconstruct_abstract,
)
from ..services.academic_providers import (
    semantic_scholar_search as _semantic_scholar_search,
)
from ..services.academic_providers import (
    to_openalex_id as _to_openalex_id,
)
from ..services.arxiv_client import (
    extract_arxiv_id as _extract_arxiv_id,
)
from ..services.arxiv_client import (
    read_arxiv_paper as _read_paper,
)
from ..services.arxiv_client import (
    search_arxiv as _arxiv_search,
)
from ..services.paper_search_engine import (
    find_code_implementations as _find_code,
)
from ..services.paper_search_engine import (
    find_datasets_for_topic as _find_datasets,
)
from ..services.paper_search_engine import (
    get_author_papers as _author_papers,
)
from ..services.paper_search_engine import (
    get_citations as _citations,
)
from ..services.paper_search_engine import (
    get_crossref_details as _crossref_details,
)
from ..services.paper_search_engine import (
    get_paper_details as _details,
)
from ..services.paper_search_engine import (
    get_recommendations as _recommend,
)
from ..services.paper_search_engine import (
    get_trending_papers as _trending,
)
from ..services.paper_search_engine import (
    search_papers_parallel as _search,
)
from .http_utils import fetch_with_retry

__all__ = [
    "_author_papers",
    "_arxiv_search",
    "_check_budget",
    "_citations",
    "_crossref_details",
    "_details",
    "_extract_arxiv_id",
    "_find_code",
    "_find_datasets",
    "_get_budget_info",
    "_get_paperclip_headers",
    "_handle_papers",
    "_increment_budget",
    "_openalex_search",
    "_paperclip_lookup",
    "_paperclip_search",
    "_read_paper",
    "_recommend",
    "_reconstruct_abstract",
    "_search",
    "_search_counts",
    "_semantic_scholar_search",
    "_to_openalex_id",
    "_trending",
    "create_papers_tool",
    "fetch_with_retry",
]

log = logging.getLogger(__name__)

# Per-session search budget tracking
_search_counts: dict[int, int] = {}  # session hash -> count
_BUDGET_DEFAULT = 25


def _check_budget(session=None) -> tuple[bool, str]:
    """Check if search budget allows another API call. Returns (ok, message)."""
    key = id(session) if session else 0
    count = _search_counts.get(key, 0)
    budget = (
        session.config.paper_search_budget
        if session and hasattr(session, "config")
        else _BUDGET_DEFAULT
    )
    if count >= budget:
        return (
            False,
            f"Search budget exhausted ({count}/{budget} calls). Ask the user before continuing.",
        )
    return True, ""


def _increment_budget(session=None) -> None:
    key = id(session) if session else 0
    _search_counts[key] = _search_counts.get(key, 0) + 1


def _get_budget_info(session=None) -> dict[str, int]:
    key = id(session) if session else 0
    budget = (
        session.config.paper_search_budget
        if session and hasattr(session, "config")
        else _BUDGET_DEFAULT
    )
    return {"used": _search_counts.get(key, 0), "max": budget}


def create_papers_tool() -> ToolSpec:
    """Create the papers tool spec with multi-source operations."""
    return ToolSpec(
        name="papers",
        description=(
            "Search and read academic papers using OpenAlex, Semantic Scholar, arXiv, CrossRef, "
            "Papers With Code, and Paperclip (8M+ biomedical papers from bioRxiv, medRxiv, PMC). "
            "Multi-source search with automatic fallback for best results. "
            "Operations: search (OpenAlex+S2), arxiv_search (arXiv direct), semantic_search (Semantic Scholar), "
            "paperclip_search (biomedical: bioRxiv/medRxiv/PMC/arXiv), paperclip_lookup (lookup by DOI/PMID), "
            "trending, details, read_paper, citations, recommend, find_code, find_datasets, "
            "author_papers."
        ),
        parameters={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": [
                        "search",
                        "arxiv_search",
                        "semantic_search",
                        "paperclip_search",
                        "paperclip_lookup",
                        "trending",
                        "details",
                        "read_paper",
                        "citations",
                        "recommend",
                        "find_code",
                        "find_datasets",
                        "author_papers",
                    ],
                    "description": (
                        "Operation to perform: "
                        "search=OpenAlex search (broad coverage), "
                        "arxiv_search=arXiv search (preprints, ML/CS/Physics), "
                        "semantic_search=Semantic Scholar search, "
                        "paperclip_search=Paperclip search (biomedical: bioRxiv, medRxiv, PMC, arXiv — 8M+ papers), "
                        "paperclip_lookup=lookup paper by DOI or PMID via Paperclip, "
                        "trending=highly cited recent papers, details=paper metadata, "
                        "read_paper=read arXiv paper sections, citations=references and citing papers, "
                        "recommend=related papers, find_code=code implementations, "
                        "find_datasets=related datasets, author_papers=papers by author"
                    ),
                },
                "query": {
                    "type": "string",
                    "description": "Search query, paper topic, or author name",
                },
                "paper_id": {
                    "type": "string",
                    "description": "Paper ID: OpenAlex ID (W...), DOI (10.xxx/...), arXiv ID (2301.12345), or S2 ID",
                },
                "section": {
                    "type": "string",
                    "description": "For read_paper: section name or number (omit for table of contents)",
                },
                "year_from": {
                    "type": "integer",
                    "description": "Filter: minimum publication year",
                },
                "year_to": {
                    "type": "integer",
                    "description": "Filter: maximum publication year",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 10)",
                },
                "source": {
                    "type": "string",
                    "enum": ["openalex", "semantic_scholar", "arxiv", "auto"],
                    "description": "Preferred source for search (default: auto, tries OpenAlex then Semantic Scholar)",
                },
                "paperclip_source": {
                    "type": "string",
                    "enum": ["biorxiv", "medrxiv", "pmc", "arxiv", "all"],
                    "description": "For paperclip_search: filter by source (default: all)",
                },
            },
            "required": ["operation"],
        },
        handler=_handle_papers,
    )


async def _handle_papers(
    operation: str,
    query: str | None = None,
    paper_id: str | None = None,
    section: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    limit: int = 10,
    source: str = "auto",
    paperclip_source: str = "all",
    session: Any = None,
    **kwargs,
) -> tuple[str, bool]:
    # Budget check for API-calling operations
    api_ops = {
        "search",
        "arxiv_search",
        "semantic_search",
        "paperclip_search",
        "paperclip_lookup",
        "trending",
        "details",
        "citations",
        "recommend",
        "find_code",
        "find_datasets",
        "author_papers",
    }
    if operation in api_ops:
        ok, msg = _check_budget(session)
        if not ok:
            return msg, False
        _increment_budget(session)
        # Emit budget update
        if session and hasattr(session, "emit"):
            from ..agent.types import AgentEvent

            await session.emit(
                AgentEvent(
                    event_type="search_budget",
                    data=_get_budget_info(session),
                )
            )

    handlers = {
        "search": lambda: _search(query or "", year_from, year_to, limit, source),
        "arxiv_search": lambda: _arxiv_search(query or "", year_from, year_to, limit),
        "semantic_search": lambda: _semantic_scholar_search(query or "", year_from, year_to, limit),
        "paperclip_search": lambda: _paperclip_search(
            query or "", year_from, year_to, limit, paperclip_source
        ),
        "paperclip_lookup": lambda: _paperclip_lookup(paper_id or ""),
        "trending": lambda: _trending(query, limit),
        "details": lambda: _details(paper_id or ""),
        "read_paper": lambda: _read_paper(paper_id or "", section),
        "citations": lambda: _citations(paper_id or "", limit),
        "recommend": lambda: _recommend(paper_id or "", limit),
        "find_code": lambda: _find_code(paper_id or query or ""),
        "find_datasets": lambda: _find_datasets(paper_id or query or ""),
        "author_papers": lambda: _author_papers(query or "", limit),
    }

    handler = handlers.get(operation)
    if not handler:
        return f"Unknown operation: {operation}", False
    try:
        return await handler()
    except Exception as e:
        return f"Papers tool error ({operation}): {str(e)}", False
