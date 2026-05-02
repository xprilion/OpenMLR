"""inspect_files tool — parallel file reading with relevance filtering."""

import asyncio
import logging
from pathlib import Path

from ..agent.types import ToolSpec

logger = logging.getLogger("openmlr.tools.inspect")

# Limits
_MAX_FILES = 50  # max files to read in one call
_MAX_LINES_PER_FILE = 200  # lines per file for relevance check
_MAX_TOTAL_CHARS = 100_000  # total output budget
_MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB — skip files larger than this


def create_inspect_tool() -> ToolSpec:
    return ToolSpec(
        name="inspect_files",
        description=(
            "Read multiple files or directories in parallel and filter for relevance.\n\n"
            "Use this when you need to quickly scan many files (e.g. an entire directory) "
            "to find which ones are relevant to the user's request. Each file is read "
            "concurrently and scored for relevance against the query.\n\n"
            "Returns relevant file contents and a list of skipped files with reasons.\n\n"
            "Examples:\n"
            '- inspect_files(paths=["code/"], query="training loop")\n'
            '- inspect_files(paths=["code/train.py", "code/model.py"], query="loss function")\n'
            '- inspect_files(paths=["data/"], query="dataset loading")'
        ),
        parameters={
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "File or directory paths to inspect. Directories are expanded "
                        "to their file listing. Relative paths resolve from workspace root."
                    ),
                },
                "query": {
                    "type": "string",
                    "description": (
                        "What you're looking for — used to filter which files are relevant. "
                        "Be specific (e.g. 'training loop implementation' not just 'training')."
                    ),
                },
                "max_files": {
                    "type": "integer",
                    "description": f"Max files to read (default {_MAX_FILES}).",
                },
            },
            "required": ["paths", "query"],
        },
        handler=_handle_inspect_files,
    )


async def _handle_inspect_files(
    paths: list[str],
    query: str,
    max_files: int = _MAX_FILES,
    **kwargs,
) -> tuple[str, bool]:
    """Read files in parallel, score for relevance, return filtered results."""
    from .local import _get_effective_root, _validate_path

    if not paths:
        return "No paths provided.", False
    if not query:
        return "No query provided — specify what you're looking for.", False

    effective_root = _get_effective_root()
    max_files = max(1, min(max_files, _MAX_FILES))

    # Phase 1: Expand directories to file lists
    file_paths: list[Path] = []
    dir_listings: list[str] = []

    for p in paths:
        target = Path(p).expanduser()
        if not target.is_absolute():
            target = effective_root / target
        target, error = _validate_path(target)
        if error:
            dir_listings.append(f"- `{p}`: {error}")
            continue

        if target.is_dir():
            entries = sorted(target.iterdir())
            dir_entries = []
            for entry in entries:
                if entry.name.startswith("."):
                    continue
                if entry.is_file():
                    # Re-validate each child to catch symlinks escaping workspace
                    resolved_entry, entry_err = _validate_path(entry.resolve())
                    if entry_err:
                        continue
                    file_paths.append(resolved_entry)
                dir_entries.append(f"  {'/' if entry.is_dir() else ' '} {entry.name}")
            rel = (
                target.relative_to(effective_root)
                if _is_relative(target, effective_root)
                else target
            )
            dir_listings.append(f"Directory `{rel}/`:\n" + "\n".join(dir_entries))
        elif target.is_file():
            file_paths.append(target)
        else:
            dir_listings.append(f"- `{p}`: not found")

    if len(file_paths) > max_files:
        skipped_count = len(file_paths) - max_files
        file_paths = file_paths[:max_files]
        dir_listings.append(
            f"\n[Truncated: only inspecting first {max_files} files, "
            f"{skipped_count} additional files skipped]"
        )

    if not file_paths:
        result = "No files found to inspect.\n"
        if dir_listings:
            result += "\n".join(dir_listings)
        return result, True

    # Phase 2: Read all files in parallel
    loop = asyncio.get_running_loop()
    read_tasks = [loop.run_in_executor(None, _read_file_snippet, fp) for fp in file_paths]
    results = await asyncio.gather(*read_tasks, return_exceptions=True)

    # Phase 3: Score relevance
    file_data: list[dict] = []
    for fp, result in zip(file_paths, results, strict=True):
        if isinstance(result, Exception):
            continue
        content, line_count = result
        if not content.strip():
            continue
        rel_path = fp.relative_to(effective_root) if _is_relative(fp, effective_root) else fp
        score = _score_relevance(content, query)
        file_data.append(
            {
                "path": str(rel_path),
                "content": content,
                "lines": line_count,
                "score": score,
            }
        )

    # Sort by relevance score (descending)
    file_data.sort(key=lambda x: x["score"], reverse=True)

    # Phase 4: Build output within budget
    output_parts: list[str] = []
    total_chars = 0
    relevant: list[dict] = []
    skipped: list[dict] = []

    for fd in file_data:
        if fd["score"] < 0.1:
            skipped.append(fd)
            continue
        if total_chars + len(fd["content"]) > _MAX_TOTAL_CHARS:
            skipped.append(fd)
            continue
        relevant.append(fd)
        total_chars += len(fd["content"])

    # Format output
    if dir_listings:
        output_parts.append("## Directory Listings\n" + "\n".join(dir_listings))

    output_parts.append(f"## Relevant Files ({len(relevant)}/{len(file_data)} inspected)")
    for fd in relevant:
        output_parts.append(
            f"\n### {fd['path']} ({fd['lines']} lines, relevance: {fd['score']:.0%})\n"
            f"```\n{fd['content']}\n```"
        )

    if skipped:
        skip_lines = [f"- `{fd['path']}` ({fd['lines']} lines)" for fd in skipped]
        output_parts.append(
            f"\n## Skipped ({len(skipped)} files — low relevance or budget exceeded)\n"
            + "\n".join(skip_lines)
        )

    return "\n\n".join(output_parts), True


def _read_file_snippet(path: Path) -> tuple[str, int]:
    """Read up to _MAX_LINES_PER_FILE lines from a file. Returns (content, total_lines)."""
    try:
        size = path.stat().st_size
        if size > _MAX_FILE_SIZE:
            return f"[File too large: {size:,} bytes, skipped]", 0
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return "", 0

    lines = text.splitlines()
    total = len(lines)
    selected = lines[:_MAX_LINES_PER_FILE]
    content = "\n".join(f"{i}: {line}" for i, line in enumerate(selected, 1))
    if total > _MAX_LINES_PER_FILE:
        content += f"\n\n[... {total - _MAX_LINES_PER_FILE} more lines truncated]"
    return content, total


def _score_relevance(content: str, query: str) -> float:
    """Simple keyword-overlap relevance score (0.0 to 1.0).

    Splits the query into terms and checks how many appear in the content.
    This is fast and doesn't require an LLM call.
    """
    content_lower = content.lower()
    terms = [t.strip() for t in query.lower().split() if len(t.strip()) > 2]
    if not terms:
        return 0.5  # no useful query terms — include by default

    matches = sum(1 for t in terms if t in content_lower)
    return matches / len(terms)


def _is_relative(path: Path, root: Path) -> bool:
    """Check if path is under root without raising."""
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
