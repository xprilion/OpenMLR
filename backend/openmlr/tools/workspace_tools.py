"""Workspace tools — project workspace operations for the agent.

Provides tools for the agent to interact with the project workspace:
- View workspace status and file tree
- Search files in workspace
- Save research notes
- Read/update the knowledge graph
- Log tool failures
"""

import json
import logging
from contextvars import ContextVar

from ..agent.types import ToolSpec
from ..workspace.knowledge import KnowledgeGraph
from ..workspace.persistence import WorkspacePersistence

log = logging.getLogger(__name__)

# Per-async-context workspace references — safe for concurrent sessions.
# ContextVar ensures each request/task has its own workspace context,
# preventing cross-user contamination in the async server.
_workspace_path_var: ContextVar[str | None] = ContextVar("workspace_path", default=None)
_persistence_var: ContextVar[WorkspacePersistence | None] = ContextVar("persistence", default=None)
_knowledge_var: ContextVar[KnowledgeGraph | None] = ContextVar("knowledge", default=None)


def set_workspace_context(workspace_path: str | None) -> None:
    """Set the project workspace path for the current async context."""
    _workspace_path_var.set(workspace_path)
    if workspace_path:
        _persistence_var.set(WorkspacePersistence(workspace_path))
        _knowledge_var.set(KnowledgeGraph(workspace_path))
    else:
        _persistence_var.set(None)
        _knowledge_var.set(None)


def _require_workspace() -> tuple[WorkspacePersistence, KnowledgeGraph]:
    """Ensure workspace is configured for the current context."""
    persistence = _persistence_var.get()
    knowledge = _knowledge_var.get()
    if not persistence or not knowledge:
        raise ValueError("No project workspace is active. Create or select a project first.")
    return persistence, knowledge


async def _handle_workspace(
    operation: str,
    # workspace_status
    # workspace_search
    query: str = "",
    # workspace_note
    topic: str = "",
    content: str = "",
    # knowledge_add
    entity_id: str = "",
    entity_type: str = "",
    label: str = "",
    properties: str = "",
    # knowledge_relate
    source_id: str = "",
    target_id: str = "",
    relationship: str = "",
    # knowledge_query
    # knowledge_summary
    session=None,
    **kwargs,
) -> tuple[str, bool]:
    """Handle workspace tool operations."""
    try:
        if operation == "status":
            return await _workspace_status(session)
        elif operation == "search":
            return await _workspace_search(query)
        elif operation == "note":
            return await _workspace_note(topic, content, session)
        elif operation == "knowledge_add":
            return await _knowledge_add(entity_id, entity_type, label, properties, session)
        elif operation == "knowledge_relate":
            return await _knowledge_relate(source_id, target_id, relationship, session)
        elif operation == "knowledge_query":
            return await _knowledge_query(query)
        elif operation == "knowledge_summary":
            return await _knowledge_summary()
        elif operation == "recent_failures":
            return await _recent_failures()
        else:
            return f"Unknown workspace operation: {operation}", False
    except ValueError as e:
        return str(e), False
    except Exception as e:
        log.warning(f"Workspace tool error ({operation}): {e}")
        return "Workspace operation failed. Check server logs for details.", False


async def _workspace_status(session=None) -> tuple[str, bool]:
    """Get workspace status and summary."""
    persistence, knowledge = _require_workspace()

    summary = persistence.get_workspace_summary()
    kg_summary = knowledge.get_summary()

    lines = [
        "## Workspace Status",
        "",
        f"**Papers:** {summary['papers']}",
        f"**Research notes:** {summary['research_notes']}",
        f"**Search results saved:** {summary['search_results']}",
        f"**Code files:** {summary['code_files']}",
        f"**Experiments logged:** {summary['experiments']}",
        f"**Tool failures logged:** {summary['tool_failures']}",
        "",
        "### Knowledge Graph",
        f"Entities: {kg_summary['total_nodes']} | Relationships: {kg_summary['total_edges']}",
    ]

    if kg_summary.get("type_counts"):
        lines.append(
            "Types: " + ", ".join(f"{t}: {c}" for t, c in kg_summary["type_counts"].items())
        )

    if summary.get("recent_tool_failures"):
        lines.append("\n### Recent Tool Failures")
        for f in summary["recent_tool_failures"]:
            lines.append(f"- **{f['tool']}**: {f['error'][:100]}")

    state = persistence.get_state()
    if state.get("key_findings"):
        lines.append("\n### Key Findings")
        for finding in state["key_findings"][-5:]:
            lines.append(f"- {finding}")

    if state.get("open_questions"):
        lines.append("\n### Open Questions")
        for q in state["open_questions"][-5:]:
            lines.append(f"- {q}")

    return "\n".join(lines), True


