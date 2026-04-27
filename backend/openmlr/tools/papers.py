"""Papers tool — OpenAlex, Semantic Scholar, arXiv, CrossRef, Papers With Code.

Multi-source academic paper search with fallback support and retry logic.
- OpenAlex: API key optional (polite pool with mailto), key provides higher rate limits
- Semantic Scholar: API key optional but recommended for higher rate limits
- arXiv: Free API, no key required (3 second delay between requests recommended)
- CrossRef/PWC: fully open APIs
"""

import logging
import os
import re
import xml.etree.ElementTree as ET

from ..agent.types import ToolSpec
from .http_utils import RateLimitError, fetch_with_retry

log = logging.getLogger(__name__)

OPENALEX_API = "https://api.openalex.org"
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1"
CROSSREF_API = "https://api.crossref.org"
ARXIV_API = "https://export.arxiv.org/api/query"
AR5IV_BASE = "https://ar5iv.labs.arxiv.org/html"
PWC_API = "https://paperswithcode.com/api/v1"

# OpenAlex: API key or polite pool via mailto
MAILTO = os.environ.get("OPENALEX_EMAIL", "openmlr@example.com")

# arXiv namespace for XML parsing
ARXIV_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


def _get_openalex_params(extra: dict = None) -> dict:
    """Get OpenAlex params - uses API key if available, otherwise polite pool."""
    api_key = os.environ.get("OPENALEX_API_KEY")
    p = {}
    if api_key:
        p["api_key"] = api_key
    else:
        p["mailto"] = MAILTO
    if extra:
        p.update(extra)
    return p


def _get_semantic_scholar_headers() -> dict:
    """Get Semantic Scholar headers with API key if available."""
    headers = {}
    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key
    return headers


def create_papers_tool() -> ToolSpec:
    return ToolSpec(
        name="papers",
        description=(
            "Search and read academic papers using OpenAlex, Semantic Scholar, arXiv, CrossRef, and Papers With Code. "
            "Multi-source search with automatic fallback for best results. "
            "Operations: search (OpenAlex+S2), arxiv_search (arXiv direct), semantic_search (Semantic Scholar), "
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
                    "enum": ["openalex", "semantic_scholar", "auto"],
                    "description": "Preferred source for search (default: auto, tries OpenAlex then Semantic Scholar)",
                },
            },
            "required": ["operation"],
        },
        handler=_handle_papers,
    )


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


def _increment_budget(session=None):
    key = id(session) if session else 0
    _search_counts[key] = _search_counts.get(key, 0) + 1


def _get_budget_info(session=None) -> dict:
    key = id(session) if session else 0
    budget = (
        session.config.paper_search_budget
        if session and hasattr(session, "config")
        else _BUDGET_DEFAULT
    )
    return {"used": _search_counts.get(key, 0), "max": budget}


