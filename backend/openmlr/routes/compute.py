"""Compute Node routes — CRUD, testing, probing, and defaults."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..compute import ComputeManager
from ..db import operations as ops
from ..db.engine import get_db
from ..db.models import User
from ..dependencies import get_current_user
from ..keys import KeyManager

router = APIRouter(prefix="/api/compute", tags=["compute"])

key_manager = KeyManager()
compute_manager = ComputeManager(key_manager)

# Fields to redact from config before sending to the frontend
_SENSITIVE_CONFIG_KEYS = {"password", "private_key", "secret", "token"}


def _redact_config(config: dict) -> dict:
    """Return config with sensitive fields masked."""
    if not config:
        return {}
    redacted = {}
    for k, v in config.items():
        if k in _SENSITIVE_CONFIG_KEYS and v:
            redacted[k] = "***"
        else:
            redacted[k] = v
    return redacted


def _node_dict(node) -> dict:
    return {
        "id": node.id,
        "name": node.name,
        "type": node.type,
        "config": _redact_config(node.config),
        "capabilities": node.capabilities or {},
        "health_status": node.health_status,
        "last_probed_at": node.last_probed_at.isoformat() if node.last_probed_at else None,
        "last_seen_at": node.last_seen_at.isoformat() if node.last_seen_at else None,
        "is_default": node.is_default,
        "priority": node.priority,
        "created_at": node.created_at.isoformat() if node.created_at else None,
        "updated_at": node.updated_at.isoformat() if node.updated_at else None,
    }


# ── Compute Nodes ────────────────────────────────────────


@router.get("/nodes")
async def list_nodes(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all compute nodes for the current user."""
    nodes = await ops.get_compute_nodes(db, user.id)
    return {"nodes": [_node_dict(n) for n in nodes]}


