"""Paper writing tool — section-by-section academic paper authoring."""

import json
from ..agent.types import ToolSpec

# In-memory writing projects (will be backed by DB later)
_projects: dict[str, dict] = {}


def create_writing_tool() -> ToolSpec:
    return ToolSpec(
        name="writing",
        description=(
            "Manage academic paper writing projects. Supports section-by-section "
            "writing with research corpus integration. Operations: create_project, "
            "set_outline, write_section, refine_section, add_citation, "
            "get_draft, list_sections, export."
        ),
        parameters={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": [
                        "create_project", "set_outline", "write_section",
                        "refine_section", "add_citation", "get_draft",
                        "list_sections", "export",
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
                        "key": {"type": "string", "description": "Citation key (e.g. smith2024)"},
                        "type": {"type": "string", "description": "Entry type (article, inproceedings, etc.)"},
                        "title": {"type": "string", "description": "Paper title"},
                        "author": {"type": "string", "description": "Author names"},
                        "year": {"type": "string", "description": "Publication year"},
                        "venue": {"type": "string", "description": "Journal or conference"},
                        "url": {"type": "string", "description": "URL or DOI"},
                    },
                    "required": ["key", "title", "author", "year"],
                },
                "format": {
                    "type": "string",
                    "enum": ["markdown", "latex"],
                    "description": "Export format (default: markdown)",
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
    format: str = "markdown",
    **kwargs,
) -> tuple[str, bool]:
    """Route writing operations."""

    if operation == "create_project":
        return _create_project(title)
    elif operation == "set_outline":
        return _set_outline(project_id, outline)
    elif operation == "write_section":
        return _write_section(project_id, section_id, content)
    elif operation == "refine_section":
        return _refine_section(project_id, section_id, content, feedback)
    elif operation == "add_citation":
        return _add_citation(project_id, citation)
    elif operation == "get_draft":
        return _get_draft(project_id)
    elif operation == "list_sections":
        return _list_sections(project_id)
    elif operation == "export":
        return _export(project_id, format)
    else:
        return f"Unknown operation: {operation}", False


def _get_project(project_id: str) -> dict | None:
    if not project_id:
        # Return most recent project
        if _projects:
            return list(_projects.values())[-1]
        return None
    return _projects.get(project_id)


def _create_project(title: str) -> tuple[str, bool]:
    if not title:
        return "Provide a 'title' for the project.", False

    import uuid
    pid = str(uuid.uuid4())[:8]
    _projects[pid] = {
        "id": pid,
        "title": title,
        "outline": [],
        "sections": {},
        "bibliography": [],
        "status": "draft",
    }
    return f"Created project '{title}' (id: {pid}). Use set_outline to define sections.", True


def _set_outline(project_id: str, outline: list) -> tuple[str, bool]:
    proj = _get_project(project_id)
    if not proj:
        return "Project not found. Create one first.", False
    if not outline:
        return "Provide an 'outline' array.", False

    proj["outline"] = outline
    lines = [f"Outline set for '{proj['title']}':\n"]
    for i, sec in enumerate(outline):
        lines.append(f"  {sec.get('id', i)}. {sec.get('title', 'Untitled')}")
        for sub in sec.get("subsections", []):
            lines.append(f"    {sub.get('id', '')}. {sub.get('title', '')}")
    return "\n".join(lines), True


def _write_section(project_id: str, section_id: str, content: str) -> tuple[str, bool]:
    proj = _get_project(project_id)
    if not proj:
        return "Project not found.", False
    if not section_id or not content:
        return "Provide both 'section_id' and 'content'.", False

    proj["sections"][section_id] = content

    written = len(proj["sections"])
    total = _count_sections(proj["outline"])
    return (
        f"Section '{section_id}' written ({len(content)} chars). "
        f"Progress: {written}/{total} sections complete."
    ), True


