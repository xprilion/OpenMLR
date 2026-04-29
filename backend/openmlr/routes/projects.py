"""Project routes — CRUD, file tree, file operations.

Security:
- Path traversal prevention via relative_to() (not str.startswith)
- Upload/write size limits
- Symlink-aware rmtree
- No server-side paths leaked to API responses
- Workspace root fallback uses restrictive permissions
"""

import json
import logging
import mimetypes
import os
import re
import shutil
import uuid as uuid_mod
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.security import decode_access_token
from ..db import operations as ops
from ..db.engine import get_db
from ..db.models import User
from ..dependencies import get_current_user, get_current_user_optional

router = APIRouter(prefix="/api/projects", tags=["projects"])

log = logging.getLogger(__name__)

# Size limits
MAX_UPLOAD_BYTES = 100 * 1024 * 1024  # 100 MB
MAX_WRITE_BYTES = 10 * 1024 * 1024  # 10 MB


def _get_workspaces_root() -> Path:
    """Get the workspace root directory, falling back to a temp dir if needed."""
    configured = os.environ.get("OPENMLR_WORKSPACES_PATH")
    if configured:
        return Path(configured)
    default = Path("/app/.workspaces")
    if default.parent.exists():
        return default
    # Fallback for non-Docker environments (tests, native dev)
    import tempfile

    fallback = Path(tempfile.gettempdir()) / "openmlr-workspaces"
    fallback.mkdir(parents=True, exist_ok=True, mode=0o700)
    return fallback


WORKSPACES_ROOT = _get_workspaces_root()

DEFAULT_PROJECT_SLUG = "_default"
DEFAULT_PROJECT_NAME = "All Conversations"


async def get_or_create_default_project(db, user_id: int):
    """Get (or create) the user's default project.

    DEPRECATED: This exists only as a fallback for the terminal route.
    New code should not call this — all conversations must belong to
    a user-created project.
    """
    existing = await ops.get_project_by_slug(db, user_id, DEFAULT_PROJECT_SLUG)
    if existing:
        return existing

    workspace_path = str(WORKSPACES_ROOT / f"user-{user_id}" / DEFAULT_PROJECT_SLUG)
    _ensure_workspace(workspace_path)

    project = await ops.create_project(
        db,
        user_id,
        DEFAULT_PROJECT_NAME,
        DEFAULT_PROJECT_SLUG,
        description="Default workspace (legacy fallback)",
        workspace_path=workspace_path,
        settings={"is_default": True},
    )
    return project


def _slugify(name: str) -> str:
    """Generate a filesystem-safe slug from a project name."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:60] or "project"


def _project_dict(project, conv_count: int | None = None) -> dict:
    """Serialize a project for the API. No server-side paths exposed."""
    d = {
        "id": project.id,
        "uuid": project.uuid,
        "name": project.name,
        "slug": project.slug,
        "description": project.description,
        "status": project.status,
        "settings": project.settings or {},
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
    }
    if conv_count is not None:
        d["conversation_count"] = conv_count
    return d


def _ensure_workspace(workspace_path: str) -> Path:
    """Ensure workspace directory and standard subdirs exist."""
    ws = Path(workspace_path)
    ws.mkdir(parents=True, exist_ok=True)
    for subdir in [
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
    ]:
        (ws / subdir).mkdir(parents=True, exist_ok=True)
    return ws


def _safe_resolve(workspace_path: str, relative_path: str) -> Path:
    """Resolve a relative path within the workspace, preventing traversal attacks.

    Uses Path.relative_to() for correct containment checking (not str.startswith).
    """
    ws = Path(workspace_path).resolve()
    target = (ws / relative_path).resolve()
    try:
        target.relative_to(ws)
    except ValueError:
        raise HTTPException(status_code=400, detail="Path traversal not allowed")
    return target


def _safe_rmtree(target: Path, workspace_path: str) -> None:
    """Remove a directory tree, refusing to follow symlinks that escape the workspace."""
    ws = Path(workspace_path).resolve()

    # Check for symlinks that point outside workspace before deleting
    for root, dirs, files in os.walk(str(target)):
        root_path = Path(root)
        for name in dirs + files:
            item = root_path / name
            if item.is_symlink():
                link_target = item.resolve()
                try:
                    link_target.relative_to(ws)
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot delete: contains symlink to outside workspace",
                    )

    shutil.rmtree(target)


# ── Project CRUD ─────────────────────────────────────────


@router.get("")
async def list_projects(
    include_archived: bool = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all projects for the current user. Excludes the legacy default project."""
    projects = await ops.get_user_projects(db, user.id, include_archived=include_archived)
    result = []
    for p in projects:
        # Skip the legacy default project — it shouldn't appear in the UI
        if p.settings and p.settings.get("is_default"):
            continue
        convs = await ops.get_project_conversations(db, p.id)
        d = _project_dict(p, conv_count=len(convs))
        result.append(d)
    return {"projects": result}


