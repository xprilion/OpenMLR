"""Workspace Persistence — file-based storage for project working data.

Handles saving/loading of:
- Search results (paper searches, web searches)
- Research notes and summaries
- Tool failure logs
- Compute capability snapshots
- Experiment logs
- Cross-conversation state
"""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

log = logging.getLogger(__name__)


class WorkspacePersistence:
    """File-based persistence for a project workspace."""

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path)
        if not self.workspace_path.exists():
            log.warning(f"Workspace path does not exist: {workspace_path}")

    def _ensure_dir(self, *parts: str) -> Path:
        """Ensure a subdirectory exists and return its path."""
        path = self.workspace_path.joinpath(*parts)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _timestamp(self) -> str:
        return datetime.now(UTC).strftime("%Y%m%d-%H%M%S")

    @staticmethod
    def _sanitize_filename(name: str, max_len: int = 80) -> str:
        """Sanitize a string for safe use in filenames. Alphanumeric + hyphen/underscore only."""
        return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)[:max_len] or "unknown"

    # ── Search Results ───────────────────────────────────

    def save_search_results(
        self,
        query: str,
        source: str,
        results: list[dict],
        conversation_uuid: str | None = None,
    ) -> Path:
        """Save paper/web search results to workspace."""
        dir_path = self._ensure_dir("research", "searches")
        filename = f"{self._timestamp()}_{self._sanitize_filename(source)}.json"
        filepath = dir_path / filename

        data = {
            "query": query,
            "source": source,
            "timestamp": datetime.now(UTC).isoformat(),
            "conversation_uuid": conversation_uuid,
            "result_count": len(results),
            "results": results,
        }
        filepath.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        log.debug(f"Saved {len(results)} search results to {filepath}")
        return filepath

    def get_recent_searches(self, limit: int = 10) -> list[dict]:
        """Get recent search results (metadata only, not full results)."""
        dir_path = self.workspace_path / "research" / "searches"
        if not dir_path.exists():
            return []

        searches = []
        for filepath in sorted(dir_path.glob("*.json"), reverse=True):
            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
                searches.append(
                    {
                        "query": data.get("query"),
                        "source": data.get("source"),
                        "timestamp": data.get("timestamp"),
                        "result_count": data.get("result_count", 0),
                        "filename": filepath.name,
                    }
                )
                if len(searches) >= limit:
                    break
            except Exception:
                continue
        return searches

    # ── Research Notes ───────────────────────────────────

    def save_research_note(
        self,
        topic: str,
        content: str,
        conversation_uuid: str | None = None,
    ) -> Path:
        """Save a research note or summary."""
        dir_path = self._ensure_dir("research", "notes")
        # Sanitize topic for filename
        safe_topic = "".join(c if c.isalnum() or c in "-_ " else "" for c in topic)
        safe_topic = safe_topic.strip().replace(" ", "_")[:100] or "note"
        filename = f"{self._timestamp()}_{safe_topic}.md"
        filepath = dir_path / filename

        header = f"# {topic}\n\n"
        header += f"_Generated: {datetime.now(UTC).isoformat()}_\n"
        if conversation_uuid:
            header += f"_Conversation: {conversation_uuid}_\n"
        header += "\n---\n\n"

        filepath.write_text(header + content, encoding="utf-8")
        log.debug(f"Saved research note to {filepath}")
        return filepath

    def get_research_notes(self, limit: int = 20) -> list[dict]:
        """List available research notes."""
        dir_path = self.workspace_path / "research" / "notes"
        if not dir_path.exists():
            return []

        notes = []
        for filepath in sorted(dir_path.glob("*.md"), reverse=True):
            try:
                content = filepath.read_text(encoding="utf-8")
                # Extract title from first line
                title = content.split("\n")[0].lstrip("# ").strip()
                notes.append(
                    {
                        "title": title,
                        "filename": filepath.name,
                        "size": filepath.stat().st_size,
                        "modified": filepath.stat().st_mtime,
                    }
                )
                if len(notes) >= limit:
                    break
            except Exception:
                continue
        return notes

    # ── Paper Storage ────────────────────────────────────

    def save_paper(
        self,
        paper_id: str,
        title: str,
        content: str,
        metadata: dict | None = None,
    ) -> Path:
        """Save a parsed paper to the workspace."""
        dir_path = self._ensure_dir("papers")
        # Use paper_id as filename (strictly sanitized)
        safe_id = self._sanitize_filename(paper_id)
        filepath = dir_path / f"{safe_id}.md"

        header = f"# {title}\n\n"
        if metadata:
            if metadata.get("authors"):
                header += f"**Authors:** {metadata['authors']}\n"
            if metadata.get("year"):
                header += f"**Year:** {metadata['year']}\n"
            if metadata.get("url"):
                header += f"**URL:** {metadata['url']}\n"
            header += "\n---\n\n"

        filepath.write_text(header + content, encoding="utf-8")

        # Save metadata separately as JSON
        meta_path = dir_path / f"{safe_id}.meta.json"
        meta_data = {
            "paper_id": paper_id,
            "title": title,
            "saved_at": datetime.now(UTC).isoformat(),
            **(metadata or {}),
        }
        meta_path.write_text(json.dumps(meta_data, indent=2, default=str), encoding="utf-8")

        return filepath

    # ── Tool Failure Logs ────────────────────────────────

    def log_tool_failure(
        self,
        tool_name: str,
        error: str,
        args: dict | None = None,
        conversation_uuid: str | None = None,
    ) -> Path:
        """Log a tool/API/MCP failure for future reference."""
        dir_path = self._ensure_dir("logs", "tool_failures")
        filename = f"{self._timestamp()}_{self._sanitize_filename(tool_name)}.json"
        filepath = dir_path / filename

        data = {
            "tool": tool_name,
            "error": error,
            "args": args,
            "timestamp": datetime.now(UTC).isoformat(),
            "conversation_uuid": conversation_uuid,
        }
        filepath.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        log.debug(f"Logged tool failure: {tool_name} -> {filepath}")
        return filepath

    def get_recent_failures(self, limit: int = 10) -> list[dict]:
        """Get recent tool failure logs."""
        dir_path = self.workspace_path / "logs" / "tool_failures"
        if not dir_path.exists():
            return []

        failures = []
        for filepath in sorted(dir_path.glob("*.json"), reverse=True):
            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
                failures.append(data)
                if len(failures) >= limit:
                    break
            except Exception:
                continue
        return failures

    # ── Compute Logs ─────────────────────────────────────

    def log_compute_probe(
        self,
        node_name: str,
        capabilities: dict,
    ) -> Path:
        """Log compute node probe results."""
        dir_path = self._ensure_dir("logs", "compute")
        filename = f"{self._timestamp()}_{self._sanitize_filename(node_name)}.json"
        filepath = dir_path / filename

        data = {
            "node_name": node_name,
            "capabilities": capabilities,
            "probed_at": datetime.now(UTC).isoformat(),
        }
        filepath.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        return filepath

    # ── Experiment Logs ──────────────────────────────────

    def log_experiment(
        self,
        name: str,
        command: str,
        result: dict,
        conversation_uuid: str | None = None,
    ) -> Path:
        """Log an experiment execution."""
        dir_path = self._ensure_dir("logs", "experiments")
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)[:80]
        filename = f"{self._timestamp()}_{safe_name}.json"
        filepath = dir_path / filename

        data = {
            "name": name,
            "command": command,
            "result": result,
            "timestamp": datetime.now(UTC).isoformat(),
            "conversation_uuid": conversation_uuid,
        }
        filepath.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        return filepath

    # ── Cross-conversation State ─────────────────────────

    def get_state(self) -> dict:
        """Load the cross-conversation state."""
        state_path = self.workspace_path / ".project-meta" / "state.json"
        if not state_path.exists():
            return {
                "last_conversation_uuid": None,
                "open_questions": [],
                "key_findings": [],
                "active_experiments": [],
            }
        try:
            return json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def save_state(self, state: dict) -> None:
        """Save the cross-conversation state."""
        state_path = self.workspace_path / ".project-meta" / "state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")

    def update_state(self, **kwargs) -> dict:
        """Update specific fields in the cross-conversation state."""
        state = self.get_state()
        state.update(kwargs)
        self.save_state(state)
        return state

    # ── Report Storage ─────────────────────────────────────

    def save_report(self, title: str, content: str) -> Path:
        """Save a task completion report to the workspace."""
        dir_path = self._ensure_dir(".project-meta", "reports")
        safe_title = self._sanitize_filename(title)
        filename = f"{safe_title}.md"
        filepath = dir_path / filename
        filepath.write_text(content, encoding="utf-8")
        log.debug(f"Saved report to {filepath}")
        return filepath

    # ── Plan Storage ─────────────────────────────────────

    def save_plan(
        self,
        plan_content: str,
        conversation_uuid: str,
    ) -> Path:
        """Save a task plan to the workspace."""
        dir_path = self._ensure_dir(".project-meta", "plans")
        # Sanitize the UUID to prevent path injection
        safe_uuid = self._sanitize_filename(conversation_uuid)
        filename = f"{safe_uuid}.md"
        filepath = dir_path / filename
        filepath.write_text(plan_content, encoding="utf-8")
        return filepath

    # ── Workspace Summary ────────────────────────────────

    def get_workspace_summary(self) -> dict:
        """Get a summary of all workspace contents for context injection."""
        summary = {
            "papers": self._count_files("papers", "*.md"),
            "research_notes": self._count_files("research/notes", "*.md"),
            "search_results": self._count_files("research/searches", "*.json"),
            "code_files": self._count_files_recursive("code"),
            "experiments": self._count_files("logs/experiments", "*.json"),
            "tool_failures": self._count_files("logs/tool_failures", "*.json"),
        }

        # Add recent failures as warnings
        recent_failures = self.get_recent_failures(limit=5)
        if recent_failures:
            summary["recent_tool_failures"] = [
                {"tool": f["tool"], "error": f["error"][:200], "time": f.get("timestamp")}
                for f in recent_failures
            ]

        return summary

    def _count_files(self, subdir: str, pattern: str) -> int:
        path = self.workspace_path / subdir
        if not path.exists():
            return 0
        return len(list(path.glob(pattern)))

    def _count_files_recursive(self, subdir: str) -> int:
        path = self.workspace_path / subdir
        if not path.exists():
            return 0
        count = 0
        for _ in path.rglob("*"):
            count += 1
        return count
