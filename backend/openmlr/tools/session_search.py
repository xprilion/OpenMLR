"""Session search tool — search past conversation history."""

import logging

from ..agent.types import ToolSpec

logger = logging.getLogger(__name__)


async def _resolve_search_project_id(session, db, ops) -> int | None:
    """Resolve the project_id from the current session's conversation."""
    conv_id = getattr(session, "conversation_id", None)
    if not conv_id:
        return None
    try:
        conv = await ops.get_conversation_by_id(db, conv_id)
        if conv:
            return conv.project_id
    except Exception:
        pass
    return None


def _format_search_results(results: list[dict]) -> str:
    """Format search results into a human-readable string."""
    lines = [f"Found {len(results)} matching conversation(s):\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"### {i}. {r['title']}")
        if r.get("created_at"):
            lines.append(f"Date: {r['created_at'][:10]}")
        lines.append(f"Snippet: {r['snippet']}")
        lines.append("")
    return "\n".join(lines)


async def _handle_session_search(
    query: str,
    project_only: bool = True,
    limit: int = 10,
    session=None,
    user_id: int | None = None,
    db=None,
    **kwargs,
) -> tuple[str, bool]:
    """Search past conversations for relevant content."""
    if not query:
        return "Error: 'query' is required.", False
    if not user_id or not db:
        return "Session search requires authentication context.", False

    from ..db import operations as ops

    project_id = None
    if project_only and session:
        project_id = await _resolve_search_project_id(session, db, ops)

    try:
        results = await ops.search_conversations(
            db, user_id, query, project_id=project_id, limit=min(limit, 20)
        )
    except Exception as e:
        logger.warning(f"Session search failed: {e}")
        return f"Search error: {e}", False

    if not results:
        scope = "this project" if project_id else "all conversations"
        return f"No matches found for '{query}' in {scope}.", True

    return _format_search_results(results), True


def create_session_search_tool() -> ToolSpec:
    return ToolSpec(
        name="session_search",
        description=(
            "Search past conversations for relevant content.\n\n"
            "Use this to recall discussions, decisions, or findings from previous sessions. "
            "Searches message content using full-text search with relevance ranking.\n\n"
            "Examples:\n"
            "- session_search(query='transformer architectures') — find past discussions\n"
            "- session_search(query='training loss plateau', project_only=false) — search all projects\n\n"
            "Returns conversation titles, dates, and matching text snippets."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (natural language)",
                },
                "project_only": {
                    "type": "boolean",
                    "description": "Search only within the current project (default: true)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return (default: 10, max: 20)",
                },
            },
            "required": ["query"],
        },
        handler=_handle_session_search,
    )
