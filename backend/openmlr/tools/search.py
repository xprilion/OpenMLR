"""Web search tool — Brave Search API with retry logic."""

import logging
import os

from ..agent.types import ToolSpec
from .http_utils import RateLimitError, fetch_with_retry

log = logging.getLogger(__name__)


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
                    "count": {
                        "type": "integer",
                        "description": "Number of results (default 5, max 20)",
                    },
                },
                "required": ["query"],
            },
            handler=_handle_web_search,
        ),
    ]


async def _handle_web_search(query: str, count: int = 5, **kwargs) -> tuple[str, bool]:
    """Search the web using Brave Search with retry logic."""
    api_key = os.environ.get("BRAVE_API_KEY")
    if not api_key:
        return "BRAVE_API_KEY not configured. Set it in Settings > Providers.", False

    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {"Accept": "application/json", "X-Subscription-Token": api_key}
    params = {"q": query, "count": min(count, 20)}

    try:
        resp = await fetch_with_retry(
            url,
            headers=headers,
            params=params,
            timeout=15,
            max_retries=3,
        )
    except RateLimitError:
        return "Brave Search rate limit reached. Try again later.", False
    except Exception as e:
        log.warning(f"Brave Search error: {e}")
        return f"Brave Search error: {str(e)[:200]}", False

    if resp.status_code == 401:
        return "BRAVE_API_KEY is invalid. Check your API key in Settings > Providers.", False
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
