"""Parallel multi-source academic paper search engine with cross-provider aggregation and caching."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from ..tools.http_utils import RateLimitError, fetch_with_retry
from .academic_providers import (
    CROSSREF_API,
    MAILTO,
    OPENALEX_API,
    PWC_API,
    SEMANTIC_SCHOLAR_API,
    extract_arxiv_from_ids,
    get_openalex_params,
    get_semantic_scholar_headers,
    openalex_search,
    reconstruct_abstract,
    semantic_scholar_search,
    to_openalex_id,
)
from .arxiv_client import search_arxiv
from .paper_cache import paper_cache

log = logging.getLogger(__name__)


async def search_papers_parallel(
    query: str,
    year_from: int | None = None,
    year_to: int | None = None,
    limit: int = 10,
    source: str = "auto",
) -> tuple[str, bool]:
    """Search academic papers across multiple providers with caching and graceful fallbacks."""
    if not query:
        return "Provide a 'query' for search.", False

    filters = {"year_from": year_from, "year_to": year_to, "limit": limit, "source": source}
    cached = await paper_cache.get_cached_search(query, filters)
    if cached and isinstance(cached, str):
        return cached, True

    if source == "openalex":
        res, ok = await openalex_search(query, year_from, year_to, limit)
    elif source == "semantic_scholar":
        res, ok = await semantic_scholar_search(query, year_from, year_to, limit)
    elif source == "arxiv":
        res, ok = await search_arxiv(query, year_from, year_to, limit)
    else:
        tasks = [
            openalex_search(query, year_from, year_to, limit),
            semantic_scholar_search(query, year_from, year_to, limit),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        first, second = results[0], results[1]
        oa_res: tuple[str, bool] = first if isinstance(first, tuple) else (str(first), False)
        s2_res: tuple[str, bool] = second if isinstance(second, tuple) else (str(second), False)

        if oa_res[1] and "No papers found" not in oa_res[0]:
            res, ok = oa_res
        elif s2_res[1] and "No papers found" not in s2_res[0]:
            res, ok = s2_res
        else:
            res, ok = oa_res if oa_res[1] else s2_res

    if ok:
        await paper_cache.set_cached_search(query, res, filters)
    return res, ok


def _format_openalex_details(w: dict[str, Any]) -> str:
    """Format OpenAlex work JSON payload into markdown details."""
    authors = ", ".join(
        a.get("author", {}).get("display_name", "") for a in (w.get("authorships") or [])
    )
    doi = (w.get("doi") or "").replace("https://doi.org/", "")
    oa_url = (w.get("open_access") or {}).get("oa_url", "")
    arxiv_id = extract_arxiv_from_ids(w.get("ids", {}))

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

    abstract = reconstruct_abstract(w.get("abstract_inverted_index"))
    if abstract:
        lines.append(f"\n**Abstract**:\n{abstract}")

    return "\n".join(lines)


async def get_paper_details(paper_id: str) -> tuple[str, bool]:
    """Fetch complete metadata for a paper by OpenAlex ID, DOI, or arXiv ID."""
    if not paper_id:
        return "Provide a 'paper_id'.", False

    cached = await paper_cache.get_cached_paper(paper_id)
    if cached and isinstance(cached, str):
        return cached, True

    oa_id = to_openalex_id(paper_id)
    try:
        r = await fetch_with_retry(
            f"{OPENALEX_API}/works/{oa_id}",
            params=get_openalex_params(),
            timeout=20,
            max_retries=3,
        )
    except RateLimitError:
        return "OpenAlex rate limit reached. Try again later.", False
    except Exception as e:
        log.warning("OpenAlex details error: %s", e)
        if paper_id.startswith("10."):
            return await get_crossref_details(paper_id)
        return f"Paper lookup error: {str(e)[:200]}", False

    if r.status_code != 200:
        if paper_id.startswith("10."):
            return await get_crossref_details(paper_id)
        return f"Paper not found: {paper_id}", False

    formatted = _format_openalex_details(r.json())
    await paper_cache.set_cached_paper(paper_id, formatted)
    return formatted, True


async def get_crossref_details(doi: str) -> tuple[str, bool]:
    """Fallback details lookup via CrossRef API."""
    try:
        r = await fetch_with_retry(
            f"{CROSSREF_API}/works/{doi}", params={"mailto": MAILTO}, timeout=15, max_retries=3
        )
    except RateLimitError:
        return "CrossRef rate limit reached. Try again later.", False
    except Exception as e:
        log.warning("CrossRef details error: %s", e)
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


async def get_citations(paper_id: str, limit: int = 10) -> tuple[str, bool]:
    """Get referencing and cited-by papers from OpenAlex."""
    if not paper_id:
        return "Provide a 'paper_id'.", False

    oa_id = to_openalex_id(paper_id)
    try:
        r = await fetch_with_retry(
            f"{OPENALEX_API}/works/{oa_id}", params=get_openalex_params(), timeout=20, max_retries=3
        )
    except RateLimitError:
        return "OpenAlex rate limit reached. Try again later.", False
    except Exception as e:
        log.warning("OpenAlex citations error: %s", e)
        return f"Citations lookup error: {str(e)[:200]}", False

    if r.status_code != 200:
        return f"Paper not found: {paper_id}", False

    w = r.json()
    ref_ids = w.get("referenced_works", [])[:limit]
    lines = [
        f"## References ({len(w.get('referenced_works', []))} total, showing {len(ref_ids)})\n"
    ]

    if ref_ids:
        pipe = "|".join(ref_ids)
        try:
            r2 = await fetch_with_retry(
                f"{OPENALEX_API}/works",
                params=get_openalex_params({"filter": f"openalex:{pipe}", "per_page": limit}),
                timeout=20,
                max_retries=2,
            )
            if r2.status_code == 200:
                for rw in r2.json().get("results", []):
                    lines.append(
                        f"- **{rw.get('title', 'Untitled')}** ({rw.get('publication_year', '?')}) [{rw.get('cited_by_count', 0)} cites]"
                    )
        except Exception:
            lines.append("(Could not fetch reference details)")

    lines.append(f"\n## Cited by ({w.get('cited_by_count', 0)} total)\n")
    try:
        r3 = await fetch_with_retry(
            f"{OPENALEX_API}/works",
            params=get_openalex_params(
                {"filter": f"cites:{oa_id}", "sort": "cited_by_count:desc", "per_page": limit}
            ),
            timeout=20,
            max_retries=2,
        )
        if r3.status_code == 200:
            for cw in r3.json().get("results", []):
                lines.append(
                    f"- **{cw.get('title', 'Untitled')}** ({cw.get('publication_year', '?')}) [{cw.get('cited_by_count', 0)} cites]"
                )
    except Exception:
        lines.append("(Could not fetch citing papers)")

    return "\n".join(lines), True


async def get_trending_papers(query: str | None = None, limit: int = 10) -> tuple[str, bool]:
    """Retrieve trending papers from OpenAlex."""
    params = get_openalex_params(
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
            f"{OPENALEX_API}/works", params=params, timeout=20, max_retries=3
        )
    except RateLimitError:
        return "OpenAlex rate limit reached. Try again later.", False
    except Exception as e:
        log.warning("OpenAlex trending error: %s", e)
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
            f"{i}. **{w.get('title', 'Untitled')}** ({w.get('publication_year', '?')})\n   {authors}  |  {w.get('cited_by_count', 0)} citations\n"
        )
    return "\n".join(lines), True


async def get_recommendations(paper_id: str, limit: int = 10) -> tuple[str, bool]:
    """Retrieve related paper recommendations from OpenAlex."""
    if not paper_id:
        return "Provide a 'paper_id'.", False

    oa_id = to_openalex_id(paper_id)
    try:
        r = await fetch_with_retry(
            f"{OPENALEX_API}/works/{oa_id}", params=get_openalex_params(), timeout=20, max_retries=3
        )
    except RateLimitError:
        return "OpenAlex rate limit reached. Try again later.", False
    except Exception as e:
        log.warning("OpenAlex recommend error: %s", e)
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
            params=get_openalex_params({"filter": f"openalex:{pipe}", "per_page": limit}),
            timeout=20,
            max_retries=2,
        )
    except Exception as e:
        log.warning("OpenAlex related works fetch error: %s", e)
        return "Failed to fetch related works.", False

    if r2.status_code != 200:
        return "Failed to fetch related works.", False

    lines = ["## Related Papers\n"]
    for i, w in enumerate(r2.json().get("results", []), 1):
        authors = ", ".join(
            a.get("author", {}).get("display_name", "") for a in (w.get("authorships") or [])[:3]
        )
        lines.append(
            f"{i}. **{w.get('title', 'Untitled')}** ({w.get('publication_year', '?')})\n   {authors}  |  {w.get('cited_by_count', 0)} citations\n"
        )
    return "\n".join(lines), True


async def find_code_implementations(query: str) -> tuple[str, bool]:
    """Search code repositories on Papers With Code."""
    if not query:
        return "Provide a query.", False
    try:
        r = await fetch_with_retry(
            f"{PWC_API}/search/", params={"q": query, "page": 1}, timeout=15, max_retries=3
        )
    except RateLimitError:
        return "Papers With Code rate limit reached. Try again later.", False
    except Exception as e:
        log.warning("Papers With Code search error: %s", e)
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


async def find_datasets_for_topic(query: str) -> tuple[str, bool]:
    """Search machine learning datasets on Papers With Code."""
    if not query:
        return "Provide a query.", False
    try:
        r = await fetch_with_retry(
            f"{PWC_API}/datasets/", params={"q": query, "page": 1}, timeout=15, max_retries=3
        )
    except RateLimitError:
        return "Papers With Code rate limit reached. Try again later.", False
    except Exception as e:
        log.warning("Papers With Code datasets error: %s", e)
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


async def get_author_papers(author_query: str, limit: int = 10) -> tuple[str, bool]:
    """Find papers by a specific author using Semantic Scholar."""
    if not author_query:
        return "Provide an author name in 'query'.", False

    params = {"query": author_query, "limit": 5}
    headers = get_semantic_scholar_headers()

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
        log.warning("Semantic Scholar author search error: %s", e)
        return f"Author search error: {str(e)[:200]}", False

    if r.status_code in (429, 403):
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

    author = authors[0]
    author_id = author.get("authorId")
    author_name = author.get("name", author_query)

    params = {"fields": "paperId,title,year,citationCount,externalIds", "limit": min(limit, 100)}
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
        log.warning("Semantic Scholar author papers error: %s", e)
        return f"Error fetching author papers: {str(e)[:200]}", False

    if r.status_code != 200:
        return f"Error fetching author papers: {r.status_code}", False

    papers = r.json().get("data", [])
    if not papers:
        return f"No papers found for author: {author_name}", True

    papers.sort(key=lambda p: p.get("citationCount", 0), reverse=True)
    papers = papers[:limit]

    lines = [f"## Papers by {author_name}\n"]
    for i, p in enumerate(papers, 1):
        doi = (p.get("externalIds") or {}).get("DOI", "")
        arxiv = (p.get("externalIds") or {}).get("ArXiv", "")
        id_info = f"DOI: {doi}" if doi else ""
        if arxiv:
            id_info += f"  arXiv: {arxiv}" if id_info else f"arXiv: {arxiv}"
        lines.append(
            f"{i}. **{p.get('title', 'Untitled')}** ({p.get('year', '?')})\n   Citations: {p.get('citationCount', 0)}{f'  |  {id_info}' if id_info else ''}\n"
        )
    return "\n".join(lines), True
