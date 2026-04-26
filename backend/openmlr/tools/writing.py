"""Paper writing tool — section-by-section academic paper authoring.

Projects are persisted to the database as resources so they survive
across Celery workers and server restarts.
"""

import json
import logging
from datetime import datetime, timezone
from ..agent.types import ToolSpec, AgentEvent
from ..db import operations as ops

logger = logging.getLogger("openmlr.tools.writing")


def _get_session_factory():
    """Get the correct async session factory for the current context."""
    from ..db.engine import _worker_engine, async_session
    eng = _worker_engine.get(None)
    if eng is not None:
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
        return async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    return async_session


# In-memory cache (hydrated from DB on first access per conversation)
_projects: dict[int, dict] = {}  # keyed by conversation_id


async def _load_project(conv_id: int) -> dict | None:
    """Load project from DB if not already cached."""
    if conv_id in _projects:
        return _projects[conv_id]
    
    session_factory = _get_session_factory()
    async with session_factory() as db:
        resource = await ops.get_resource_by_id(db, f"paper-{conv_id}")
        if resource and resource.content:
            # Try to load the project JSON from a special metadata resource
            meta_resource = await ops.get_resource_by_id(db, f"paper-meta-{conv_id}")
            if meta_resource and meta_resource.content:
                try:
                    proj = json.loads(meta_resource.content)
                    _projects[conv_id] = proj
                    return proj
                except json.JSONDecodeError:
                    pass
    return None


async def _save_project(conv_id: int, proj: dict) -> None:
    """Save project metadata and draft to DB."""
    _projects[conv_id] = proj
    
    session_factory = _get_session_factory()
    async with session_factory() as db:
        # Save project metadata (structure, bibliography, etc.)
        await ops.upsert_resource(
            db, conv_id,
            resource_id=f"paper-meta-{conv_id}",
            title=f"Paper Metadata: {proj.get('title', 'Untitled')}",
            resource_type="doc",
            content=json.dumps(proj, default=str),
        )
        # Save the rendered draft as the paper resource
        draft, _ = _get_draft_from_proj(proj)
        await ops.upsert_paper_resource(db, conv_id, proj.get("title", "Paper"), draft)


def create_writing_tool() -> ToolSpec:
    return ToolSpec(
        name="writing",
        description=(
            "Manage academic paper writing. Supports section-by-section writing.\n"
            "Operations: create_project, set_outline, write_section, refine_section, "
            "add_citation, get_draft, list_sections.\n\n"
            "The paper is auto-saved after each write. Users can preview and export "
            "from the Paper tab in the UI — do NOT use the 'write' file tool for papers."
        ),
        parameters={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": [
                        "create_project", "set_outline", "write_section",
                        "refine_section", "add_citation", "get_draft",
                        "list_sections",
                    ],
                    "description": "Which writing operation to perform",
                },
                "project_id": {
                    "type": "string",
                    "description": "Project identifier (auto-generated on create)",
                },
                "title": {
                    "type": "string",
                    "description": "Paper title (for create_project)",
                },
                "outline": {
                    "type": "array",
                    "description": "Section structure: list of {id, title, subsections?} objects",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "title": {"type": "string"},
                            "subsections": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string"},
                                        "title": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                },
                "section_id": {
                    "type": "string",
                    "description": "Section ID to write/refine",
                },
                "content": {
                    "type": "string",
                    "description": "Section content (Markdown)",
                },
                "feedback": {
                    "type": "string",
                    "description": "Feedback for refine_section",
                },
                "citation": {
                    "type": "object",
                    "description": "BibTeX-style citation object",
                    "properties": {
                        "key": {"type": "string"},
                        "type": {"type": "string"},
                        "title": {"type": "string"},
                        "author": {"type": "string"},
                        "year": {"type": "string"},
                        "venue": {"type": "string"},
                        "url": {"type": "string"},
                    },
                    "required": ["key", "title", "author", "year"],
                },
            },
            "required": ["operation"],
        },
        handler=_handle_writing,
    )


async def _handle_writing(
    operation: str,
    project_id: str = None,
    title: str = None,
    outline: list = None,
    section_id: str = None,
    content: str = None,
    feedback: str = None,
    citation: dict = None,
    session=None,
    **kwargs,
) -> tuple[str, bool]:
    """Route writing operations."""
    conv_id = session.conversation_id if session else None

    if operation == "create_project":
        result, ok = _create_project(conv_id, title)
        if ok and conv_id:
            await _save_project(conv_id, _projects[conv_id])
            await _emit_resources(session, conv_id)
        return result, ok

    # For all other operations, try to load existing project
    if conv_id:
        await _load_project(conv_id)

    if operation == "set_outline":
        result, ok = _set_outline(conv_id, outline)
        if ok and conv_id:
            await _save_project(conv_id, _projects[conv_id])
            await _emit_resources(session, conv_id)
        return result, ok
    elif operation == "write_section":
        result, ok = _write_section(conv_id, section_id, content)
        if ok and conv_id:
            await _save_project(conv_id, _projects[conv_id])
            await _emit_resources(session, conv_id)
        return result, ok
    elif operation == "refine_section":
        result, ok = _refine_section(conv_id, section_id, content, feedback)
        if ok and content and conv_id:
            await _save_project(conv_id, _projects[conv_id])
            await _emit_resources(session, conv_id)
        return result, ok
    elif operation == "add_citation":
        result, ok = _add_citation(conv_id, citation)
        if ok and conv_id:
            await _save_project(conv_id, _projects[conv_id])
            await _emit_resources(session, conv_id)
        return result, ok
    elif operation == "get_draft":
        return _get_draft(conv_id)
    elif operation == "list_sections":
        return _list_sections(conv_id)
    else:
        return f"Unknown operation: {operation}", False


