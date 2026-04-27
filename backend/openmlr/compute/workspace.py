"""Workspace Manager — project-scoped filesystem with backward-compatible conversation support.

The workspace is the persistent home for all project artifacts:
code, data, models, outputs, papers, research notes, logs, and knowledge graph.
It persists across conversations and compute resource changes.
"""

import json
import logging
import os
import shutil
import tarfile
from datetime import UTC, datetime
from pathlib import Path

log = logging.getLogger(__name__)

# Default workspace root — overridden by OPENMLR_WORKSPACES_PATH in Docker
WORKSPACES_ROOT = Path(os.environ.get("OPENMLR_WORKSPACES_PATH", "/app/.workspaces"))

# Standard project workspace subdirectories
PROJECT_SUBDIRS = [
    "code",
    "data",
    "models",
    "outputs",
    "papers",
    "research",
    "research/searches",
    "research/notes",
    "research/citations",
    "logs",
    "logs/tool_failures",
    "logs/compute",
    "logs/experiments",
    "venvs",
    ".project-meta",
    ".project-meta/plans",
]

# Legacy conversation-only subdirectories (backward compat)
LEGACY_SUBDIRS = ["data", "models", "code", "outputs", ".openmlr-meta"]


class WorkspaceManager:
    """Manages isolated workspace directories for projects and conversations.

    Supports two modes:
    - Project mode: workspace at WORKSPACES_ROOT/{project_slug}/
    - Legacy mode: workspace at ~/.openmlr/workspaces/workspace-{uuid}/
    """

    def __init__(self, base_dir: str | Path = None):
        self.base_dir = Path(base_dir) if base_dir else Path.home() / ".openmlr"
        self.workspace_dir = self.base_dir / "workspaces"
        self.archive_dir = self.base_dir / "archive"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Ensure workspace and archive directories exist."""
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    # ── Project-scoped workspaces ────────────────────────

    @staticmethod
    def get_project_workspace_path(project_slug: str) -> Path:
        """Get the workspace directory for a project."""
        return WORKSPACES_ROOT / project_slug

    @staticmethod
    def create_project_workspace(project_slug: str, name: str = "", description: str = "") -> Path:
        """Create a new project workspace with all standard subdirectories."""
        path = WORKSPACES_ROOT / project_slug
        path.mkdir(parents=True, exist_ok=True)

        for subdir in PROJECT_SUBDIRS:
            (path / subdir).mkdir(parents=True, exist_ok=True)

        # Write initial project metadata if it doesn't exist
        meta_path = path / ".project-meta" / "project.json"
        if not meta_path.exists():
            meta_path.write_text(
                json.dumps(
                    {
                        "name": name or project_slug,
                        "slug": project_slug,
                        "description": description,
                        "created_at": datetime.now(UTC).isoformat(),
                    },
                    indent=2,
                )
            )

        # Initialize empty knowledge graph if it doesn't exist
        kg_path = path / ".project-meta" / "knowledge.json"
        if not kg_path.exists():
            kg_path.write_text(
                json.dumps(
                    {
                        "nodes": [],
                        "edges": [],
                        "version": 1,
                    },
                    indent=2,
                )
            )

        # Initialize empty state file for cross-conversation persistence
        state_path = path / ".project-meta" / "state.json"
        if not state_path.exists():
            state_path.write_text(
                json.dumps(
                    {
                        "last_conversation_uuid": None,
                        "open_questions": [],
                        "key_findings": [],
                        "active_experiments": [],
                    },
                    indent=2,
                )
            )

        return path

    @staticmethod
    def project_workspace_exists(project_slug: str) -> bool:
        """Check if a project workspace exists."""
        return (WORKSPACES_ROOT / project_slug).exists()

    @staticmethod
    def get_project_workspace_size(project_slug: str) -> int:
        """Get total size of a project workspace in bytes."""
        path = WORKSPACES_ROOT / project_slug
        if not path.exists():
            return 0
        total = 0
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                fp = Path(dirpath) / f
                if fp.exists():
                    total += fp.stat().st_size
        return total

    # ── Legacy conversation-scoped workspaces ────────────

    def get_workspace_path(self, conversation_uuid: str) -> Path:
        """Get the workspace directory for a conversation (legacy mode)."""
        return self.workspace_dir / f"workspace-{conversation_uuid}"

    def create_workspace(self, conversation_uuid: str) -> Path:
        """Create a new workspace directory for a conversation (legacy mode)."""
        path = self.get_workspace_path(conversation_uuid)
        path.mkdir(parents=True, exist_ok=True)
        for subdir in LEGACY_SUBDIRS:
            (path / subdir).mkdir(exist_ok=True)
        return path

    def workspace_exists(self, conversation_uuid: str) -> bool:
        """Check if a conversation workspace exists."""
        return self.get_workspace_path(conversation_uuid).exists()

    def archive_workspace(self, conversation_uuid: str) -> Path | None:
        """Archive a workspace before deletion. Returns archive path."""
        path = self.get_workspace_path(conversation_uuid)
        if not path.exists():
            return None

        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        archive_name = f"workspace-{conversation_uuid}-{timestamp}.tar.gz"
        archive_path = self.archive_dir / archive_name

        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(path, arcname=path.name)

        return archive_path

    def delete_workspace(self, conversation_uuid: str, archive: bool = True) -> bool:
        """Delete a workspace. If archive=True, archive it first."""
        path = self.get_workspace_path(conversation_uuid)
        if not path.exists():
            return False

        if archive:
            self.archive_workspace(conversation_uuid)

        shutil.rmtree(path)
        return True

    def get_workspace_size(self, conversation_uuid: str) -> int:
        """Get total size of a workspace in bytes."""
        path = self.get_workspace_path(conversation_uuid)
        if not path.exists():
            return 0

        total = 0
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                fp = Path(dirpath) / f
                if fp.exists():
                    total += fp.stat().st_size
        return total

    def list_workspaces(self) -> list[dict]:
        """List all conversation workspaces with metadata."""
        workspaces = []
        for path in self.workspace_dir.glob("workspace-*"):
            if path.is_dir():
                uuid = path.name.replace("workspace-", "")
                size = self.get_workspace_size(uuid)
                workspaces.append(
                    {
                        "uuid": uuid,
                        "path": str(path),
                        "size_bytes": size,
                        "created": datetime.fromtimestamp(path.stat().st_ctime, UTC).isoformat(),
                    }
                )
        return sorted(workspaces, key=lambda x: x["created"], reverse=True)

    def cleanup_archives(self, max_age_days: int = 30, max_count: int = 100) -> dict:
        """Clean up old workspace archives."""
        deleted = 0
        freed_bytes = 0

        archives = []
        for path in self.archive_dir.glob("workspace-*.tar.gz"):
            if path.is_file():
                mtime = datetime.fromtimestamp(path.stat().st_mtime, UTC)
                archives.append({"path": path, "mtime": mtime, "size": path.stat().st_size})

        archives.sort(key=lambda x: x["mtime"])

        now = datetime.now(UTC)
        for archive in archives:
            age_days = (now - archive["mtime"]).days
            if age_days > max_age_days:
                freed_bytes += archive["size"]
                archive["path"].unlink()
                deleted += 1

        remaining = [a for a in archives if a["path"].exists()]
        while len(remaining) > max_count:
            oldest = remaining.pop(0)
            freed_bytes += oldest["size"]
            oldest["path"].unlink()
            deleted += 1

        return {"deleted": deleted, "freed_bytes": freed_bytes}

    def cleanup_workspaces(self, conversation_uuids: list[str], archive: bool = True) -> dict:
        """Clean up workspaces for deleted conversations."""
        deleted = 0
        freed_bytes = 0
        keep_set = set(conversation_uuids)

        for path in self.workspace_dir.glob("workspace-*"):
            if not path.is_dir():
                continue
            uuid = path.name.replace("workspace-", "")
            if uuid not in keep_set:
                size = self.get_workspace_size(uuid)
                if archive:
                    self.archive_workspace(uuid)
                shutil.rmtree(path)
                freed_bytes += size
                deleted += 1

        return {"deleted": deleted, "freed_bytes": freed_bytes}