@router.post("")
async def create_project(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new project with a workspace directory."""
    body = await request.json()
    name = body.get("name", "").strip()
    description = body.get("description", "").strip() or None

    if not name:
        raise HTTPException(status_code=400, detail="Missing 'name'")

    slug = _slugify(name)

    # Check for duplicate slug
    existing = await ops.get_project_by_slug(db, user.id, slug)
    if existing:
        slug = f"{slug}-{str(uuid_mod.uuid4())[:6]}"

    # Create workspace directory
    workspace_path = str(WORKSPACES_ROOT / slug)
    _ensure_workspace(workspace_path)

    # Write initial project metadata
    meta_path = Path(workspace_path) / ".project-meta" / "project.json"
    meta_path.write_text(
        json.dumps(
            {
                "name": name,
                "slug": slug,
                "description": description,
                "created_by": user.username,
            },
            indent=2,
        )
    )

    # Initialize empty knowledge graph
    kg_path = Path(workspace_path) / ".project-meta" / "knowledge.json"
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

    project = await ops.create_project(
        db,
        user.id,
        name,
        slug,
        description=description,
        workspace_path=workspace_path,
        settings=body.get("settings"),
    )

    return {"project": _project_dict(project, conv_count=0)}


@router.get("/{project_uuid}")
async def get_project(
    project_uuid: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get project details including conversation count."""
    project = await ops.get_project_by_uuid(db, project_uuid, user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    convs = await ops.get_project_conversations(db, project.id)
    return {"project": _project_dict(project, conv_count=len(convs))}


@router.put("/{project_uuid}")
async def update_project(
    project_uuid: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update project name, description, or settings."""
    project = await ops.get_project_by_uuid(db, project_uuid, user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    is_default = project.settings and project.settings.get("is_default")

    body = await request.json()
    updates = {}
    if "name" in body:
        if is_default:
            raise HTTPException(status_code=400, detail="Cannot rename the default project")
        updates["name"] = body["name"].strip()
    if "description" in body:
        updates["description"] = body["description"].strip() or None
    if "settings" in body:
        # Prevent removing the is_default flag
        new_settings = body["settings"]
        if is_default and isinstance(new_settings, dict):
            new_settings["is_default"] = True
        updates["settings"] = new_settings

    updated = await ops.update_project(db, project.id, user.id, **updates)
    return {"project": _project_dict(updated)}


@router.delete("/{project_uuid}")
async def delete_project(
    project_uuid: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Archive a project (soft delete). Workspace files are preserved."""
    project = await ops.get_project_by_uuid(db, project_uuid, user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await ops.archive_project(db, project.id, user.id)
    return {"ok": True}


@router.get("/{project_uuid}/conversations")
async def list_project_conversations(
    project_uuid: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all conversations within a project."""
    project = await ops.get_project_by_uuid(db, project_uuid, user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    convs = await ops.get_project_conversations(db, project.id)
    return {
        "conversations": [
            {
                "id": c.id,
                "uuid": c.uuid,
                "title": c.title,
                "model": c.model,
                "mode": c.mode,
                "user_message_count": c.user_message_count,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            }
            for c in convs
        ]
    }


@router.post("/{project_uuid}/attach/{conversation_uuid}")
async def attach_conversation(
    project_uuid: str,
    conversation_uuid: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Attach an existing conversation to a project."""
    project = await ops.get_project_by_uuid(db, project_uuid, user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    conv = await ops.get_conversation_by_uuid(db, conversation_uuid)
    if not conv or conv.user_id != user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await ops.attach_conversation_to_project(db, conv.id, project.id, user.id)
    return {"ok": True}


@router.post("/{project_uuid}/detach/{conversation_uuid}")
async def detach_conversation(
    project_uuid: str,
    conversation_uuid: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Detach a conversation from a project."""
    # Verify both project and conversation ownership
    project = await ops.get_project_by_uuid(db, project_uuid, user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    conv = await ops.get_conversation_by_uuid(db, conversation_uuid)
    if not conv or conv.user_id != user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await ops.attach_conversation_to_project(db, conv.id, None, user.id)
    return {"ok": True}


# ── File Tree & File Operations ──────────────────────────


@router.get("/{project_uuid}/files")
async def list_files(
    project_uuid: str,
    path: str = "",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List files and directories in the project workspace."""
    project = await ops.get_project_by_uuid(db, project_uuid, user.id)
    if not project or not project.workspace_path:
        raise HTTPException(status_code=404, detail="Project not found")

    target = _safe_resolve(project.workspace_path, path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Not a directory")

    entries = []
    try:
        for item in sorted(
            target.iterdir(),
            key=lambda p: (not p.is_dir(), p.name.lower()),
        ):
            # Skip hidden files except .project-meta
            if item.name.startswith(".") and item.name != ".project-meta":
                continue
            try:
                stat = item.stat(follow_symlinks=False)
            except OSError:
                continue
            entries.append(
                {
                    "name": item.name,
                    "path": str(item.relative_to(Path(project.workspace_path))),
                    "is_dir": item.is_dir(),
                    "size": stat.st_size if item.is_file() else None,
                    "modified": stat.st_mtime,
                }
            )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="Permission denied") from exc

    return {"path": path, "entries": entries}


async def _get_user_from_token_param(token: str | None, db: AsyncSession) -> User | None:
    """Resolve a user from a query-string token (for img/binary loads)."""
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    result = await db.execute(
        select(User).where(User.id == int(payload["sub"]), User.is_active == True)
    )
    return result.scalar_one_or_none()


@router.get("/{project_uuid}/files/{file_path:path}")
async def read_file(
    project_uuid: str,
    file_path: str,
    token: str | None = Query(None),
    user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Read a file from the project workspace.

    Supports auth via Bearer header or ?token= query param (for <img> tags).
    """
    # Fall back to token query param (for image tags that can't set headers)
    if user is None and token:
        user = await _get_user_from_token_param(token, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    project = await ops.get_project_by_uuid(db, project_uuid, user.id)
    if not project or not project.workspace_path:
        raise HTTPException(status_code=404, detail="Project not found")

    target = _safe_resolve(project.workspace_path, file_path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    if target.is_dir():
        return await list_files(project_uuid, file_path, user, db)

    # Reject symlinks that point outside workspace
    if target.is_symlink():
        try:
            target.resolve().relative_to(Path(project.workspace_path).resolve())
        except ValueError:
            raise HTTPException(status_code=400, detail="Symlink points outside workspace")

    # For text files, return content as JSON
    mime, _ = mimetypes.guess_type(str(target))
    is_text = (
        mime is None
        or mime.startswith("text/")
        or mime in ("application/json", "application/xml", "application/x-yaml")
    )

    if is_text:
        try:
            content = target.read_text(encoding="utf-8", errors="replace")
            if len(content) > 500_000:
                content = content[:500_000] + "\n\n[... truncated at 500KB ...]"
            return {
                "path": file_path,
                "content": content,
                "size": target.stat().st_size,
            }
        except Exception:
            pass

    return FileResponse(str(target), filename=target.name)


@router.put("/{project_uuid}/files/{file_path:path}")
async def write_file(
    project_uuid: str,
    file_path: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Write content to a file in the project workspace."""
    project = await ops.get_project_by_uuid(db, project_uuid, user.id)
    if not project or not project.workspace_path:
        raise HTTPException(status_code=404, detail="Project not found")

    target = _safe_resolve(project.workspace_path, file_path)

    body = await request.json()
    content = body.get("content", "")

    # Enforce write size limit
    if len(content) > MAX_WRITE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Content too large (max {MAX_WRITE_BYTES // 1024 // 1024}MB)",
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")

    return {"ok": True, "path": file_path, "size": target.stat().st_size}


@router.delete("/{project_uuid}/files/{file_path:path}")
async def delete_file(
    project_uuid: str,
    file_path: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a file or directory from the project workspace."""
    project = await ops.get_project_by_uuid(db, project_uuid, user.id)
    if not project or not project.workspace_path:
        raise HTTPException(status_code=404, detail="Project not found")

    target = _safe_resolve(project.workspace_path, file_path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")

    # Prevent deleting top-level standard dirs
    ws = Path(project.workspace_path)
    rel = target.relative_to(ws)
    protected = {
        "code",
        "data",
        "models",
        "outputs",
        "papers",
        "research",
        "logs",
        ".project-meta",
    }
    if str(rel) in protected:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete standard workspace directory",
        )

    if target.is_dir():
        _safe_rmtree(target, project.workspace_path)
    else:
        target.unlink()

    return {"ok": True}


@router.post("/{project_uuid}/upload/{file_path:path}")
async def upload_file(
    project_uuid: str,
    file_path: str,
    file: UploadFile,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a file to the project workspace."""
    project = await ops.get_project_by_uuid(db, project_uuid, user.id)
    if not project or not project.workspace_path:
        raise HTTPException(status_code=404, detail="Project not found")

    target = _safe_resolve(project.workspace_path, file_path)

    # Read with size limit to prevent OOM
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {MAX_UPLOAD_BYTES // 1024 // 1024}MB)",
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)

    return {"ok": True, "path": file_path, "size": len(content)}
