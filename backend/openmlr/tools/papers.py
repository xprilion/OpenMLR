"""Papers tool — OpenAlex, CrossRef, ArXiv, Papers With Code.

No Semantic Scholar dependency. All APIs are free with no approval forms.
OpenAlex: polite pool (just needs mailto). CrossRef/ArXiv/PWC: fully open.
"""

import os
import re
import httpx
from typing import Optional
from ..agent.types import ToolSpec

OPENALEX_API = "https://api.openalex.org"
CROSSREF_API = "https://api.crossref.org"
ARXIV_API = "http://export.arxiv.org/api/query"
AR5IV_BASE = "https://ar5iv.labs.arxiv.org/html"
PWC_API = "https://paperswithcode.com/api/v1"

# OpenAlex polite pool — just an email, no key needed
MAILTO = os.environ.get("OPENALEX_EMAIL", "openmlr@example.com")


def _oa_params(extra: dict = None) -> dict:
    """OpenAlex common params (polite pool via mailto)."""
    p = {"mailto": MAILTO}
    if extra:
        p.update(extra)
    return p


def create_papers_tool() -> ToolSpec:
    return ToolSpec(
        name="papers",
        description=(
            "Search and read academic papers using OpenAlex, CrossRef, and ArXiv. "
            "Operations: search, trending, details, read_paper, citations, "
            "recommend, find_code, find_datasets."
        ),
        parameters={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": [
                        "search", "trending", "details", "read_paper",
                        "citations", "recommend", "find_code", "find_datasets",
                    ],
                    "description": "Which operation to perform",
                },
                "query": {
                    "type": "string",
                    "description": "Search query or paper topic",
                },
                "paper_id": {
                    "type": "string",
                    "description": "Paper ID: OpenAlex ID (W...), DOI (10.xxx/...), or arXiv ID (2301.12345)",
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
    budget = session.config.paper_search_budget if session and hasattr(session, 'config') else _BUDGET_DEFAULT
    if count >= budget:
        return False, f"Search budget exhausted ({count}/{budget} calls). Ask the user before continuing."
    return True, ""

def _increment_budget(session=None):
    key = id(session) if session else 0
    _search_counts[key] = _search_counts.get(key, 0) + 1

def _get_budget_info(session=None) -> dict:
    key = id(session) if session else 0
    budget = session.config.paper_search_budget if session and hasattr(session, 'config') else _BUDGET_DEFAULT
    return {"used": _search_counts.get(key, 0), "max": budget}


async def _handle_papers(
    operation: str,
    query: str = None,
    paper_id: str = None,
    section: str = None,
    year_from: int = None,
    year_to: int = None,
    limit: int = 10,
    session=None,
    **kwargs,
) -> tuple[str, bool]:
    # Budget check for API-calling operations
    api_ops = {"search", "trending", "details", "citations", "recommend", "find_code", "find_datasets"}
    if operation in api_ops:
        ok, msg = _check_budget(session)
        if not ok:
            return msg, False
        _increment_budget(session)
        # Emit budget update
        if session:
            from ..agent.types import AgentEvent
            await session.emit(AgentEvent(
                event_type="search_budget",
                data=_get_budget_info(session),
            ))

    handlers = {
        "search": lambda: _search(query, year_from, year_to, limit),
        "trending": lambda: _trending(query, limit),
        "details": lambda: _details(paper_id),
        "read_paper": lambda: _read_paper(paper_id, section),
        "citations": lambda: _citations(paper_id, limit),
        "recommend": lambda: _recommend(paper_id, limit),
        "find_code": lambda: _find_code(paper_id or query),
        "find_datasets": lambda: _find_datasets(paper_id or query),
    }
    handler = handlers.get(operation)
    if not handler:
        return f"Unknown operation: {operation}", False
    try:
        return await handler()
    except Exception as e:
        return f"Papers tool error ({operation}): {str(e)}", False


# ── Search (OpenAlex) ────────────────────────────────────

async def _search(query: str, year_from: int = None, year_to: int = None, limit: int = 10) -> tuple[str, bool]:
    if not query:
        return "Provide a 'query' for search.", False

    params = _oa_params({"search": query, "per_page": min(limit, 50)})

    filters = []
    if year_from:
        filters.append(f"from_publication_date:{year_from}-01-01")
    if year_to:
        filters.append(f"to_publication_date:{year_to}-12-31")
    if filters:
        params["filter"] = ",".join(filters)

    async with httpx.AsyncClient() as c:
        r = await c.get(f"{OPENALEX_API}/works", params=params, timeout=20)

    if r.status_code != 200:
        return f"OpenAlex error {r.status_code}: {r.text[:300]}", False

    works = r.json().get("results", [])
    if not works:
        return f"No papers found for: {query}", True

    total = r.json().get("meta", {}).get("count", len(works))
    lines = [f"Found {total} papers for '{query}':\n"]
    for i, w in enumerate(works, 1):
        authors = ", ".join(a.get("author", {}).get("display_name", "") for a in (w.get("authorships") or [])[:3])
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


# ── Trending (OpenAlex) ──────────────────────────────────

async def _trending(query: str = None, limit: int = 10) -> tuple[str, bool]:
    params = _oa_params({
        "sort": "cited_by_count:desc",
        "filter": "from_publication_date:2024-01-01",
        "per_page": min(limit, 50),
    })
    if query:
        params["search"] = query

    async with httpx.AsyncClient() as c:
        r = await c.get(f"{OPENALEX_API}/works", params=params, timeout=20)

    if r.status_code != 200:
        return f"OpenAlex error {r.status_code}", False

    works = r.json().get("results", [])
    if not works:
        return "No trending papers found.", True

    lines = [f"Trending papers{f' on: {query}' if query else ''}:\n"]
    for i, w in enumerate(works, 1):
        authors = ", ".join(a.get("author", {}).get("display_name", "") for a in (w.get("authorships") or [])[:3])
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

    async with httpx.AsyncClient() as c:
        r = await c.get(f"{OPENALEX_API}/works/{oa_id}", params=_oa_params(), timeout=20)

    if r.status_code != 200:
        # Fallback to CrossRef for DOI
        if paper_id.startswith("10."):
            return await _crossref_details(paper_id)
        return f"Paper not found: {paper_id}", False

    w = r.json()
    authors = ", ".join(a.get("author", {}).get("display_name", "") for a in (w.get("authorships") or []))
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
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{CROSSREF_API}/works/{doi}", params={"mailto": MAILTO}, timeout=15)

    if r.status_code != 200:
        return f"CrossRef lookup failed for DOI: {doi}", False

    w = r.json().get("message", {})
    title = (w.get("title") or ["Untitled"])[0]
    authors = ", ".join(f"{a.get('given', '')} {a.get('family', '')}" for a in (w.get("author") or []))
    year = (w.get("published-print") or w.get("published-online") or {}).get("date-parts", [[None]])[0][0]

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
    async with httpx.AsyncClient(follow_redirects=True) as c:
        r = await c.get(url, timeout=30)

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
        toc.append(f"\nUse read_paper with section=<number or name> to read a section.")
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
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{OPENALEX_API}/works/{oa_id}", params=_oa_params(), timeout=20)

    if r.status_code != 200:
        return f"Paper not found: {paper_id}", False

    w = r.json()
    ref_ids = w.get("referenced_works", [])[:limit]
    lines = [f"## References ({len(w.get('referenced_works', []))} total, showing {len(ref_ids)})\n"]

    # Batch-fetch referenced works
    if ref_ids:
        pipe = "|".join(ref_ids)
        async with httpx.AsyncClient() as c:
            r2 = await c.get(
                f"{OPENALEX_API}/works",
                params=_oa_params({"filter": f"openalex:{pipe}", "per_page": limit}),
                timeout=20,
            )
        if r2.status_code == 200:
            for rw in r2.json().get("results", []):
                lines.append(
                    f"- **{rw.get('title', 'Untitled')}** ({rw.get('publication_year', '?')}) "
                    f"[{rw.get('cited_by_count', 0)} cites]"
                )

    # Cited-by via filter
    lines.append(f"\n## Cited by ({w.get('cited_by_count', 0)} total)\n")
    async with httpx.AsyncClient() as c:
        r3 = await c.get(
            f"{OPENALEX_API}/works",
            params=_oa_params({
                "filter": f"cites:{oa_id}",
                "sort": "cited_by_count:desc",
                "per_page": limit,
            }),
            timeout=20,
        )
    if r3.status_code == 200:
        for cw in r3.json().get("results", []):
            lines.append(
                f"- **{cw.get('title', 'Untitled')}** ({cw.get('publication_year', '?')}) "
                f"[{cw.get('cited_by_count', 0)} cites]"
            )

    return "\n".join(lines), True


# ── Recommendations (OpenAlex related_works) ──────────────

async def _recommend(paper_id: str, limit: int = 10) -> tuple[str, bool]:
    if not paper_id:
        return "Provide a 'paper_id'.", False

    oa_id = _to_openalex_id(paper_id)

    async with httpx.AsyncClient() as c:
        r = await c.get(f"{OPENALEX_API}/works/{oa_id}", params=_oa_params(), timeout=20)

    if r.status_code != 200:
        return f"Paper not found: {paper_id}", False

    related = r.json().get("related_works", [])[:limit]
    if not related:
        return "No related works found.", True

    pipe = "|".join(related)
    async with httpx.AsyncClient() as c:
        r2 = await c.get(
            f"{OPENALEX_API}/works",
            params=_oa_params({"filter": f"openalex:{pipe}", "per_page": limit}),
            timeout=20,
        )

    if r2.status_code != 200:
        return "Failed to fetch related works.", False

    lines = ["## Related Papers\n"]
    for i, w in enumerate(r2.json().get("results", []), 1):
        authors = ", ".join(a.get("author", {}).get("display_name", "") for a in (w.get("authorships") or [])[:3])
        lines.append(
            f"{i}. **{w.get('title', 'Untitled')}** ({w.get('publication_year', '?')})\n"
            f"   {authors}  |  {w.get('cited_by_count', 0)} citations\n"
        )
    return "\n".join(lines), True


# ── Find Code (Papers With Code) ─────────────────────────

async def _find_code(query: str) -> tuple[str, bool]:
    if not query:
        return "Provide a query.", False

    async with httpx.AsyncClient() as c:
        r = await c.get(f"{PWC_API}/search/", params={"q": query, "page": 1}, timeout=15)

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

    async with httpx.AsyncClient() as c:
        r = await c.get(f"{PWC_API}/datasets/", params={"q": query, "page": 1}, timeout=15)

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


def _extract_arxiv_id(text: str) -> Optional[str]:
    match = re.search(r'(\d{4}\.\d{4,5}(?:v\d+)?)', text)
    if match:
        return match.group(1)
    match = re.search(r'arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5}(?:v\d+)?)', text)
    if match:
        return match.group(1)
    return None


def _extract_arxiv_from_ids(ids: dict) -> Optional[str]:
    """Extract arxiv ID from OpenAlex ids dict."""
    openalex_id = ids.get("openalex", "")
    doi = ids.get("doi", "")
    if "arXiv" in doi:
        return _extract_arxiv_id(doi)
    return None


def _reconstruct_abstract(inverted_index: dict) -> Optional[str]:
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
        sections.append({
            "title": "Abstract",
            "text": abstract.get_text(strip=True).replace("Abstract", "", 1).strip(),
            "level": 2,
        })

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


def _find_section(sections: list[dict], query: str) -> Optional[dict]:
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
