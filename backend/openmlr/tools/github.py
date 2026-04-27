"""GitHub tools — code search, repo listing, file reading, paper implementations."""

import logging
import os

from ..agent.types import ToolSpec
from .http_utils import RateLimitError, fetch_with_retry

log = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


def _headers() -> dict:
    token = os.environ.get("GITHUB_TOKEN")
    h = {"Accept": "application/vnd.github+json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def create_github_tools() -> list[ToolSpec]:
    return [
        ToolSpec(
            name="github_read_file",
            description=(
                "Read a file from a GitHub repository. Provide owner/repo and path within the repo."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "Repository owner (user or org)"},
                    "repo": {"type": "string", "description": "Repository name"},
                    "path": {"type": "string", "description": "File path within the repo"},
                    "ref": {"type": "string", "description": "Branch/tag/commit (default: main)"},
                },
                "required": ["owner", "repo", "path"],
            },
            handler=_handle_read_file,
        ),
        ToolSpec(
            name="github_list_repos",
            description=(
                "List repositories for a GitHub user or organization, "
                "sorted by stars. Useful for finding popular projects."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "GitHub user or org name"},
                    "sort": {
                        "type": "string",
                        "description": "Sort by: stars, forks, updated (default: stars)",
                        "enum": ["stars", "forks", "updated"],
                    },
                    "limit": {"type": "integer", "description": "Max repos to return (default 20)"},
                },
                "required": ["owner"],
            },
            handler=_handle_list_repos,
        ),
        ToolSpec(
            name="github_find_examples",
            description=(
                "Search GitHub for code examples matching a query. "
                "Useful for finding reference implementations, training scripts, etc."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g. 'LoRA fine-tune llama')",
                    },
                    "language": {
                        "type": "string",
                        "description": "Filter by language (e.g. 'python')",
                    },
                    "limit": {"type": "integer", "description": "Max results (default 10)"},
                },
                "required": ["query"],
            },
            handler=_handle_find_examples,
        ),
        ToolSpec(
            name="github_search_repos",
            description=(
                "Search GitHub repositories by keywords, topic, or paper title. "
                "Great for finding ML paper implementations, frameworks, and datasets."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (paper title, method name, topic)",
                    },
                    "topic": {
                        "type": "string",
                        "description": "Filter by topic (e.g. 'machine-learning', 'deep-learning')",
                    },
                    "min_stars": {"type": "integer", "description": "Minimum stars (default 10)"},
                    "sort": {
                        "type": "string",
                        "description": "Sort by: stars, forks, updated, best-match (default: stars)",
                        "enum": ["stars", "forks", "updated", "best-match"],
                    },
                    "limit": {"type": "integer", "description": "Max results (default 10)"},
                },
                "required": ["query"],
            },
            handler=_handle_search_repos,
        ),
        ToolSpec(
            name="github_get_readme",
            description=(
                "Get the README file from a GitHub repository. "
                "Useful for understanding what a repo does before diving into code."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "Repository owner"},
                    "repo": {"type": "string", "description": "Repository name"},
                },
                "required": ["owner", "repo"],
            },
            handler=_handle_get_readme,
        ),
    ]


