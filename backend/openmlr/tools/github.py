"""GitHub tools — code search, repo listing, file reading."""

import os
import httpx
from ..agent.types import ToolSpec


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
                "Read a file from a GitHub repository. "
                "Provide owner/repo and path within the repo."
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
                    "query": {"type": "string", "description": "Search query (e.g. 'LoRA fine-tune llama')"},
                    "language": {"type": "string", "description": "Filter by language (e.g. 'python')"},
                    "limit": {"type": "integer", "description": "Max results (default 10)"},
                },
                "required": ["query"],
            },
            handler=_handle_find_examples,
        ),
    ]


async def _handle_read_file(
    owner: str, repo: str, path: str, ref: str = "main", **kwargs
) -> tuple[str, bool]:
    """Read a file from GitHub."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}"
    params = {"ref": ref}

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=_headers(), params=params, timeout=30)

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
        numbered = [f"{i+1}: {line}" for i, line in enumerate(lines)]
        output = "\n".join(numbered)
        if len(output) > 50000:
            output = output[:50000] + "\n...[truncated]"
        return output, True

    return data.get("content", "Unable to decode file"), True


async def _handle_list_repos(
    owner: str, sort: str = "stars", limit: int = 20, **kwargs
) -> tuple[str, bool]:
    """List repos for a GitHub user/org."""
    url = f"{GITHUB_API}/users/{owner}/repos"
    params = {"sort": sort, "direction": "desc", "per_page": min(limit, 100)}

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=_headers(), params=params, timeout=30)

    if resp.status_code != 200:
        # Try orgs endpoint
        url = f"{GITHUB_API}/orgs/{owner}/repos"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=_headers(), params=params, timeout=30)
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
    """Search GitHub for code examples."""
    url = f"{GITHUB_API}/search/code"
    q = f"{query} language:{language}"
    params = {"q": q, "per_page": min(limit, 30)}

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=_headers(), params=params, timeout=30)

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
