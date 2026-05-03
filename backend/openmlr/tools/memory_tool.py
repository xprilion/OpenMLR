"""Persistent memory tool — bounded, curated, always-in-context facts.

Two targets:
- "project": Project-scoped agent notes (environment, conventions, lessons).
  Stored in UserSetting(category="memory", key="project_{project_id}").
  Limit: 2500 chars.
- "user": User-scoped preferences and profile.
  Stored in UserSetting(category="memory", key="user_profile").
  Limit: 1500 chars.
"""

import logging
import re

from ..agent.types import ToolSpec

logger = logging.getLogger(__name__)

# Character limits per target
MEMORY_LIMITS = {
    "project": 2500,
    "user": 1500,
}

# Section separator for entries
ENTRY_SEPARATOR = "\n§\n"

# Security patterns to block (prompt injection, credential exfiltration)
_THREAT_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(your\s+)?rules", re.IGNORECASE),
    re.compile(r"system\s+prompt\s+override", re.IGNORECASE),
    re.compile(r"do\s+not\s+tell\s+the\s+user", re.IGNORECASE),
    re.compile(r"curl\s+.*\$[A-Z_]+", re.IGNORECASE),
    re.compile(r"cat\s+\.(env|credentials|secrets)", re.IGNORECASE),
]

_INVISIBLE_CHARS = {"\u200b", "\u200c", "\u200d", "\ufeff", "\u2060", "\u2062", "\u2063"}


def _scan_memory_content(content: str) -> tuple[bool, str]:
    """Check memory content for injection/exfiltration patterns.
    Returns (is_safe, threat_type)."""
    for char in _INVISIBLE_CHARS:
        if char in content:
            return False, "invisible_unicode"
    for pattern in _THREAT_PATTERNS:
        if pattern.search(content):
            return False, "prompt_injection"
    return True, ""


def _parse_entries(raw: str) -> list[str]:
    """Parse stored memory string into individual entries."""
    if not raw:
        return []
    return [e.strip() for e in raw.split(ENTRY_SEPARATOR) if e.strip()]


def _serialize_entries(entries: list[str]) -> str:
    """Serialize entries back to storage format."""
    return ENTRY_SEPARATOR.join(entries)


async def _get_memory_key(target: str, session, db) -> str | None:
    """Build the UserSetting key for the given target."""
    if target == "user":
        return "user_profile"
    if target == "project":
        conv_id = getattr(session, "conversation_id", None)
        if not conv_id:
            return None
        # Resolve actual project_id from conversation
        try:
            from ..db import operations as ops

            conv = await ops.get_conversation_by_id(db, conv_id)
            if conv and conv.project_id:
                return f"project_{conv.project_id}"
        except Exception:
            pass
        # Fallback to conversation_id if no project
        return f"project_{conv_id}"
    return None


async def _load_memory(target: str, session, user_id: int, db) -> tuple[list[str], int]:
    """Load memory entries from DB. Returns (entries, total_chars)."""
    from ..db import operations as ops

    key = await _get_memory_key(target, session, db)
    if not key:
        return [], 0

    data = await ops.get_user_setting(db, user_id, "memory", key)
    if not data:
        return [], 0

    if isinstance(data, dict):
        raw = data.get("content", "")
    elif isinstance(data, str):
        raw = data
    else:
        raw = str(data)

    entries = _parse_entries(raw)
    total_chars = sum(len(e) for e in entries)
    return entries, total_chars


async def _save_memory(target: str, entries: list[str], session, user_id: int, db) -> None:
    """Persist memory entries to DB."""
    from ..db import operations as ops

    key = await _get_memory_key(target, session, db)
    if not key:
        return

    content = _serialize_entries(entries)
    await ops.set_user_setting(db, user_id, "memory", key, {"content": content})