async def _handle_read_file(
    owner: str, repo: str, path: str, ref: str = "main", **kwargs
) -> tuple[str, bool]:
    """Read a file from GitHub with retry logic."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}"
    params = {"ref": ref}

    try:
        resp = await fetch_with_retry(
            url,
            headers=_headers(),
            params=params,
            timeout=30,
            max_retries=3,
        )
    except RateLimitError:
        return "GitHub rate limit reached. Try again later or add GITHUB_TOKEN.", False
    except Exception as e:
        log.warning(f"GitHub read file error: {e}")
        return f"GitHub API error: {str(e)[:200]}", False

    if resp.status_code == 404:
        return f"File not found: {owner}/{repo}/{path}", False
    if resp.status_code != 200:
        return f"GitHub API error {resp.status_code}: {resp.text[:500]}", False

    data = resp.json()

    if data.get("type") == "dir":
        entries = [f"{'[dir] ' if e['type'] == 'dir' else ''}{e['name']}" for e in data]
        return "\n".join(entries), True

    if data.get("encoding") == "base64":
        import base64

        content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        # Add line numbers
        lines = content.split("\n")
        numbered = [f"{i + 1}: {line}" for i, line in enumerate(lines)]
        output = "\n".join(numbered)
        if len(output) > 50000:
            output = output[:50000] + "\n...[truncated]"
        return output, True

    return data.get("content", "Unable to decode file"), True


async def _handle_list_repos(
    owner: str, sort: str = "stars", limit: int = 20, **kwargs
) -> tuple[str, bool]:
    """List repos for a GitHub user/org with retry logic."""
    url = f"{GITHUB_API}/users/{owner}/repos"
    params = {"sort": sort, "direction": "desc", "per_page": min(limit, 100)}

    try:
        resp = await fetch_with_retry(
            url,
            headers=_headers(),
            params=params,
            timeout=30,
            max_retries=3,
        )
    except RateLimitError:
        return "GitHub rate limit reached. Try again later or add GITHUB_TOKEN.", False
    except Exception as e:
        log.warning(f"GitHub list repos error: {e}")
        return f"GitHub API error: {str(e)[:200]}", False

    if resp.status_code != 200:
        # Try orgs endpoint
        url = f"{GITHUB_API}/orgs/{owner}/repos"
        try:
            resp = await fetch_with_retry(
                url,
                headers=_headers(),
                params=params,
                timeout=30,
                max_retries=2,
            )
        except Exception:
            pass
        if resp.status_code != 200:
            return f"GitHub API error {resp.status_code}", False

    repos = resp.json()[:limit]
    lines = []
    for r in repos:
        stars = r.get("stargazers_count", 0)
        desc = (r.get("description") or "")[:80]
        lines.append(f"  {r['full_name']} ({stars} stars) — {desc}")

    return "\n".join(lines) if lines else "No repositories found.", True


async def _handle_find_examples(
    query: str, language: str = "python", limit: int = 10, **kwargs
) -> tuple[str, bool]:
    """Search GitHub for code examples with retry logic."""
    url = f"{GITHUB_API}/search/code"
    q = f"{query} language:{language}"
    params = {"q": q, "per_page": min(limit, 30)}

    try:
        resp = await fetch_with_retry(
            url,
            headers=_headers(),
            params=params,
            timeout=30,
            max_retries=3,
        )
    except RateLimitError:
        return "GitHub rate limit reached. Try again later or add GITHUB_TOKEN.", False
    except Exception as e:
        log.warning(f"GitHub find examples error: {e}")
        return f"GitHub search error: {str(e)[:200]}", False

    if resp.status_code == 403:
        return "GitHub code search requires authentication. Add GITHUB_TOKEN.", False
    if resp.status_code != 200:
        return f"GitHub search error {resp.status_code}: {resp.text[:300]}", False

    data = resp.json()
    items = data.get("items", [])[:limit]

    if not items:
        return f"No results for: {query}", True

    lines = []
    for item in items:
        repo = item.get("repository", {}).get("full_name", "?")
        path = item.get("path", "?")
        lines.append(f"  {repo}/{path}")
        lines.append(f"    URL: {item.get('html_url', '')}")

    header = f"Found {data.get('total_count', 0)} results (showing {len(items)}):\n"
    return header + "\n".join(lines), True


async def _handle_search_repos(
    query: str,
    topic: str = None,
    min_stars: int = 10,
    sort: str = "stars",
    limit: int = 10,
    **kwargs,
) -> tuple[str, bool]:
    """Search GitHub repositories with retry logic."""
    url = f"{GITHUB_API}/search/repositories"

    # Build query
    q_parts = [query]
    if topic:
        q_parts.append(f"topic:{topic}")
    if min_stars > 0:
        q_parts.append(f"stars:>={min_stars}")

    params = {
        "q": " ".join(q_parts),
        "per_page": min(limit, 30),
    }
    if sort != "best-match":
        params["sort"] = sort
        params["order"] = "desc"

    try:
        resp = await fetch_with_retry(
            url,
            headers=_headers(),
            params=params,
            timeout=30,
            max_retries=3,
        )
    except RateLimitError:
        return "GitHub rate limit reached. Try again later or add GITHUB_TOKEN.", False
    except Exception as e:
        log.warning(f"GitHub search repos error: {e}")
        return f"GitHub search error: {str(e)[:200]}", False

    if resp.status_code != 200:
        return f"GitHub search error {resp.status_code}: {resp.text[:300]}", False

    data = resp.json()
    items = data.get("items", [])[:limit]

    if not items:
        return f"No repositories found for: {query}", True

    lines = [f"Found {data.get('total_count', 0)} repos (showing {len(items)}):\n"]
    for r in items:
        stars = r.get("stargazers_count", 0)
        forks = r.get("forks_count", 0)
        desc = (r.get("description") or "")[:100]
        topics = r.get("topics", [])[:5]

        lines.append(f"**{r['full_name']}** ({stars} stars, {forks} forks)")
        if desc:
            lines.append(f"  {desc}")
        if topics:
            lines.append(f"  Topics: {', '.join(topics)}")
        lines.append(f"  URL: {r.get('html_url', '')}\n")

    return "\n".join(lines), True


async def _handle_get_readme(owner: str, repo: str, **kwargs) -> tuple[str, bool]:
    """Get README from a GitHub repository with retry logic."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}/readme"

    try:
        resp = await fetch_with_retry(
            url,
            headers=_headers(),
            timeout=30,
            max_retries=3,
        )
    except RateLimitError:
        return "GitHub rate limit reached. Try again later or add GITHUB_TOKEN.", False
    except Exception as e:
        log.warning(f"GitHub get readme error: {e}")
        return f"GitHub API error: {str(e)[:200]}", False

    if resp.status_code == 404:
        return f"No README found in {owner}/{repo}", False
    if resp.status_code != 200:
        return f"GitHub API error {resp.status_code}", False

    data = resp.json()

    if data.get("encoding") == "base64":
        import base64

        content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        # Truncate if too long
        if len(content) > 30000:
            content = content[:30000] + "\n\n...[truncated]"
        return f"# README for {owner}/{repo}\n\n{content}", True

    return data.get("content", "Unable to decode README"), True