def _refine_section(project_id: str, section_id: str, content: str, feedback: str) -> tuple[str, bool]:
    proj = _get_project(project_id)
    if not proj:
        return "Project not found.", False
    if not section_id:
        return "Provide 'section_id' to refine.", False

    if content:
        proj["sections"][section_id] = content
        return f"Section '{section_id}' refined ({len(content)} chars).", True
    else:
        existing = proj["sections"].get(section_id, "")
        return (
            f"Current content of '{section_id}' ({len(existing)} chars):\n\n"
            f"{existing[:5000]}\n\n"
            f"Feedback: {feedback or 'none provided'}\n"
            f"Provide updated 'content' to apply refinement."
        ), True


def _add_citation(project_id: str, citation: dict) -> tuple[str, bool]:
    proj = _get_project(project_id)
    if not proj:
        return "Project not found.", False
    if not citation:
        return "Provide a 'citation' object.", False

    proj["bibliography"].append(citation)
    key = citation.get("key", f"ref{len(proj['bibliography'])}")
    return f"Added citation [@{key}]. Bibliography now has {len(proj['bibliography'])} entries.", True


def _get_draft(project_id: str) -> tuple[str, bool]:
    proj = _get_project(project_id)
    if not proj:
        return "Project not found.", False

    lines = [f"# {proj['title']}\n"]

    if proj["outline"]:
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
        # No outline — just dump sections
        for sid, content in proj["sections"].items():
            lines.append(f"\n## {sid}\n\n{content}")

    # Bibliography
    if proj["bibliography"]:
        lines.append("\n## References\n")
        for i, c in enumerate(proj["bibliography"], 1):
            key = c.get("key", f"ref{i}")
            author = c.get("author", "Unknown")
            title = c.get("title", "Untitled")
            year = c.get("year", "?")
            lines.append(f"[{key}] {author}. \"{title}\". {year}.")

    return "\n".join(lines), True


def _list_sections(project_id: str) -> tuple[str, bool]:
    proj = _get_project(project_id)
    if not proj:
        return "Project not found.", False

    lines = [f"## Sections for '{proj['title']}'\n"]
    if proj["outline"]:
        for sec in proj["outline"]:
            sid = sec.get("id", "")
            written = "done" if sid in proj["sections"] else "pending"
            char_count = len(proj["sections"].get(sid, ""))
            lines.append(f"  [{written}] {sid}: {sec.get('title', '')} ({char_count} chars)")
    else:
        lines.append("No outline defined. Use set_outline first.")

    return "\n".join(lines), True


def _export(project_id: str, fmt: str = "markdown") -> tuple[str, bool]:
    proj = _get_project(project_id)
    if not proj:
        return "Project not found.", False

    draft, _ = _get_draft(project_id)

    if fmt == "latex":
        return _convert_to_latex(proj, draft), True
    else:
        return f"Markdown draft:\n\n{draft}", True


def _convert_to_latex(proj: dict, markdown: str) -> str:
    """Basic Markdown to LaTeX conversion."""
    lines = [
        "\\documentclass{article}",
        "\\usepackage[utf8]{inputenc}",
        "\\usepackage{amsmath,amssymb}",
        "\\usepackage{hyperref}",
        "",
        f"\\title{{{proj['title']}}}",
        "\\author{}",
        "\\date{\\today}",
        "",
        "\\begin{document}",
        "\\maketitle",
        "",
    ]

    # Simple conversion
    for line in markdown.split("\n"):
        if line.startswith("### "):
            lines.append(f"\\subsubsection{{{line[4:]}}}")
        elif line.startswith("## "):
            lines.append(f"\\subsection{{{line[3:]}}}")
        elif line.startswith("# "):
            lines.append(f"\\section{{{line[2:]}}}")
        else:
            lines.append(line)

    # Bibliography
    if proj["bibliography"]:
        lines.append("")
        lines.append("\\begin{thebibliography}{99}")
        for c in proj["bibliography"]:
            key = c.get("key", "")
            author = c.get("author", "")
            title = c.get("title", "")
            year = c.get("year", "")
            lines.append(f"\\bibitem{{{key}}} {author}. \\textit{{{title}}}. {year}.")
        lines.append("\\end{thebibliography}")

    lines.append("\\end{document}")
    return "\n".join(lines)


def _count_sections(outline: list) -> int:
    count = len(outline)
    for sec in outline:
        count += len(sec.get("subsections", []))
    return count