async def _workspace_search(query: str) -> tuple[str, bool]:
    """Search files in workspace by name or content."""
    import os

    persistence, _ = _require_workspace()

    if not query:
        return "Please provide a search query.", False

    results = []
    query_lower = query.lower()
    ws_path = persistence.workspace_path

    # Limits to prevent DoS from deeply nested or very large workspaces
    max_depth = 8
    max_files_scanned = 5000
    files_scanned = 0
    ws_path_str = str(ws_path)

    for dirpath, dirnames, filenames in os.walk(ws_path):
        # Enforce depth limit
        depth = dirpath[len(ws_path_str) :].count(os.sep)
        if depth >= max_depth:
            dirnames.clear()  # Don't descend further
            continue

        for fname in filenames:
            if files_scanned >= max_files_scanned:
                break
            if fname.startswith("."):
                continue

            files_scanned += 1
            fpath = os.path.join(dirpath, fname)
            rel_path = os.path.relpath(fpath, ws_path)

            # Name match
            if query_lower in fname.lower():
                results.append(f"- **{rel_path}** (name match)")
                continue

            # Content match (text files only, skip large files)
            try:
                if os.path.getsize(fpath) > 500_000:
                    continue
                with open(fpath, encoding="utf-8", errors="ignore") as f:
                    content = f.read(10000)
                if query_lower in content.lower():
                    results.append(f"- **{rel_path}** (content match)")
            except Exception:
                continue

        if files_scanned >= max_files_scanned:
            break

    if not results:
        return f"No files found matching '{query}'.", True

    return f"## Search Results for '{query}'\n\n" + "\n".join(results[:30]), True


async def _workspace_note(topic: str, content: str, session=None) -> tuple[str, bool]:
    """Save a research note to the workspace."""
    persistence, _ = _require_workspace()

    if not topic or not content:
        return "Please provide both 'topic' and 'content' for the note.", False

    conv_uuid = getattr(session, "conversation_uuid", None) if session else None
    filepath = persistence.save_research_note(topic, content, conv_uuid)

    return f"Research note saved: {filepath.name}", True


async def _knowledge_add(
    entity_id: str,
    entity_type: str,
    label: str,
    properties: str,
    session=None,
) -> tuple[str, bool]:
    """Add an entity to the knowledge graph."""
    _, knowledge = _require_workspace()

    if not entity_id or not entity_type or not label:
        return "Please provide entity_id, entity_type, and label.", False

    props = {}
    if properties:
        try:
            props = json.loads(properties)
        except json.JSONDecodeError:
            return "Invalid JSON in properties.", False

    conv_uuid = getattr(session, "conversation_uuid", None) if session else None
    is_new = knowledge.add_entity(entity_id, entity_type, label, props, conv_uuid)
    knowledge.save()

    action = "Added" if is_new else "Updated"
    return f"{action} entity: {label} ({entity_type})", True


async def _knowledge_relate(
    source_id: str,
    target_id: str,
    relationship: str,
    session=None,
) -> tuple[str, bool]:
    """Add a relationship between entities in the knowledge graph."""
    _, knowledge = _require_workspace()

    if not source_id or not target_id or not relationship:
        return "Please provide source_id, target_id, and relationship.", False

    conv_uuid = getattr(session, "conversation_uuid", None) if session else None
    success = knowledge.add_relationship(
        source_id, target_id, relationship, conversation_uuid=conv_uuid
    )
    if success:
        knowledge.save()
        return f"Added relationship: {source_id} --[{relationship}]--> {target_id}", True
    return "Failed to add relationship. Ensure both entities exist.", False