def _get_project(conv_id: int) -> dict | None:
    """Get project from in-memory cache."""
    if not conv_id:
        return None
    return _projects.get(conv_id)


def _create_project(conv_id: int, title: str) -> tuple[str, bool]:
    if not title:
        return "Provide a 'title' for the project.", False

    proj = {
        "title": title,
        "outline": [],
        "sections": {},
        "bibliography": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if conv_id:
        _projects[conv_id] = proj
    return f"Created paper project: '{title}'. Use set_outline to define sections.", True


def _set_outline(conv_id: int, outline: list) -> tuple[str, bool]:
    proj = _get_project(conv_id)
    if not proj:
        return "No paper project exists. Call create_project first.", False
    if not outline:
        return "Provide an 'outline' array.", False

    proj["outline"] = outline
    lines = [f"Outline set for '{proj['title']}':\n"]
    for sec in outline:
        lines.append(f"  {sec.get('id', '?')}. {sec.get('title', 'Untitled')}")
        for sub in sec.get("subsections", []):
            lines.append(f"    {sub.get('id', '')}. {sub.get('title', '')}")
    return "\n".join(lines), True


def _write_section(conv_id: int, section_id: str, content: str) -> tuple[str, bool]:
    proj = _get_project(conv_id)
    if not proj:
        return "No paper project exists. Call create_project first.", False
    if not section_id or not content:
        return "Provide both 'section_id' and 'content'.", False

    proj["sections"][section_id] = content
    written = len(proj["sections"])
    total = _count_sections(proj["outline"])
    return (
        f"Section '{section_id}' written ({len(content)} chars). "
        f"Progress: {written}/{total} sections. Paper auto-saved."
    ), True


def _refine_section(conv_id: int, section_id: str, content: str, feedback: str) -> tuple[str, bool]:
    proj = _get_project(conv_id)
    if not proj:
        return "No paper project exists.", False
    if not section_id:
        return "Provide 'section_id' to refine.", False

    if content:
        proj["sections"][section_id] = content
        return f"Section '{section_id}' refined ({len(content)} chars). Paper auto-saved.", True
    else:
        existing = proj["sections"].get(section_id, "")
        return (
            f"Current content of '{section_id}' ({len(existing)} chars):\n\n"
            f"{existing[:5000]}\n\n"
            f"Feedback: {feedback or 'none provided'}\n"
            f"Provide updated 'content' to apply refinement."
        ), True


def _add_citation(conv_id: int, citation: dict) -> tuple[str, bool]:
    proj = _get_project(conv_id)
    if not proj:
        return "No paper project exists.", False
    if not citation:
        return "Provide a 'citation' object.", False

    proj["bibliography"].append(citation)
    key = citation.get("key", f"ref{len(proj['bibliography'])}")
    return f"Added citation [@{key}]. Bibliography: {len(proj['bibliography'])} entries.", True


def _get_draft(conv_id: int) -> tuple[str, bool]:
    proj = _get_project(conv_id)
    if not proj:
        return "No paper project exists.", False
    return _get_draft_from_proj(proj)


def _get_draft_from_proj(proj: dict) -> tuple[str, bool]:
    """Generate the full markdown draft from a project dict."""
    lines = [f"# {proj['title']}\n"]

    if proj.get("outline"):
        for sec in proj["outline"]:
            sid = sec.get("id", "")
            title = sec.get("title", "")
            content = proj["sections"].get(sid, "[Not yet written]")
            lines.append(f"\n## {title}\n\n{content}")

            for sub in sec.get("subsections", []):
                sub_id = sub.get("id", "")
                sub_title = sub.get("title", "")
                sub_content = proj["sections"].get(sub_id, "[Not yet written]")
                lines.append(f"\n### {sub_title}\n\n{sub_content}")
    else:
        for sid, content in proj.get("sections", {}).items():
            lines.append(f"\n## {sid}\n\n{content}")

    if proj.get("bibliography"):
        lines.append("\n## References\n")
        for c in proj["bibliography"]:
            key = c.get("key", "?")
            author = c.get("author", "Unknown")
            title = c.get("title", "Untitled")
            year = c.get("year", "?")
            lines.append(f"[{key}] {author}. \"{title}\". {year}.")

    return "\n".join(lines), True


def _list_sections(conv_id: int) -> tuple[str, bool]:
    proj = _get_project(conv_id)
    if not proj:
        return "No paper project exists.", False

    lines = [f"## Sections for '{proj['title']}'\n"]
    if proj.get("outline"):
        for sec in proj["outline"]:
            sid = sec.get("id", "")
            written = "done" if sid in proj["sections"] else "pending"
            char_count = len(proj["sections"].get(sid, ""))
            lines.append(f"  [{written}] {sid}: {sec.get('title', '')} ({char_count} chars)")
    else:
        lines.append("No outline defined. Use set_outline first.")
    return "\n".join(lines), True


async def _emit_resources(session, conv_id: int) -> None:
    """Emit resources update event to frontend."""
    if not session:
        return
    session_factory = _get_session_factory()
    async with session_factory() as db:
        resources = await ops.get_conversation_resources(db, conv_id)
        res_list = [
            {"title": r.title, "url": r.url or "", "type": r.type, "id": r.resource_id}
            for r in resources
        ]
        await session.emit(AgentEvent(
            event_type="resources_update",
            data={"resources": res_list},
        ))


def _count_sections(outline: list) -> int:
    count = len(outline)
    for sec in outline:
        count += len(sec.get("subsections", []))
    return count