async def _handle_memory(
    action: str,
    target: str = "project",
    content: str = "",
    old_text: str = "",
    session=None,
    user_id: int | None = None,
    db=None,
    **kwargs,
) -> tuple[str, bool]:
    """Handle memory tool actions: add, replace, remove."""
    if target not in MEMORY_LIMITS:
        return f"Invalid target '{target}'. Use 'project' or 'user'.", False

    if not user_id or not db:
        return "Memory tool requires authentication context.", False

    char_limit = MEMORY_LIMITS[target]
    entries, total_chars = await _load_memory(target, session, user_id, db)

    if action == "add":
        if not content:
            return "Error: 'content' is required for add action.", False

        # Security scan
        is_safe, threat = _scan_memory_content(content)
        if not is_safe:
            return f"Memory entry blocked: detected {threat} pattern.", False

        # Duplicate check
        if content.strip() in entries:
            return "Entry already exists (no duplicate added).", True

        # Check capacity
        new_total = total_chars + len(content.strip())
        if new_total > char_limit:
            entry_list = "\n".join(
                f"  - {e[:80]}..." if len(e) > 80 else f"  - {e}" for e in entries
            )
            return (
                f"Memory at {total_chars}/{char_limit} chars. "
                f"Adding this entry ({len(content.strip())} chars) would exceed the limit.\n"
                f"Replace or remove existing entries first.\n\n"
                f"Current entries:\n{entry_list}\n\n"
                f"Usage: {total_chars}/{char_limit}"
            ), False

        entries.append(content.strip())
        await _save_memory(target, entries, session, user_id, db)
        new_total = sum(len(e) for e in entries)
        return f"Added to {target} memory. Usage: {new_total}/{char_limit} chars.", True

    elif action == "replace":
        if not old_text:
            return "Error: 'old_text' is required for replace action.", False
        if not content:
            return "Error: 'content' is required for replace action.", False

        # Security scan on new content
        is_safe, threat = _scan_memory_content(content)
        if not is_safe:
            return f"Memory entry blocked: detected {threat} pattern.", False

        # Find matching entry by substring
        matches = [i for i, e in enumerate(entries) if old_text in e]
        if len(matches) == 0:
            return f"No entry matching '{old_text}' found.", False
        if len(matches) > 1:
            return (
                f"Found {len(matches)} entries matching '{old_text}'. Provide a more specific substring.",
                False,
            )

        idx = matches[0]
        old_entry_len = len(entries[idx])
        new_entry = content.strip()
        new_total = total_chars - old_entry_len + len(new_entry)
        if new_total > char_limit:
            return (
                f"Replacement would exceed limit ({new_total}/{char_limit} chars). "
                f"Use a shorter entry or remove other entries first."
            ), False

        entries[idx] = new_entry
        await _save_memory(target, entries, session, user_id, db)
        new_total = sum(len(e) for e in entries)
        return f"Replaced entry in {target} memory. Usage: {new_total}/{char_limit} chars.", True

    elif action == "remove":
        if not old_text:
            return "Error: 'old_text' is required for remove action.", False

        matches = [i for i, e in enumerate(entries) if old_text in e]
        if len(matches) == 0:
            return f"No entry matching '{old_text}' found.", False
        if len(matches) > 1:
            return (
                f"Found {len(matches)} entries matching '{old_text}'. Provide a more specific substring.",
                False,
            )

        removed = entries.pop(matches[0])
        await _save_memory(target, entries, session, user_id, db)
        new_total = sum(len(e) for e in entries)
        return (
            f"Removed from {target} memory: '{removed[:60]}...'. Usage: {new_total}/{char_limit} chars.",
            True,
        )

    else:
        return f"Unknown action '{action}'. Use 'add', 'replace', or 'remove'.", False


def create_memory_tool() -> ToolSpec:
    return ToolSpec(
        name="memory",
        description=(
            "Manage persistent memory that carries across sessions.\n\n"
            "Memory entries are injected into the system prompt at session start, "
            "so you always have access to saved facts without a tool call.\n\n"
            "Two targets:\n"
            "- 'project': Project-scoped notes (environment, conventions, lessons learned). "
            f"Limit: {MEMORY_LIMITS['project']} chars.\n"
            "- 'user': User preferences and profile (communication style, expertise). "
            f"Limit: {MEMORY_LIMITS['user']} chars.\n\n"
            "Actions:\n"
            "- add: Save a new memory entry\n"
            "- replace: Replace an existing entry (match by old_text substring)\n"
            "- remove: Remove an entry (match by old_text substring)\n\n"
            "Save proactively when you learn: user preferences, environment facts, "
            "project conventions, corrections, completed work summaries."
        ),
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "replace", "remove"],
                    "description": "Action to perform",
                },
                "target": {
                    "type": "string",
                    "enum": ["project", "user"],
                    "description": "Memory target: 'project' for project notes, 'user' for user profile",
                },
                "content": {
                    "type": "string",
                    "description": "Content to add or replacement content (for add/replace)",
                },
                "old_text": {
                    "type": "string",
                    "description": "Unique substring to identify the entry to replace/remove",
                },
            },
            "required": ["action", "target"],
        },
        handler=_handle_memory,
    )


async def load_memory_for_prompt(user_id: int, session, db) -> str:
    """Load all memory entries and format for system prompt injection.

    Called at session start. Returns a formatted string or empty string.
    """
    sections = []

    for target, limit in MEMORY_LIMITS.items():
        entries, total_chars = await _load_memory(target, session, user_id, db)
        if not entries:
            continue

        pct = int(total_chars / limit * 100) if limit > 0 else 0
        label = "MEMORY (project notes)" if target == "project" else "USER PROFILE"
        header = f"{'═' * 50}\n{label} [{pct}% — {total_chars}/{limit} chars]\n{'═' * 50}"
        body = "\n§\n".join(entries)
        sections.append(f"{header}\n{body}")

    return "\n\n".join(sections)