async def _knowledge_query(query: str) -> tuple[str, bool]:
    """Search the knowledge graph."""
    _, knowledge = _require_workspace()

    if not query:
        return "Please provide a search query.", False

    results = knowledge.search_entities(query)
    if not results:
        return f"No entities found matching '{query}'.", True

    lines = [f"## Knowledge Graph: '{query}'\n"]
    for entity in results:
        lines.append(f"- **{entity.get('label', entity['id'])}** ({entity.get('type', '?')})")
        neighbors = knowledge.get_neighbors(entity["id"])
        for n in neighbors[:5]:
            lines.append(f"  - {n.get('relationship', '?')} -> {n.get('label', n['id'])}")

    return "\n".join(lines), True


async def _knowledge_summary() -> tuple[str, bool]:
    """Get a full knowledge graph summary for context."""
    _, knowledge = _require_workspace()
    context = knowledge.get_context_for_conversation()
    if not context:
        return "Knowledge graph is empty.", True
    return context, True


async def _recent_failures() -> tuple[str, bool]:
    """Get recent tool failure logs."""
    persistence, _ = _require_workspace()
    failures = persistence.get_recent_failures(limit=10)
    if not failures:
        return "No recent tool failures.", True

    lines = ["## Recent Tool Failures\n"]
    for f in failures:
        lines.append(f"- **{f['tool']}** ({f.get('timestamp', '?')}): {f['error'][:200]}")
    return "\n".join(lines), True


def create_workspace_tools() -> list[ToolSpec]:
    """Create workspace tool specs."""
    return [
        ToolSpec(
            name="workspace",
            description=(
                "Interact with the project workspace — persistent storage for research data, "
                "knowledge graph, notes, and logs.\n\n"
                "Operations:\n"
                "- status: View workspace summary (file counts, knowledge graph size, recent failures)\n"
                "- search: Search files by name or content (requires 'query')\n"
                "- note: Save a research note (requires 'topic' and 'content')\n"
                "- knowledge_add: Add entity to knowledge graph (requires 'entity_id', 'entity_type', 'label'; optional 'properties' as JSON)\n"
                "- knowledge_relate: Add relationship (requires 'source_id', 'target_id', 'relationship')\n"
                "- knowledge_query: Search knowledge graph (requires 'query')\n"
                "- knowledge_summary: Get full knowledge graph context\n"
                "- recent_failures: View recent tool/API failure logs\n\n"
                "Entity types: paper, concept, method, dataset, finding, question, experiment, tool, author, code_artifact\n"
                "Relationship types: cites, implements, evaluates_on, proposes, introduces, relates_to, answers, depends_on, uses, produces, contradicts, extends"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": [
                            "status",
                            "search",
                            "note",
                            "knowledge_add",
                            "knowledge_relate",
                            "knowledge_query",
                            "knowledge_summary",
                            "recent_failures",
                        ],
                        "description": "The workspace operation to perform.",
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query (for search, knowledge_query).",
                    },
                    "topic": {"type": "string", "description": "Note topic (for note)."},
                    "content": {"type": "string", "description": "Note content (for note)."},
                    "entity_id": {
                        "type": "string",
                        "description": "Entity ID (for knowledge_add).",
                    },
                    "entity_type": {
                        "type": "string",
                        "description": "Entity type (for knowledge_add).",
                    },
                    "label": {"type": "string", "description": "Entity label (for knowledge_add)."},
                    "properties": {
                        "type": "string",
                        "description": "JSON string of additional properties (for knowledge_add).",
                    },
                    "source_id": {
                        "type": "string",
                        "description": "Source entity ID (for knowledge_relate).",
                    },
                    "target_id": {
                        "type": "string",
                        "description": "Target entity ID (for knowledge_relate).",
                    },
                    "relationship": {
                        "type": "string",
                        "description": "Relationship type (for knowledge_relate).",
                    },
                },
                "required": ["operation"],
            },
            handler=_handle_workspace,
        ),
    ]
