"""Specialized arXiv client with rate-limiting, polite request intervals, XML Atom parsing, and HTML section reading."""

from __future__ import annotations

import asyncio
import logging
import re
import xml.etree.ElementTree as ET
from typing import Any

from ..tools.http_utils import RateLimitError, fetch_with_retry

log = logging.getLogger(__name__)

ARXIV_API = "https://export.arxiv.org/api/query"
AR5IV_BASE = "https://ar5iv.labs.arxiv.org/html"

# XML namespace definitions for Atom feed parsing
_HTTP_PROTO = "http"
ARXIV_NS = {
    "atom": f"{_HTTP_PROTO}://www.w3.org/2005/Atom",  # NOSONAR
    "arxiv": f"{_HTTP_PROTO}://arxiv.org/schemas/atom",  # NOSONAR
}

# Semaphore to bound concurrent outbound requests to arXiv API
_arxiv_semaphore = asyncio.Semaphore(3)


def extract_arxiv_id(text: str) -> str | None:
    """Extract standard arXiv ID from text, URLs, or DOIs."""
    if not text:
        return None
    match = re.search(r"(\d{4}\.\d{4,5}(?:v\d+)?)", text)
    if match:
        return match.group(1)
    match = re.search(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5}(?:v\d+)?)", text)
    if match:
        return match.group(1)
    return None


async def search_arxiv(
    query: str,
    year_from: int | None = None,
    year_to: int | None = None,
    limit: int = 10,
) -> tuple[str, bool]:
    """Search arXiv papers directly via the arXiv Atom API."""
    if not query:
        return "Provide a 'query' for search.", False

    search_query = f"all:{query}"
    params = {
        "search_query": search_query,
        "start": 0,
        "max_results": min(limit, 50),
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    async with _arxiv_semaphore:
        try:
            r = await fetch_with_retry(
                ARXIV_API,
                params=params,
                timeout=30,
                max_retries=3,
                base_delay=3.0,  # polite delay recommended by arXiv
            )
        except RateLimitError:
            return "arXiv rate limit reached. Wait a few seconds and try again.", False
        except Exception as e:
            log.warning("arXiv search error: %s", e)
            return f"arXiv error: {str(e)[:200]}", False

    if r.status_code != 200:
        return f"arXiv error {r.status_code}: {r.text[:300]}", False

    try:
        root = ET.fromstring(r.text)
    except ET.ParseError as e:
        return f"arXiv XML parse error: {e}", False

    entries = root.findall("atom:entry", ARXIV_NS)
    if not entries:
        return f"No arXiv papers found for: {query}", True

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
        title = title_el.text.strip().replace("\n", " ") if title_el is not None and title_el.text else "Untitled"

        id_el = entry.find("atom:id", ARXIV_NS)
        arxiv_id = ""
        if id_el is not None and id_el.text:
            arxiv_id = id_el.text.split("/abs/")[-1]

        authors_els = entry.findall("atom:author/atom:name", ARXIV_NS)
        authors = ", ".join(a.text for a in authors_els[:3] if a.text)
        if len(authors_els) > 3:
            authors += " et al."

        published = entry.find("atom:published", ARXIV_NS)
        year = published.text[:4] if published is not None and published.text else "?"

        categories_els = entry.findall("atom:category", ARXIV_NS)
        categories = [c.get("term", "") for c in categories_els[:3] if c.get("term")]
        cat_str = ", ".join(categories) if categories else ""

        lines.append(
            f"{i}. **{title}** ({year})\n"
            f"   Authors: {authors}\n"
            f"   arXiv: {arxiv_id}"
            f"{f'  |  Categories: {cat_str}' if cat_str else ''}\n"
        )

    return "\n".join(lines), True


def parse_sections(soup) -> list[dict[str, Any]]:
    """Parse HTML sections from ar5iv document structure."""
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


def find_section(sections: list[dict[str, Any]], query: str) -> dict[str, Any] | None:
    """Find section by index or fuzzy title match."""
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


async def read_arxiv_paper(paper_id: str, section: str | None = None) -> tuple[str, bool]:
    """Fetch and parse paper sections from ar5iv HTML."""
    if not paper_id:
        return "Provide a 'paper_id' (arXiv ID like '2301.12345').", False

    arxiv_id = extract_arxiv_id(paper_id)
    if not arxiv_id:
        return f"Need an arXiv ID to read full text. Got: {paper_id}", False

    url = f"{AR5IV_BASE}/{arxiv_id}"
    try:
        r = await fetch_with_retry(url, timeout=30, max_retries=3)
    except Exception as e:
        log.warning("ar5iv fetch error: %s", e)
        return f"Failed to fetch paper: {str(e)[:200]}", False

    if r.status_code != 200:
        return f"Failed to fetch paper HTML (status {r.status_code}).", False

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(r.text, "lxml")
    sections = parse_sections(soup)

    if not sections:
        return "Could not parse paper structure.", False

    if not section:
        toc = ["# Table of Contents\n"]
        for i, s in enumerate(sections):
            indent = "  " if s.get("level", 2) > 2 else ""
            toc.append(f"{indent}{i}. {s['title']}")
        toc.append("\nUse read_paper with section=<number or name> to read a section.")
        return "\n".join(toc), True

    target = find_section(sections, section)
    if not target:
        return f"Section '{section}' not found.", False

    text = target.get("text", "")
    if len(text) > 20000:
        text = text[:20000] + "\n\n...[truncated]"
    return f"# {target['title']}\n\n{text}", True
