"""Web search tool — Brave Search API."""

import os
import httpx
from ..agent.types import ToolSpec


def create_search_tools() -> list[ToolSpec]:
    return [
        ToolSpec(
            name="web_search",
            description=(
                "Search the web using Brave Search API. "
                "Returns titles, URLs, and descriptions of top results. "
                "Use for finding documentation, blog posts, tutorials, etc."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "count": {"type": "integer", "description": "Number of results (default 5, max 20)"},
                },
                "required": ["query"],
            },
            handler=_handle_web_search,
        ),
    ]


async def _handle_web_search(query: str, count: int = 5, **kwargs) -> tuple[str, bool]:
    """Search the web using Brave Search."""
    api_key = os.environ.get("BRAVE_API_KEY")
    if not api_key:
        return "BRAVE_API_KEY not configured. Set it in Settings > Providers.", False

    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {"Accept": "application/json", "X-Subscription-Token": api_key}
    params = {"q": query, "count": min(count, 20)}

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers, params=params, timeout=15)

    if resp.status_code != 200:
        return f"Brave Search error {resp.status_code}: {resp.text[:300]}", False

    data = resp.json()
    results = data.get("web", {}).get("results", [])

    if not results:
        return f"No results for: {query}", True

    lines = []
    for r in results:
        lines.append(f"**{r.get('title', '')}**")
        lines.append(f"  URL: {r.get('url', '')}")
        desc = r.get("description", "")
        if desc:
            lines.append(f"  {desc[:200]}")
        lines.append("")

    return "\n".join(lines), True
