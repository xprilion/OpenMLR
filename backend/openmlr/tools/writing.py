"""Paper writing tool — section-by-section academic paper authoring."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from ..agent.types import AgentEvent, ToolSpec
from ..db import operations as ops
from ..services.bibtex_validator import validate_bibtex

logger = logging.getLogger("openmlr.tools.writing")


def _get_session_factory():
    """Get the correct async session factory for the current context."""
    from ..db.engine import _worker_engine, async_session

    eng = _worker_engine.get(None)
    if eng is not None:
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

        return async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    return async_session


_projects: dict[int, dict] = {}


async def _load_project(conv_id: int) -> dict | None:
    if conv_id in _projects:
        return _projects[conv_id]

    session_factory = _get_session_factory()
    async with session_factory() as db:
        resource = await ops.get_resource_by_id(db, f"paper-{conv_id}")
        if resource and resource.content:
            meta_resource = await ops.get_resource_by_id(db, f"paper-meta-{conv_id}")
            if meta_resource and meta_resource.content:
                try:
                    proj = json.loads(meta_resource.content)
                    _projects[conv_id] = proj
                    return proj
                except json.JSONDecodeError:
                    pass
    return None


async def _get_author_info(db, conv_id: int) -> dict | None:
    conv = await ops.get_conversation_by_id(db, conv_id)
    if not conv or not conv.user_id:
        return None

    author_info = {}
    for key in ["author_name", "author_email", "author_affiliation", "author_orcid"]:
        setting = await ops.get_user_setting(db, conv.user_id, "writing", key)
        if setting:
            author_info[key.replace("author_", "")] = setting

    return author_info if author_info else None


async def _save_project(conv_id: int, proj: dict) -> None:
    _projects[conv_id] = proj
    session_factory = _get_session_factory()
    async with session_factory() as db:
        await ops.upsert_resource(
            db,
            conv_id,
            resource_id=f"paper-meta-{conv_id}",
            title=f"Paper Metadata: {proj.get('title', 'Untitled')}",
            resource_type="doc",
            content=json.dumps(proj, default=str),
        )
        author_info = await _get_author_info(db, conv_id)
        draft, _ = _get_draft_from_proj(proj, author_info)
        await ops.upsert_paper_resource(db, conv_id, proj.get("title", "Paper"), draft)

        try:
            ws_path = await ops.get_project_workspace_for_conversation(db, conv_id)
            if ws_path:
                papers_dir = Path(ws_path) / "papers"
                papers_dir.mkdir(parents=True, exist_ok=True)
                safe_title = (
                    "".join(
                        c if c.isalnum() or c in "-_ " else "_" for c in proj.get("title", "paper")
                    )[:80]
                    .strip()
                    .replace(" ", "_")
                    or "paper"
                )
                (papers_dir / f"{safe_title}.md").write_text(draft, encoding="utf-8")
                (papers_dir / f".{safe_title}.meta.json").write_text(
                    json.dumps(proj, indent=2, default=str), encoding="utf-8"
                )
        except Exception as e:
            logger.warning(f"Failed to write paper to workspace: {e}")


def create_writing_tool() -> ToolSpec:
    return ToolSpec(
        name="writing",
        description=(
            "Manage academic paper writing with section-by-section authoring.\n\n"
            "Workflow: create_project -> set_outline -> write_section -> "
            "add_citation -> validate_citations -> export_latex -> get_draft.\n\n"
            "Operations:\n"
            "- create_project: Start paper with title\n"
            "- set_outline: Define section structure [{id, title, subsections}]\n"
            "- write_section: Write section content by ID\n"
            "- refine_section: Revise an existing section\n"
            "- add_citation: Add reference to bibliography\n"
            "- validate_citations: Validate BibTeX against paper text\n"
            "- export_latex: Export full paper to LaTeX\n"
            "- get_draft: Review full paper draft\n"
            "- list_sections: Check sections done/pending"
        ),
        parameters={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": [
                        "create_project",
                        "set_outline",
                        "write_section",
                        "refine_section",
                        "add_citation",
                        "validate_citations",
                        "export_latex",
                        "get_draft",
                        "list_sections",
                    ],
                    "description": "Writing operation to perform",
                },
                "project_id": {"type": "string", "description": "Project identifier"},
                "title": {"type": "string", "description": "Paper title"},
                "outline": {"type": "array", "description": "Outline structure"},
                "section_id": {"type": "string", "description": "Section ID to write/refine"},
                "content": {"type": "string", "description": "Section content"},
                "feedback": {"type": "string", "description": "Feedback for refine"},
                "citation": {"type": "object", "description": "BibTeX citation dict"},
            },
            "required": ["operation"],
        },
        handler=_handle_writing,
    )


async def _handle_writing(
    operation: str,
    project_id: str | None = None,
    title: str | None = None,
    outline: list | None = None,
    section_id: str | None = None,
    content: str | None = None,
    feedback: str | None = None,
    citation: dict | None = None,
    session=None,
    **kwargs,
) -> tuple[str, bool]:
    conv_id = session.conversation_id if session else None

    if operation == "create_project":
        result, ok = _create_project(conv_id, title)
        if ok and conv_id:
            await _save_project(conv_id, _projects[conv_id])
            await _emit_resources(session, conv_id)
            await _emit_files_changed(session, "papers")
        return result, ok

    if conv_id:
        await _load_project(conv_id)

    handlers = {
        "set_outline": lambda: _set_outline(conv_id, outline),
        "write_section": lambda: _write_section(conv_id, section_id, content),
        "refine_section": lambda: _refine_section(conv_id, section_id, content, feedback),
        "add_citation": lambda: _add_citation(conv_id, citation),
        "validate_citations": lambda: _validate_citations(conv_id),
        "list_sections": lambda: _list_sections(conv_id),
    }

    if operation in handlers:
        result, ok = handlers[operation]()
        if ok and conv_id and operation not in ("validate_citations", "list_sections"):
            await _save_project(conv_id, _projects[conv_id])
            await _emit_resources(session, conv_id)
            await _emit_files_changed(session, "papers")
        return result, ok
    elif operation == "export_latex":
        return await _export_latex(conv_id)
    elif operation == "get_draft":
        return await _get_draft(conv_id)

    return f"Unknown operation: {operation}", False


def _get_project(conv_id: int | None) -> dict | None:
    return _projects.get(conv_id) if conv_id else None


def _create_project(conv_id: int | None, title: str | None) -> tuple[str, bool]:
    if not title:
        return "Provide a 'title' for the project.", False

    proj = {
        "title": title,
        "outline": [],
        "sections": {},
        "bibliography": [],
        "created_at": datetime.now(UTC).isoformat(),
    }
    if conv_id:
        _projects[conv_id] = proj
    return f"Created paper project: '{title}'. Use set_outline to define sections.", True


def _set_outline(conv_id: int | None, outline: list | None) -> tuple[str, bool]:
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


def _write_section(conv_id: int | None, section_id: str | None, content: str | None) -> tuple[str, bool]:
    proj = _get_project(conv_id)
    if not proj:
        return "No paper project exists. Call create_project first.", False
    if not section_id or not content:
        return "Provide both 'section_id' and 'content'.", False

    proj["sections"][section_id] = content
    written = len(proj["sections"])
    total = _count_sections(proj["outline"])
    incomplete = _get_incomplete_sections(proj)
    msg = f"Section '{section_id}' written ({len(content)} chars). Progress: {written}/{total} sections. Paper auto-saved."
    if incomplete:
        msg += f"\n\nRemaining incomplete sections ({len(incomplete)}): " + ", ".join(incomplete) + "\nYou MUST write all remaining sections — do NOT leave placeholders."
    else:
        msg += "\n\nAll sections are now written."
    return msg, True


def _refine_section(
    conv_id: int | None, section_id: str | None, content: str | None, feedback: str | None
) -> tuple[str, bool]:
    proj = _get_project(conv_id)
    if not proj:
        return "No paper project exists.", False
    if not section_id:
        return "Provide 'section_id' to refine.", False

    if content:
        proj["sections"][section_id] = content
        return f"Section '{section_id}' refined ({len(content)} chars). Paper auto-saved.", True
    existing = proj["sections"].get(section_id, "")
    return (
        f"Current content of '{section_id}' ({len(existing)} chars):\n\n"
        f"{existing[:5000]}\n\nFeedback: {feedback or 'none provided'}\n"
        f"Provide updated 'content' to apply refinement."
    ), True


def _add_citation(conv_id: int | None, citation: dict | None) -> tuple[str, bool]:
    proj = _get_project(conv_id)
    if not proj:
        return "No paper project exists.", False
    if not citation:
        return "Provide a 'citation' object.", False

    proj["bibliography"].append(citation)
    key = citation.get("key", f"ref{len(proj['bibliography'])}")
    return f"Added citation [@{key}]. Bibliography: {len(proj['bibliography'])} entries.", True


def _validate_citations(conv_id: int | None) -> tuple[str, bool]:
    proj = _get_project(conv_id)
    if not proj:
        return "No paper project exists.", False

    bib_lines = []
    for c in proj.get("bibliography", []):
        k = c.get("key", "unknown")
        t = c.get("type", "misc")
        bib_lines.append(f"@{t}{{{k},")
        for f_name, f_val in c.items():
            if f_name not in ["key", "type"]:
                bib_lines.append(f"  {f_name} = {{{f_val}}},")
        bib_lines.append("}\n")

    val_res = validate_bibtex("\n".join(bib_lines), "\n".join(proj.get("sections", {}).values()))
    report = [
        f"BibTeX Validation Report for '{proj['title']}':",
        f"- Valid: {val_res.valid}",
        f"- Total Citations: {val_res.entries_count}",
    ]
    if val_res.missing_citations:
        report.append(f"- Missing Citations ({len(val_res.missing_citations)}): {', '.join(val_res.missing_citations)}")
    if val_res.unused_citations:
        report.append(f"- Unused Citations ({len(val_res.unused_citations)}): {', '.join(val_res.unused_citations)}")
    if val_res.errors:
        report.append("\nErrors:\n" + "\n".join(f"  - {e}" for e in val_res.errors))
    if val_res.warnings:
        report.append("\nWarnings:\n" + "\n".join(f"  - {w}" for w in val_res.warnings[:5]))

    return "\n".join(report), val_res.valid


async def _export_latex(conv_id: int | None) -> tuple[str, bool]:
    from .latex_compiler import markdown_to_latex

    proj = _get_project(conv_id)
    if not proj:
        return "No paper project exists.", False

    author_info = None
    if conv_id:
        session_factory = _get_session_factory()
        async with session_factory() as db:
            author_info = await _get_author_info(db, conv_id)

    draft, _ = _get_draft_from_proj(proj, author_info)
    return markdown_to_latex(draft, title=proj.get("title", "Paper"), author_info=author_info), True


async def _get_draft(conv_id: int | None) -> tuple[str, bool]:
    proj = _get_project(conv_id)
    if not proj:
        return "No paper project exists.", False

    author_info = None
    if conv_id:
        session_factory = _get_session_factory()
        async with session_factory() as db:
            author_info = await _get_author_info(db, conv_id)

    draft, ok = _get_draft_from_proj(proj, author_info)
    incomplete = _get_incomplete_sections(proj)
    if incomplete:
        draft += (
            "\n\n---\n"
            f"**WARNING — {len(incomplete)} section(s) still incomplete (marked '[Not yet written]'):**\n"
            + "".join(f"  - {s}\n" for s in incomplete)
            + "\nYou MUST write content for every section before the paper can be considered complete."
        )

    return draft, ok


def _get_incomplete_sections(proj: dict) -> list[str]:
    incomplete = []
    for sec in proj.get("outline", []):
        sid = sec.get("id", "")
        if sid and sid not in proj.get("sections", {}):
            incomplete.append(f"{sid} ({sec.get('title', '')})")
        for sub in sec.get("subsections", []):
            sub_id = sub.get("id", "")
            if sub_id and sub_id not in proj.get("sections", {}):
                incomplete.append(f"{sub_id} ({sub.get('title', '')})")
    return incomplete


def _get_draft_from_proj(proj: dict, author_info: dict | None = None) -> tuple[str, bool]:
    lines = [f"# {proj['title']}\n"]

    if author_info:
        author_lines = []
        if author_info.get("name"):
            author_lines.append(f"**{author_info['name']}**")
        if author_info.get("affiliation"):
            author_lines.append(f"*{author_info['affiliation']}*")
        if author_info.get("email"):
            author_lines.append(f"Email: {author_info['email']}")
        if author_info.get("orcid"):
            author_lines.append(f"ORCID: [{author_info['orcid']}](https://orcid.org/{author_info['orcid']})")
        if author_lines:
            lines.extend(["\n".join(author_lines), "\n---\n"])

    if proj.get("outline"):
        for sec in proj["outline"]:
            sid, title = sec.get("id", ""), sec.get("title", "")
            lines.append(f"\n## {title}\n\n{proj['sections'].get(sid, '[Not yet written]')}")
            for sub in sec.get("subsections", []):
                sub_id, sub_title = sub.get("id", ""), sub.get("title", "")
                lines.append(f"\n### {sub_title}\n\n{proj['sections'].get(sub_id, '[Not yet written]')}")
    else:
        for sid, content in proj.get("sections", {}).items():
            lines.append(f"\n## {sid}\n\n{content}")

    if proj.get("bibliography"):
        lines.append("\n## References\n")
        for c in proj["bibliography"]:
            lines.append(f'[{c.get("key", "?")}] {c.get("author", "Unknown")}. "{c.get("title", "Untitled")}". {c.get("year", "?")}.')

    return "\n".join(lines), True


def _list_sections(conv_id: int | None) -> tuple[str, bool]:
    proj = _get_project(conv_id)
    if not proj:
        return "No paper project exists.", False

    lines = [f"## Sections for '{proj['title']}'\n"]
    if proj.get("outline"):
        for sec in proj["outline"]:
            sid = sec.get("id", "")
            written = "done" if sid in proj["sections"] else "pending"
            lines.append(f"  [{written}] {sid}: {sec.get('title', '')} ({len(proj['sections'].get(sid, ''))} chars)")
    else:
        lines.append("No outline defined. Use set_outline first.")
    return "\n".join(lines), True


async def _emit_files_changed(session, path: str = "") -> None:
    if session:
        await session.emit(AgentEvent(event_type="workspace_files_changed", data={"path": path}))


async def _emit_resources(session, conv_id: int) -> None:
    if not session:
        return
    session_factory = _get_session_factory()
    async with session_factory() as db:
        resources = await ops.get_conversation_resources(db, conv_id)
        res_list = [{"title": r.title, "url": r.url or "", "type": r.type, "id": r.resource_id} for r in resources]
        await session.emit(AgentEvent(event_type="resources_update", data={"resources": res_list}))


def _count_sections(outline: list) -> int:
    return len(outline) + sum(len(sec.get("subsections", [])) for sec in outline)
