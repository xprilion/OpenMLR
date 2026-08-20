"""Academic API providers — OpenAlex, Semantic Scholar, CrossRef, Paperclip, Papers With Code."""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

from ..tools.http_utils import RateLimitError
from ..tools.http_utils import fetch_with_retry as _default_fetch

log = logging.getLogger(__name__)

OPENALEX_API = "https://api.openalex.org"
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1"
CROSSREF_API = "https://api.crossref.org"
PWC_API = "https://paperswithcode.com/api/v1"
PAPERCLIP_API = "https://paperclip.gxl.ai"

MAILTO = os.environ.get("OPENALEX_EMAIL", "openmlr@example.com")
_PAPERCLIP_RATE_LIMIT_MSG = "Paperclip rate limit reached. Try again later."


def _get_active_fetch():
    """Retrieve fetch_with_retry dynamically to support unittest.mock patching."""
    papers_mod = sys.modules.get("openmlr.tools.papers")
    if papers_mod and hasattr(papers_mod, "fetch_with_retry"):
        return getattr(papers_mod, "fetch_with_retry")
    return _default_fetch


def get_openalex_params(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Get OpenAlex params - uses API key if available, otherwise polite pool."""
    api_key = os.environ.get("OPENALEX_API_KEY")
    p: dict[str, Any] = {}
    if api_key:
        p["api_key"] = api_key
    else:
        p["mailto"] = MAILTO
    if extra:
        p.update(extra)
    return p


def get_semantic_scholar_headers() -> dict[str, str]:
    """Get Semantic Scholar headers with API key if available."""
    headers = {}
    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key
    return headers


def get_paperclip_headers() -> dict[str, str] | None:
    """Get Paperclip auth headers. Returns None if not configured."""
    api_key = os.environ.get("PAPERCLIP_API_KEY")
    if not api_key:
        return None
    return {
        "Content-Type": "application/json",
        "X-API-Key": api_key,
    }


def to_openalex_id(paper_id: str) -> str:
    """Convert various IDs to OpenAlex lookup format."""
    if paper_id.startswith("W") or paper_id.startswith("https://openalex.org/"):
        return paper_id
    if paper_id.startswith("10."):
        return f"https://doi.org/{paper_id}"
    from .arxiv_client import extract_arxiv_id

    arxiv = extract_arxiv_id(paper_id)
    if arxiv:
        return f"https://doi.org/10.48550/arXiv.{arxiv}"
    return paper_id


def extract_arxiv_from_ids(ids: dict[str, Any]) -> str | None:
    """Extract arxiv ID from OpenAlex ids dict."""
    from .arxiv_client import extract_arxiv_id

    doi = ids.get("openalex", "") or ids.get("doi", "")
    if "arXiv" in doi:
        return extract_arxiv_id(doi)
    return None


def reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    """Reconstruct abstract from OpenAlex's inverted index format."""
    if not inverted_index:
        return None
    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort()
    return " ".join(w for _, w in word_positions)


async def openalex_search(
    query: str,
    year_from: int | None = None,
    year_to: int | None = None,
    limit: int = 10,
) -> tuple[str, bool]:
    """Search using OpenAlex API with retry logic."""
    params = get_openalex_params({"search": query, "per_page": min(limit, 50)})

    filters = []
    if year_from:
        filters.append(f"from_publication_date:{year_from}-01-01")
    if year_to:
        filters.append(f"to_publication_date:{year_to}-12-31")
    if filters:
        params["filter"] = ",".join(filters)

    fetch_fn = _get_active_fetch()
    try:
        r = await fetch_fn(
            f"{OPENALEX_API}/works",
            params=params,
            timeout=20,
            max_retries=3,
        )
    except RateLimitError:
        return "OpenAlex rate limit reached. Try again later.", False
    except Exception as e:
        log.warning("OpenAlex search error: %s", e)
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


async def semantic_scholar_search(
    query: str,
    year_from: int | None = None,
    year_to: int | None = None,
    limit: int = 10,
) -> tuple[str, bool]:
    """Search using Semantic Scholar API with retry logic."""
    if not query:
        return "Provide a 'query' for search.", False

    params: dict[str, Any] = {
        "query": query,
        "limit": min(limit, 100),
        "fields": "paperId,title,year,authors,citationCount,abstract,externalIds",
    }

    if year_from or year_to:
        if year_from and year_to:
            params["year"] = f"{year_from}-{year_to}"
        elif year_from:
            params["year"] = f"{year_from}-"
        elif year_to:
            params["year"] = f"-{year_to}"

    headers = get_semantic_scholar_headers()
    fetch_fn = _get_active_fetch()

    try:
        r = await fetch_fn(
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
        log.warning("Semantic Scholar search error: %s", e)
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


async def paperclip_search(
    query: str,
    year_from: int | None = None,
    year_to: int | None = None,
    limit: int = 10,
    paperclip_source: str = "all",
) -> tuple[str, bool]:
    """Search biomedical papers using Paperclip (bioRxiv, medRxiv, PMC, arXiv)."""
    if not query:
        return "Provide a 'query' for search.", False

    headers = get_paperclip_headers()
    if not headers:
        return (
            "PAPERCLIP_API_KEY not configured. "
            "Set it in Settings > Providers or set the PAPERCLIP_API_KEY environment variable. "
            "Get an API key at https://paperclip.gxl.ai",
            False,
        )

    raw_parts = [f'"{query}"', f"-n {min(limit, 100)}"]
    if paperclip_source and paperclip_source != "all":
        raw_parts.append(f"--source {paperclip_source}")

    year = year_from or year_to
    if year:
        raw_parts.append(f"--year {year}")

    raw = " ".join(raw_parts)
    fetch_fn = _get_active_fetch()

    try:
        resp = await fetch_fn(
            f"{PAPERCLIP_API}/api/cli/execute",
            method="POST",
            headers=headers,
            json={"command": "search", "raw": raw},
            timeout=120,
            max_retries=2,
        )
    except RateLimitError:
        return _PAPERCLIP_RATE_LIMIT_MSG, False
    except Exception as e:
        log.warning("Paperclip search error: %s", e)
        return f"Paperclip error: {str(e)[:200]}", False

    return parse_paperclip_response(resp, query)


def parse_paperclip_response(resp, query: str) -> tuple[str, bool]:
    """Parse and format a Paperclip API response."""
    if resp.status_code in (401, 403):
        return (
            "PAPERCLIP_API_KEY is invalid or expired. Check your API key in Settings > Providers.",
            False,
        )
    if resp.status_code == 429:
        return _PAPERCLIP_RATE_LIMIT_MSG, False
    if resp.status_code != 200:
        try:
            detail = resp.json().get("detail", resp.text[:300])
        except Exception:
            detail = resp.text[:300]
        return f"Paperclip error {resp.status_code}: {detail}", False

    data = resp.json()
    output = data.get("output", "")

    if not output:
        return f"No papers found for: {query}", True

    result_id = data.get("result_id", "")
    elapsed = data.get("elapsed_ms")
    header = "Results via Paperclip (bioRxiv/medRxiv/PMC/arXiv)"
    if elapsed:
        header += f" [{elapsed}ms]"
    if result_id:
        header += f" [{result_id}]"

    return f"{header}:\n\n{output}", True


async def paperclip_lookup(paper_id: str) -> tuple[str, bool]:
    """Look up a paper by DOI or PMID using Paperclip."""
    if not paper_id:
        return "Provide a 'paper_id' (DOI like '10.1101/...' or PMID).", False

    headers = get_paperclip_headers()
    if not headers:
        return (
            "PAPERCLIP_API_KEY not configured. "
            "Set it in Settings > Providers or set the PAPERCLIP_API_KEY environment variable. "
            "Get an API key at https://paperclip.gxl.ai",
            False,
        )

    field = "pmid" if paper_id.isdigit() else "doi"
    raw = f"{field} {paper_id}"
    fetch_fn = _get_active_fetch()

    try:
        resp = await fetch_fn(
            f"{PAPERCLIP_API}/api/cli/execute",
            method="POST",
            headers=headers,
            json={"command": "lookup", "raw": raw},
            timeout=60,
            max_retries=2,
        )
    except RateLimitError:
        return _PAPERCLIP_RATE_LIMIT_MSG, False
    except Exception as e:
        log.warning("Paperclip lookup error: %s", e)
        return f"Paperclip lookup error: {str(e)[:200]}", False

    if resp.status_code in (401, 403):
        return "PAPERCLIP_API_KEY is invalid or expired.", False
    if resp.status_code != 200:
        try:
            detail = resp.json().get("detail", resp.text[:300])
        except Exception:
            detail = resp.text[:300]
        return f"Paperclip lookup error {resp.status_code}: {detail}", False

    data = resp.json()
    output = data.get("output", "")
    if not output:
        return f"No paper found for {field}: {paper_id}", True

    return f"Paperclip lookup result:\n\n{output}", True