async def _handle_papers(
    operation: str,
    query: str = None,
    paper_id: str = None,
    section: str = None,
    year_from: int = None,
    year_to: int = None,
    limit: int = 10,
    source: str = "auto",
    session=None,
    **kwargs,
) -> tuple[str, bool]:
    # Budget check for API-calling operations
    api_ops = {
        "search",
        "arxiv_search",
        "semantic_search",
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
        if session:
            from ..agent.types import AgentEvent

            await session.emit(
                AgentEvent(
                    event_type="search_budget",
                    data=_get_budget_info(session),
                )
            )

    handlers = {
        "search": lambda: _search(query, year_from, year_to, limit, source),
        "arxiv_search": lambda: _arxiv_search(query, year_from, year_to, limit),
        "semantic_search": lambda: _semantic_scholar_search(query, year_from, year_to, limit),
        "trending": lambda: _trending(query, limit),
        "details": lambda: _details(paper_id),
        "read_paper": lambda: _read_paper(paper_id, section),
        "citations": lambda: _citations(paper_id, limit),
        "recommend": lambda: _recommend(paper_id, limit),
        "find_code": lambda: _find_code(paper_id or query),
        "find_datasets": lambda: _find_datasets(paper_id or query),
        "author_papers": lambda: _author_papers(query, limit),
    }
    handler = handlers.get(operation)
    if not handler:
        return f"Unknown operation: {operation}", False
    try:
        return await handler()
    except Exception as e:
        return f"Papers tool error ({operation}): {str(e)}", False


# ── Search (OpenAlex with S2 fallback) ────────────────────────────────────


async def _search(
    query: str, year_from: int = None, year_to: int = None, limit: int = 10, source: str = "auto"
) -> tuple[str, bool]:
    if not query:
        return "Provide a 'query' for search.", False

    # Try OpenAlex first (or if explicitly requested)
    if source in ("openalex", "auto"):
        result, success = await _openalex_search(query, year_from, year_to, limit)
        if success and "No papers found" not in result:
            return result, success
        # If OpenAlex failed or found nothing and we're in auto mode, try S2
        if source == "auto":
            s2_result, s2_success = await _semantic_scholar_search(query, year_from, year_to, limit)
            if s2_success and "No papers found" not in s2_result:
                return s2_result, s2_success
        return result, success  # Return OpenAlex result even if empty

    # Semantic Scholar explicitly requested
    if source == "semantic_scholar":
        return await _semantic_scholar_search(query, year_from, year_to, limit)

    return "Invalid source specified", False


async def _openalex_search(
    query: str, year_from: int = None, year_to: int = None, limit: int = 10
) -> tuple[str, bool]:
    """Search using OpenAlex API with retry logic."""
    params = _get_openalex_params({"search": query, "per_page": min(limit, 50)})

    filters = []
    if year_from:
        filters.append(f"from_publication_date:{year_from}-01-01")
    if year_to:
        filters.append(f"to_publication_date:{year_to}-12-31")
    if filters:
        params["filter"] = ",".join(filters)

    try:
        r = await fetch_with_retry(
            f"{OPENALEX_API}/works",
            params=params,
            timeout=20,
            max_retries=3,
        )
    except RateLimitError:
        return "OpenAlex rate limit reached. Try again later.", False
    except Exception as e:
        log.warning(f"OpenAlex search error: {e}")
        return f"OpenAlex error: {str(e)[:200]}", False

    if r.status_code != 200:
        return f"OpenAlex error {r.status_code}: {r.text[:300]}", False

    works = r.json().get("results", [])
    if not works:
        return f"No papers found for: {query}", True

    total = r.json().get("meta", {}).get("count", len(works))
    lines = [f"Found {total} papers for '{query}' (via OpenAlex):\n"]
    for i, w in enumerate(works, 1):
        authors = ", ".join(
            a.get("author", {}).get("display_name", "") for a in (w.get("authorships") or [])[:3]
        )
        if len(w.get("authorships", [])) > 3:
            authors += " et al."
        doi = (w.get("doi") or "").replace("https://doi.org/", "")
        oa_id = w.get("id", "").split("/")[-1]
        lines.append(
            f"{i}. **{w.get('title', 'Untitled')}** ({w.get('publication_year', '?')})\n"
            f"   Authors: {authors}\n"
            f"   Citations: {w.get('cited_by_count', 0)}  |  ID: {oa_id}"
            f"{f'  |  DOI: {doi}' if doi else ''}\n"
        )
    return "\n".join(lines), True


# ── arXiv Search ────────────────────────────────────


async def _arxiv_search(
    query: str, year_from: int = None, year_to: int = None, limit: int = 10
) -> tuple[str, bool]:
    """Search arXiv papers directly. Great for ML/CS/Physics preprints."""
    if not query:
        return "Provide a 'query' for search.", False

    # Build arXiv query
    # arXiv uses prefix search: all:term searches all fields
    search_query = f"all:{query}"

    params = {
        "search_query": search_query,
        "start": 0,
        "max_results": min(limit, 50),
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    try:
        r = await fetch_with_retry(
            ARXIV_API,
            params=params,
            timeout=30,
            max_retries=3,
            base_delay=3.0,  # arXiv recommends 3 second delay
        )
    except RateLimitError:
        return "arXiv rate limit reached. Wait a few seconds and try again.", False
    except Exception as e:
        log.warning(f"arXiv search error: {e}")
        return f"arXiv error: {str(e)[:200]}", False

    if r.status_code != 200:
        return f"arXiv error {r.status_code}: {r.text[:300]}", False

    # Parse Atom XML response
    try:
        root = ET.fromstring(r.text)
    except ET.ParseError as e:
        return f"arXiv XML parse error: {e}", False

    entries = root.findall("atom:entry", ARXIV_NS)
    if not entries:
        return f"No arXiv papers found for: {query}", True

    # Filter by year if specified
    filtered_entries = []
    for entry in entries:
        published = entry.find("atom:published", ARXIV_NS)
        if published is not None and published.text:
            year = int(published.text[:4])
            if year_from and year < year_from:
                continue
            if year_to and year > year_to:
                continue
        filtered_entries.append(entry)

    if not filtered_entries:
        return f"No arXiv papers found for: {query} (in year range)", True

    lines = [f"Found {len(filtered_entries)} arXiv papers for '{query}':\n"]
    for i, entry in enumerate(filtered_entries[:limit], 1):
        title_el = entry.find("atom:title", ARXIV_NS)
        title = title_el.text.strip().replace("\n", " ") if title_el is not None else "Untitled"

        # Get arXiv ID from id URL
        id_el = entry.find("atom:id", ARXIV_NS)
        arxiv_id = ""
        if id_el is not None and id_el.text:
            arxiv_id = id_el.text.split("/abs/")[-1]

        # Get authors
        authors_els = entry.findall("atom:author/atom:name", ARXIV_NS)
        authors = ", ".join(a.text for a in authors_els[:3])
        if len(authors_els) > 3:
            authors += " et al."

        # Get published date
        published = entry.find("atom:published", ARXIV_NS)
        year = published.text[:4] if published is not None and published.text else "?"

        # Get categories
        categories_els = entry.findall("atom:category", ARXIV_NS)
        categories = [c.get("term", "") for c in categories_els[:3]]
        cat_str = ", ".join(categories) if categories else ""

        lines.append(
            f"{i}. **{title}** ({year})\n"
            f"   Authors: {authors}\n"
            f"   arXiv: {arxiv_id}"
            f"{f'  |  Categories: {cat_str}' if cat_str else ''}\n"
        )

    return "\n".join(lines), True


# ── Semantic Scholar Search ────────────────────────────────────


async def _semantic_scholar_search(
    query: str, year_from: int = None, year_to: int = None, limit: int = 10
) -> tuple[str, bool]:
    """Search using Semantic Scholar API with retry logic."""
    if not query:
        return "Provide a 'query' for search.", False

    params = {
        "query": query,
        "limit": min(limit, 100),
        "fields": "paperId,title,year,authors,citationCount,abstract,externalIds",
    }

    # Year filtering
    if year_from or year_to:
        year_filter = ""
        if year_from and year_to:
            year_filter = f"{year_from}-{year_to}"
        elif year_from:
            year_filter = f"{year_from}-"
        elif year_to:
            year_filter = f"-{year_to}"
        params["year"] = year_filter

    headers = _get_semantic_scholar_headers()

    try:
        r = await fetch_with_retry(
            f"{SEMANTIC_SCHOLAR_API}/paper/search",
            params=params,
            headers=headers,
            timeout=20,
            max_retries=3,
        )
    except RateLimitError:
        return (
            "Semantic Scholar rate limit reached. Try again later or add SEMANTIC_SCHOLAR_API_KEY.",
            False,
        )
    except Exception as e:
        log.warning(f"Semantic Scholar search error: {e}")
        return f"Semantic Scholar error: {str(e)[:200]}", False

    if r.status_code == 429:
        return (
            "Semantic Scholar rate limit reached. Try again later or add SEMANTIC_SCHOLAR_API_KEY.",
            False,
        )
    if r.status_code != 200:
        return f"Semantic Scholar error {r.status_code}: {r.text[:300]}", False

    data = r.json()
    papers = data.get("data", [])
    if not papers:
        return f"No papers found for: {query}", True

    total = data.get("total", len(papers))
    lines = [f"Found {total} papers for '{query}' (via Semantic Scholar):\n"]
    for i, p in enumerate(papers, 1):
        authors = ", ".join(a.get("name", "") for a in (p.get("authors") or [])[:3])
        if len(p.get("authors", [])) > 3:
            authors += " et al."
        doi = (p.get("externalIds") or {}).get("DOI", "")
        arxiv = (p.get("externalIds") or {}).get("ArXiv", "")
        s2_id = p.get("paperId", "")

        id_info = f"S2:{s2_id[:12]}"
        if doi:
            id_info += f"  |  DOI: {doi}"
        if arxiv:
            id_info += f"  |  arXiv: {arxiv}"

        lines.append(
            f"{i}. **{p.get('title', 'Untitled')}** ({p.get('year', '?')})\n"
            f"   Authors: {authors}\n"
            f"   Citations: {p.get('citationCount', 0)}  |  {id_info}\n"
        )
    return "\n".join(lines), True


# ── Trending (OpenAlex) ──────────────────────────────────


async def _trending(query: str = None, limit: int = 10) -> tuple[str, bool]:
    params = _get_openalex_params(
        {
            "sort": "cited_by_count:desc",
            "filter": "from_publication_date:2024-01-01",
            "per_page": min(limit, 50),
        }
    )
    if query:
        params["search"] = query

    try:
        r = await fetch_with_retry(
            f"{OPENALEX_API}/works",
            params=params,
            timeout=20,
            max_retries=3,
        )
    except RateLimitError:
        return "OpenAlex rate limit reached. Try again later.", False
    except Exception as e:
        log.warning(f"OpenAlex trending error: {e}")
        return f"OpenAlex error: {str(e)[:200]}", False

    if r.status_code != 200:
        return f"OpenAlex error {r.status_code}", False

    works = r.json().get("results", [])
    if not works:
        return "No trending papers found.", True

    lines = [f"Trending papers{f' on: {query}' if query else ''}:\n"]
    for i, w in enumerate(works, 1):
        authors = ", ".join(
            a.get("author", {}).get("display_name", "") for a in (w.get("authorships") or [])[:3]
        )
        lines.append(
            f"{i}. **{w.get('title', 'Untitled')}** ({w.get('publication_year', '?')})\n"
            f"   {authors}  |  {w.get('cited_by_count', 0)} citations\n"
        )
    return "\n".join(lines), True


# ── Details (OpenAlex + CrossRef) ─────────────────────────


async def _details(paper_id: str) -> tuple[str, bool]:
    if not paper_id:
        return "Provide a 'paper_id'.", False

    oa_id = _to_openalex_id(paper_id)

    try:
        r = await fetch_with_retry(
            f"{OPENALEX_API}/works/{oa_id}",
            params=_get_openalex_params(),
            timeout=20,
            max_retries=3,
        )
    except RateLimitError:
        return "OpenAlex rate limit reached. Try again later.", False
    except Exception as e:
        log.warning(f"OpenAlex details error: {e}")
        # Fallback to CrossRef for DOI
        if paper_id.startswith("10."):
            return await _crossref_details(paper_id)
        return f"Paper lookup error: {str(e)[:200]}", False

    if r.status_code != 200:
        # Fallback to CrossRef for DOI
        if paper_id.startswith("10."):
            return await _crossref_details(paper_id)
        return f"Paper not found: {paper_id}", False

    w = r.json()
    authors = ", ".join(
        a.get("author", {}).get("display_name", "") for a in (w.get("authorships") or [])
    )
    doi = (w.get("doi") or "").replace("https://doi.org/", "")
    oa_url = (w.get("open_access") or {}).get("oa_url", "")
    arxiv_id = _extract_arxiv_from_ids(w.get("ids", {}))

    lines = [
        f"# {w.get('title', 'Untitled')}",
        f"**Year**: {w.get('publication_year', '?')}",
        f"**Authors**: {authors}",
        f"**Citations**: {w.get('cited_by_count', 0)}  |  **References**: {len(w.get('referenced_works', []))}",
    ]
    if doi:
        lines.append(f"**DOI**: https://doi.org/{doi}")
    if arxiv_id:
        lines.append(f"**ArXiv**: https://arxiv.org/abs/{arxiv_id}")
    if oa_url:
        lines.append(f"**Open Access**: {oa_url}")

    abstract = _reconstruct_abstract(w.get("abstract_inverted_index"))
    if abstract:
        lines.append(f"\n**Abstract**:\n{abstract}")

    return "\n".join(lines), True


async def _crossref_details(doi: str) -> tuple[str, bool]:
    try:
        r = await fetch_with_retry(
            f"{CROSSREF_API}/works/{doi}",
            params={"mailto": MAILTO},
            timeout=15,
            max_retries=3,
        )
    except RateLimitError:
        return "CrossRef rate limit reached. Try again later.", False
    except Exception as e:
        log.warning(f"CrossRef details error: {e}")
        return f"CrossRef lookup failed: {str(e)[:200]}", False

    if r.status_code != 200:
        return f"CrossRef lookup failed for DOI: {doi}", False

    w = r.json().get("message", {})
    title = (w.get("title") or ["Untitled"])[0]
    authors = ", ".join(
        f"{a.get('given', '')} {a.get('family', '')}" for a in (w.get("author") or [])
    )
    year = (w.get("published-print") or w.get("published-online") or {}).get(
        "date-parts", [[None]]
    )[0][0]

    lines = [
        f"# {title}",
        f"**Year**: {year or '?'}",
        f"**Authors**: {authors}",
        f"**DOI**: https://doi.org/{doi}",
        f"**References**: {w.get('reference-count', 0)}",
        f"**Cited by**: {w.get('is-referenced-by-count', 0)}",
    ]
    return "\n".join(lines), True


# ── Read Paper (ArXiv HTML via ar5iv) ─────────────────────


async def _read_paper(paper_id: str, section: str = None) -> tuple[str, bool]:
    if not paper_id:
        return "Provide a 'paper_id' (arXiv ID like '2301.12345').", False

    arxiv_id = _extract_arxiv_id(paper_id)
    if not arxiv_id:
        return f"Need an arXiv ID to read full text. Got: {paper_id}", False

    url = f"{AR5IV_BASE}/{arxiv_id}"
    try:
        r = await fetch_with_retry(
            url,
            timeout=30,
            max_retries=3,
        )
    except Exception as e:
        log.warning(f"ar5iv fetch error: {e}")
        return f"Failed to fetch paper: {str(e)[:200]}", False

    if r.status_code != 200:
        return f"Failed to fetch paper HTML (status {r.status_code}).", False

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(r.text, "lxml")
    sections = _parse_sections(soup)

    if not sections:
        return "Could not parse paper structure.", False

    if not section:
        toc = ["# Table of Contents\n"]
        for i, s in enumerate(sections):
            indent = "  " if s.get("level", 2) > 2 else ""
            toc.append(f"{indent}{i}. {s['title']}")
        toc.append("\nUse read_paper with section=<number or name> to read a section.")
        return "\n".join(toc), True

    target = _find_section(sections, section)
    if not target:
        return f"Section '{section}' not found.", False

    text = target.get("text", "")
    if len(text) > 20000:
        text = text[:20000] + "\n\n...[truncated]"
    return f"# {target['title']}\n\n{text}", True


# ── Citations (OpenAlex) ──────────────────────────────────


async def _citations(paper_id: str, limit: int = 10) -> tuple[str, bool]:
    if not paper_id:
        return "Provide a 'paper_id'.", False

    oa_id = _to_openalex_id(paper_id)

    # Get the paper's referenced_works
    try:
        r = await fetch_with_retry(
            f"{OPENALEX_API}/works/{oa_id}",
            params=_get_openalex_params(),
            timeout=20,
            max_retries=3,
        )
    except RateLimitError:
        return "OpenAlex rate limit reached. Try again later.", False
    except Exception as e:
        log.warning(f"OpenAlex citations error: {e}")
        return f"Citations lookup error: {str(e)[:200]}", False

    if r.status_code != 200:
        return f"Paper not found: {paper_id}", False

    w = r.json()
    ref_ids = w.get("referenced_works", [])[:limit]
    lines = [
        f"## References ({len(w.get('referenced_works', []))} total, showing {len(ref_ids)})\n"
    ]

    # Batch-fetch referenced works
    if ref_ids:
        pipe = "|".join(ref_ids)
        try:
            r2 = await fetch_with_retry(
                f"{OPENALEX_API}/works",
                params=_get_openalex_params({"filter": f"openalex:{pipe}", "per_page": limit}),
                timeout=20,
                max_retries=2,
            )
            if r2.status_code == 200:
                for rw in r2.json().get("results", []):
                    lines.append(
                        f"- **{rw.get('title', 'Untitled')}** ({rw.get('publication_year', '?')}) "
                        f"[{rw.get('cited_by_count', 0)} cites]"
                    )
        except Exception:
            lines.append("(Could not fetch reference details)")

    # Cited-by via filter
    lines.append(f"\n## Cited by ({w.get('cited_by_count', 0)} total)\n")
    try:
        r3 = await fetch_with_retry(
            f"{OPENALEX_API}/works",
            params=_get_openalex_params(
                {
                    "filter": f"cites:{oa_id}",
                    "sort": "cited_by_count:desc",
                    "per_page": limit,
                }
            ),
            timeout=20,
            max_retries=2,
        )
        if r3.status_code == 200:
            for cw in r3.json().get("results", []):
                lines.append(
                    f"- **{cw.get('title', 'Untitled')}** ({cw.get('publication_year', '?')}) "
                    f"[{cw.get('cited_by_count', 0)} cites]"
                )
    except Exception:
        lines.append("(Could not fetch citing papers)")

    return "\n".join(lines), True


# ── Recommendations (OpenAlex related_works) ──────────────


async def _recommend(paper_id: str, limit: int = 10) -> tuple[str, bool]:
    if not paper_id:
        return "Provide a 'paper_id'.", False

    oa_id = _to_openalex_id(paper_id)

    try:
        r = await fetch_with_retry(
            f"{OPENALEX_API}/works/{oa_id}",
            params=_get_openalex_params(),
            timeout=20,
            max_retries=3,
        )
    except RateLimitError:
        return "OpenAlex rate limit reached. Try again later.", False
    except Exception as e:
        log.warning(f"OpenAlex recommend error: {e}")
        return f"Recommendation lookup error: {str(e)[:200]}", False

    if r.status_code != 200:
        return f"Paper not found: {paper_id}", False

    related = r.json().get("related_works", [])[:limit]
    if not related:
        return "No related works found.", True

    pipe = "|".join(related)
    try:
        r2 = await fetch_with_retry(
            f"{OPENALEX_API}/works",
            params=_get_openalex_params({"filter": f"openalex:{pipe}", "per_page": limit}),
            timeout=20,
            max_retries=2,
        )
    except Exception as e:
        log.warning(f"OpenAlex related works fetch error: {e}")
        return "Failed to fetch related works.", False

    if r2.status_code != 200:
        return "Failed to fetch related works.", False

    lines = ["## Related Papers\n"]
    for i, w in enumerate(r2.json().get("results", []), 1):
        authors = ", ".join(
            a.get("author", {}).get("display_name", "") for a in (w.get("authorships") or [])[:3]
        )
        lines.append(
            f"{i}. **{w.get('title', 'Untitled')}** ({w.get('publication_year', '?')})\n"
            f"   {authors}  |  {w.get('cited_by_count', 0)} citations\n"
        )
    return "\n".join(lines), True


# ── Find Code (Papers With Code) ─────────────────────────


async def _find_code(query: str) -> tuple[str, bool]:
    if not query:
        return "Provide a query.", False

    try:
        r = await fetch_with_retry(
            f"{PWC_API}/search/",
            params={"q": query, "page": 1},
            timeout=15,
            max_retries=3,
        )
    except RateLimitError:
        return "Papers With Code rate limit reached. Try again later.", False
    except Exception as e:
        log.warning(f"Papers With Code search error: {e}")
        return f"Papers With Code error: {str(e)[:200]}", False

    if r.status_code != 200:
        return "Papers With Code API error.", False

    results = r.json().get("results", [])[:10]
    if not results:
        return f"No code found for: {query}", True

    lines = ["## Code Implementations\n"]
    for item in results:
        paper = item.get("paper", {})
        lines.append(f"- **{paper.get('title', 'Unknown')}**")
        if item.get("repository"):
            lines.append(f"  Repo: {item['repository'].get('url', '')}")
    return "\n".join(lines), True


# ── Find Datasets (Papers With Code) ─────────────────────


async def _find_datasets(query: str) -> tuple[str, bool]:
    if not query:
        return "Provide a query.", False

    try:
        r = await fetch_with_retry(
            f"{PWC_API}/datasets/",
            params={"q": query, "page": 1},
            timeout=15,
            max_retries=3,
        )
    except RateLimitError:
        return "Papers With Code rate limit reached. Try again later.", False
    except Exception as e:
        log.warning(f"Papers With Code datasets error: {e}")
        return f"Papers With Code error: {str(e)[:200]}", False

    if r.status_code != 200:
        return "Papers With Code datasets API error.", False

    results = r.json().get("results", [])[:10]
    if not results:
        return f"No datasets found for: {query}", True

    lines = ["## Related Datasets\n"]
    for d in results:
        name = d.get("name", "Unknown")
        desc = (d.get("description") or "")[:150]
        lines.append(f"- **{name}**: {desc}")
    return "\n".join(lines), True


# ── Author Papers (Semantic Scholar) ─────────────────────


async def _author_papers(author_query: str, limit: int = 10) -> tuple[str, bool]:
    """Find papers by a specific author using Semantic Scholar."""
    if not author_query:
        return "Provide an author name in 'query'.", False

    # First search for the author
    params = {"query": author_query, "limit": 5}
    headers = _get_semantic_scholar_headers()

    try:
        r = await fetch_with_retry(
            f"{SEMANTIC_SCHOLAR_API}/author/search",
            params=params,
            headers=headers,
            timeout=20,
            max_retries=3,
        )
    except RateLimitError:
        return (
            "Semantic Scholar rate limit reached. Try again later or add SEMANTIC_SCHOLAR_API_KEY.",
            False,
        )
    except Exception as e:
        log.warning(f"Semantic Scholar author search error: {e}")
        return f"Author search error: {str(e)[:200]}", False

    if r.status_code == 429:
        return (
            "Semantic Scholar rate limit reached. Try again later or add SEMANTIC_SCHOLAR_API_KEY.",
            False,
        )
    if r.status_code != 200:
        return f"Author search error {r.status_code}: {r.text[:300]}", False

    data = r.json()
    authors = data.get("data", [])
    if not authors:
        return f"No authors found matching: {author_query}", True

    # Get papers from the best matching author
    author = authors[0]
    author_id = author.get("authorId")
    author_name = author.get("name", author_query)

    params = {
        "fields": "paperId,title,year,citationCount,externalIds",
        "limit": min(limit, 100),
    }

    try:
        r = await fetch_with_retry(
            f"{SEMANTIC_SCHOLAR_API}/author/{author_id}/papers",
            params=params,
            headers=headers,
            timeout=20,
            max_retries=3,
        )
    except RateLimitError:
        return (
            "Semantic Scholar rate limit reached. Try again later or add SEMANTIC_SCHOLAR_API_KEY.",
            False,
        )
    except Exception as e:
        log.warning(f"Semantic Scholar author papers error: {e}")
        return f"Error fetching author papers: {str(e)[:200]}", False

    if r.status_code != 200:
        return f"Error fetching author papers: {r.status_code}", False

    papers = r.json().get("data", [])
    if not papers:
        return f"No papers found for author: {author_name}", True

    # Sort by citation count
    papers.sort(key=lambda p: p.get("citationCount", 0), reverse=True)
    papers = papers[:limit]

    lines = [f"## Papers by {author_name}\n"]
    for i, p in enumerate(papers, 1):
        doi = (p.get("externalIds") or {}).get("DOI", "")
        arxiv = (p.get("externalIds") or {}).get("ArXiv", "")

        id_info = ""
        if doi:
            id_info += f"DOI: {doi}"
        if arxiv:
            id_info += f"  arXiv: {arxiv}" if id_info else f"arXiv: {arxiv}"

        lines.append(
            f"{i}. **{p.get('title', 'Untitled')}** ({p.get('year', '?')})\n"
            f"   Citations: {p.get('citationCount', 0)}"
            f"{f'  |  {id_info}' if id_info else ''}\n"
        )
    return "\n".join(lines), True


# ── Helpers ───────────────────────────────────────────────


def _to_openalex_id(paper_id: str) -> str:
    """Convert various IDs to OpenAlex lookup format."""
    if paper_id.startswith("W") or paper_id.startswith("https://openalex.org/"):
        return paper_id
    if paper_id.startswith("10."):
        return f"https://doi.org/{paper_id}"
    arxiv = _extract_arxiv_id(paper_id)
    if arxiv:
        return f"https://doi.org/10.48550/arXiv.{arxiv}"
    return paper_id


def _extract_arxiv_id(text: str) -> str | None:
    match = re.search(r"(\d{4}\.\d{4,5}(?:v\d+)?)", text)
    if match:
        return match.group(1)
    match = re.search(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5}(?:v\d+)?)", text)
    if match:
        return match.group(1)
    return None


def _extract_arxiv_from_ids(ids: dict) -> str | None:
    """Extract arxiv ID from OpenAlex ids dict."""
    ids.get("openalex", "")
    doi = ids.get("doi", "")
    if "arXiv" in doi:
        return _extract_arxiv_id(doi)
    return None


def _reconstruct_abstract(inverted_index: dict) -> str | None:
    """Reconstruct abstract from OpenAlex's inverted index format."""
    if not inverted_index:
        return None
    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort()
    return " ".join(w for _, w in word_positions)


def _parse_sections(soup) -> list[dict]:
    sections = []
    title_tag = soup.find("h1", class_="ltx_title")
    if title_tag:
        sections.append({"title": title_tag.get_text(strip=True), "text": "", "level": 1})

    abstract = soup.find("div", class_="ltx_abstract")
    if abstract:
        sections.append(
            {
                "title": "Abstract",
                "text": abstract.get_text(strip=True).replace("Abstract", "", 1).strip(),
                "level": 2,
            }
        )

    for heading in soup.find_all(["h2", "h3", "h4"]):
        level = int(heading.name[1])
        title = heading.get_text(strip=True)
        if not title:
            continue
        text_parts = []
        for sibling in heading.find_next_siblings():
            if sibling.name in ("h2", "h3", "h4"):
                break
            text = sibling.get_text(strip=True)
            if text:
                text_parts.append(text)
        sections.append({"title": title, "text": "\n\n".join(text_parts), "level": level})

    return sections


def _find_section(sections: list[dict], query: str) -> dict | None:
    try:
        idx = int(query)
        if 0 <= idx < len(sections):
            return sections[idx]
    except ValueError:
        pass
    query_lower = query.lower().strip()
    for sec in sections:
        if query_lower in sec["title"].lower():
            return sec
    return None
