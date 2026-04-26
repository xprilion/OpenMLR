"""SSH Key routes — CRUD for key assets stored in .keys/."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import operations as ops
from ..db.engine import get_db
from ..db.models import User
from ..dependencies import get_current_user
from ..keys import KeyManager

router = APIRouter(prefix="/api", tags=["keys"])

key_manager = KeyManager()


@router.get("/keys")
async def list_keys(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all SSH key metadata for the current user."""
    keys = await ops.get_ssh_keys(db, user.id)
    return {
        "keys": [
            {
                "id": k.id,
                "filename": k.filename,
                "fingerprint": k.fingerprint,
                "algorithm": k.algorithm,
                "comment": k.comment,
                "created_at": k.created_at.isoformat() if k.created_at else None,
            }
            for k in keys
        ]
    }


@router.post("/keys")
async def create_key(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload or generate an SSH key pair."""
    body = await request.json()
    action = body.get("action")
    filename = body.get("filename", "")

    if not filename:
        raise HTTPException(status_code=400, detail="Missing 'filename'")

    # Prevent path traversal in filename
    from pathlib import Path as PyPath
    safe_filename = PyPath(filename).name
    if not safe_filename or safe_filename.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")

    existing = await ops.get_ssh_key_by_filename(db, user.id, safe_filename)
    if existing:
        raise HTTPException(status_code=409, detail=f"Key '{safe_filename}' already exists")

    if action == "upload":
        private_key = body.get("private_key", "")
        if not private_key:
            raise HTTPException(status_code=400, detail="Missing 'private_key' for upload")

        try:
            meta = key_manager.validate_key(private_key)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid key: {e}")

        key_manager.write_key(safe_filename, private_key)

    elif action == "generate":
        algorithm = body.get("algorithm", "ed25519")
        comment = body.get("comment", f"openmlr-{user.id}")
        try:
            key_path, pub_path = key_manager.generate_key_pair(safe_filename, algorithm, comment)
            private_key = key_path.read_text()
            meta = key_manager.validate_key(private_key)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    else:
        raise HTTPException(status_code=400, detail="action must be 'upload' or 'generate'")

    key = await ops.create_ssh_key(
        db, user.id, safe_filename, meta["fingerprint"],
        meta["algorithm"], meta["public_key"], body.get("comment"),
    )

    return {
        "key": {
            "id": key.id,
            "filename": key.filename,
            "fingerprint": key.fingerprint,
            "algorithm": key.algorithm,
            "public_key": key.public_key,
            "comment": key.comment,
            "created_at": key.created_at.isoformat() if key.created_at else None,
        }
    }


@router.delete("/keys/{filename}")
async def delete_key(
    filename: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an SSH key and its public counterpart."""
    # Sanitize filename to prevent path traversal
    from pathlib import Path as PyPath
    safe_filename = PyPath(filename).name
    if not safe_filename or safe_filename != filename or safe_filename.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")
    filename = safe_filename

    # Check if any compute nodes reference this key
    nodes = await ops.get_compute_nodes(db, user.id)
    dependent_nodes = [n for n in nodes if n.config.get("key_filename") == filename]

    if dependent_nodes:
        node_names = ", ".join(n.name for n in dependent_nodes)
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete key: used by compute nodes: {node_names}"
        )

    deleted_db = await ops.delete_ssh_key(db, user.id, filename)
    if not deleted_db:
        raise HTTPException(status_code=404, detail="Key not found")

    key_manager.delete_key(filename)
    return {"ok": True}