@router.post("/nodes")
async def create_node(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new compute node."""
    body = await request.json()
    name = body.get("name", "").strip()
    node_type = body.get("type", "").strip()
    config = body.get("config", {})
    is_default = body.get("is_default", False)
    priority = body.get("priority", 0)

    if not name:
        raise HTTPException(status_code=400, detail="Missing 'name'")
    if node_type not in ("local", "ssh", "modal"):
        raise HTTPException(status_code=400, detail="type must be 'local', 'ssh', or 'modal'")

    # Validate config
    valid, error = compute_manager.validate_node_config(node_type, config)
    if not valid:
        raise HTTPException(status_code=400, detail=error)

    # Check for duplicate name
    existing = await ops.get_compute_node_by_name(db, user.id, name)
    if existing:
        raise HTTPException(status_code=409, detail=f"Node '{name}' already exists")

    # If setting as default, clear existing default
    if is_default:
        await ops.set_default_compute_node(db, user.id, None)

    node = await ops.create_compute_node(
        db,
        user.id,
        name,
        node_type,
        config,
        is_default=is_default,
        priority=priority,
    )

    return {"node": _node_dict(node)}


@router.get("/nodes/{node_id}")
async def get_node(
    node_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single compute node."""
    node = await ops.get_compute_node_by_id(db, node_id, user.id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return {"node": _node_dict(node)}


@router.put("/nodes/{node_id}")
async def update_node(
    node_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a compute node's configuration."""
    body = await request.json()
    node = await ops.get_compute_node_by_id(db, node_id, user.id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    updates = {}
    if "name" in body:
        new_name = body["name"].strip()
        if new_name and new_name != node.name:
            existing = await ops.get_compute_node_by_name(db, user.id, new_name)
            if existing:
                raise HTTPException(status_code=409, detail=f"Node '{new_name}' already exists")
        updates["name"] = new_name

    if "config" in body:
        config = body["config"]
        valid, error = compute_manager.validate_node_config(node.type, config)
        if not valid:
            raise HTTPException(status_code=400, detail=error)
        updates["config"] = config

    if "priority" in body:
        updates["priority"] = int(body["priority"])

    if "is_default" in body:
        if body["is_default"]:
            await ops.set_default_compute_node(db, user.id, None)
        updates["is_default"] = bool(body["is_default"])

    updated = await ops.update_compute_node(db, node_id, user.id, **updates)
    return {"node": _node_dict(updated)}


@router.delete("/nodes/{node_id}")
async def delete_node(
    node_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a compute node."""
    deleted = await ops.delete_compute_node(db, node_id, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Node not found")
    return {"ok": True}


@router.post("/nodes/{node_id}/set-default")
async def set_default_node(
    node_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Set a compute node as the user's default."""
    node = await ops.get_compute_node_by_id(db, node_id, user.id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    await ops.set_default_compute_node(db, user.id, node_id)
    return {"ok": True}


@router.post("/nodes/{node_id}/test")
async def test_node(
    node_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Test connectivity to a compute node (lightweight)."""
    node = await ops.get_compute_node_by_id(db, node_id, user.id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    if node.type == "ssh":
        return await _test_ssh_node(node)
    elif node.type == "local":
        return await _test_local_node(node)
    elif node.type == "modal":
        return await _test_modal_node(node)

    return {"ok": False, "error": "Unknown node type"}


@router.post("/test")
async def test_node_config(
    request: Request,
    user: User = Depends(get_current_user),
):
    """Test connectivity for an unsaved node config.

    Used before creating a node so the user can verify credentials work.
    """
    body = await request.json()
    node_type = body.get("type", "")
    config = body.get("config", {})

    if node_type not in ("local", "ssh", "modal"):
        return {"ok": False, "error": "Invalid node type"}

    # Build a lightweight mock object that _test_* functions can read
    class _MockNode:
        def __init__(self, t, c):
            self.type = t
            self.config = c

    mock = _MockNode(node_type, config)

    if node_type == "ssh":
        return await _test_ssh_node(mock)
    elif node_type == "local":
        return await _test_local_node(mock)
    elif node_type == "modal":
        return await _test_modal_node(mock)

    return {"ok": False, "error": "Unknown node type"}


@router.post("/nodes/{node_id}/probe")
async def probe_node(
    node_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deep capability discovery for a compute node."""
    node = await ops.get_compute_node_by_id(db, node_id, user.id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    from ..compute import WorkspaceManager
    from ..compute.probe import probe_sandbox
    from ..sandbox.manager import SandboxManager

    try:
        wm = WorkspaceManager()
        sm = SandboxManager(workspace_manager=wm)
        await sm.create(node.type, node.config)
        sandbox = sm.get_active()

        if not sandbox:
            raise RuntimeError("Failed to create sandbox")

        caps = await probe_sandbox(sandbox)

        # Update node in database
        await ops.update_compute_node(
            db,
            node.id,
            user.id,
            capabilities=caps.to_dict(),
            health_status="online",
            last_probed_at=datetime.now(UTC),
        )

        await sm.destroy()

        return {
            "ok": True,
            "capabilities": caps.to_dict(),
        }

    except Exception as e:
        await ops.update_compute_node(
            db,
            node.id,
            user.id,
            health_status="offline",
        )
        return {"ok": False, "error": str(e)}


async def _test_ssh_node(node):
    """Test SSH connectivity and retrieve host key fingerprint if not set."""
    import asyncio

    import paramiko

    config = node.config
    host = config.get("host", "")
    port = config.get("port", 22)
    username = config.get("username", "")
    key_filename = config.get("key_filename")
    password = config.get("password")

    try:

        def _do_test():
            client = paramiko.SSHClient()
            # Use WarningPolicy to get host key without auto-adding
            client.set_missing_host_key_policy(paramiko.WarningPolicy())

            connect_kwargs = {
                "hostname": host,
                "port": port,
                "username": username,
                "timeout": 10,
            }

            if key_filename:
                key_path = key_manager.get_key_path(key_filename)
                connect_kwargs["key_filename"] = str(key_path)
            elif password:
                connect_kwargs["password"] = password

            try:
                client.connect(**connect_kwargs)
            except paramiko.SSHException as e:
                # If host key is unknown, paramiko raises an exception with WarningPolicy
                # We need to extract the host key from the transport
                transport = client.get_transport()
                if transport:
                    transport.close()
                raise e

            # Get host key fingerprint
            transport = client.get_transport()
            host_key = transport.get_remote_server_key()
            fingerprint = host_key.get_fingerprint().hex()

            # Run a simple command
            stdin, stdout, stderr = client.exec_command("echo ok", timeout=5)
            exit_code = stdout.channel.recv_exit_status()
            output = stdout.read().decode("utf-8", errors="replace").strip()

            client.close()

            return {
                "connected": exit_code == 0 and output == "ok",
                "host_key_fingerprint": fingerprint,
                "output": output,
            }

        result = await asyncio.to_thread(_do_test)
        return {
            "ok": result["connected"],
            "host_key_fingerprint": result.get("host_key_fingerprint"),
            "message": "Connected successfully"
            if result["connected"]
            else f"Unexpected output: {result['output']}",
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}


async def _test_local_node(node):
    """Test local workspace directory."""
    import os
    from pathlib import Path

    config = node.config
    workdir = config.get("workdir", "")
    if not workdir:
        workdir = os.getcwd()

    path = Path(workdir).expanduser()
    if path.exists() and path.is_dir():
        return {"ok": True, "message": f"Workspace ready: {path}"}
    else:
        return {"ok": False, "error": f"Workspace not found: {path}"}


async def _test_modal_node(node):
    """Test Modal connectivity."""
    try:
        import importlib.util

        if importlib.util.find_spec("modal") is not None:
            return {"ok": True, "message": "Modal client available"}
        return {"ok": False, "error": "Modal client not installed"}
    except Exception:
        return {"ok": False, "error": "Modal client not installed"}
