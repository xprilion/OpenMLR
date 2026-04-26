"""Workspace Manager — per-conversation filesystem isolation."""

import os
import shutil
import tarfile
from datetime import UTC, datetime
from pathlib import Path


class WorkspaceManager:
    """Manages isolated workspace directories for each conversation."""

    def __init__(self, base_dir: str | Path = None):
        self.base_dir = Path(base_dir) if base_dir else Path.home() / ".openmlr"
        self.workspace_dir = self.base_dir / "workspaces"
        self.archive_dir = self.base_dir / "archive"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Ensure workspace and archive directories exist."""
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    def get_workspace_path(self, conversation_uuid: str) -> Path:
        """Get the workspace directory for a conversation."""
        return self.workspace_dir / f"workspace-{conversation_uuid}"

    def create_workspace(self, conversation_uuid: str) -> Path:
        """Create a new workspace directory for a conversation."""
        path = self.get_workspace_path(conversation_uuid)
        path.mkdir(parents=True, exist_ok=True)
        # Create standard subdirectories
        for subdir in ["data", "models", "code", "outputs"]:
            (path / subdir).mkdir(exist_ok=True)
        # Create meta directory (hidden from agent)
        (path / ".openmlr-meta").mkdir(exist_ok=True)
        return path

    def workspace_exists(self, conversation_uuid: str) -> bool:
        """Check if a workspace exists."""
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
        """List all workspaces with metadata."""
        workspaces = []
        for path in self.workspace_dir.glob("workspace-*"):
            if path.is_dir():
                uuid = path.name.replace("workspace-", "")
                size = self.get_workspace_size(uuid)
                workspaces.append({
                    "uuid": uuid,
                    "path": str(path),
                    "size_bytes": size,
                    "created": datetime.fromtimestamp(path.stat().st_ctime, UTC).isoformat(),
                })
        return sorted(workspaces, key=lambda x: x["created"], reverse=True)

    def cleanup_archives(self, max_age_days: int = 30, max_count: int = 100) -> dict:
        """Clean up old workspace archives.

        Args:
            max_age_days: Delete archives older than this many days
            max_count: Keep at most this many archives, delete oldest first

        Returns:
            Dict with deleted count and freed bytes
        """
        deleted = 0
        freed_bytes = 0

        # Get all archives sorted by modification time (oldest first)
        archives = []
        for path in self.archive_dir.glob("workspace-*.tar.gz"):
            if path.is_file():
                mtime = datetime.fromtimestamp(path.stat().st_mtime, UTC)
                archives.append({"path": path, "mtime": mtime, "size": path.stat().st_size})

        archives.sort(key=lambda x: x["mtime"])

        # Delete old archives
        now = datetime.now(UTC)
        for archive in archives:
            age_days = (now - archive["mtime"]).days
            if age_days > max_age_days:
                freed_bytes += archive["size"]
                archive["path"].unlink()
                deleted += 1

        # Delete excess archives (oldest first)
        remaining = [a for a in archives if a["path"].exists()]
        while len(remaining) > max_count:
            oldest = remaining.pop(0)
            freed_bytes += oldest["size"]
            oldest["path"].unlink()
            deleted += 1

        return {"deleted": deleted, "freed_bytes": freed_bytes}

    def cleanup_workspaces(self, conversation_uuids: list[str], archive: bool = True) -> dict:
        """Clean up workspaces for deleted conversations.

        Args:
            conversation_uuids: List of conversation UUIDs to keep
            archive: Whether to archive before deleting

        Returns:
            Dict with deleted count and freed bytes
        """
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
