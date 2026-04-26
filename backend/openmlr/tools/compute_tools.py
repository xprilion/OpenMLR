"""Compute tools — agent-facing tools for compute node discovery and selection."""

import asyncio
import io
import os
from datetime import UTC, datetime
from pathlib import Path

from ..agent.types import ToolSpec
from ..compute.probe import probe_sandbox


def _validate_sync_path(workspace: Path, rel_path: str) -> tuple[Path, str | None]:
    """Validate that a relative path stays within the workspace. Returns (resolved, error)."""
    target = (workspace / rel_path).resolve()
    try:
        target.relative_to(workspace.resolve())
    except ValueError:
        return target, f"Path '{rel_path}' escapes workspace boundary"
    return target, None


async def _handle_list(user_id: int = None, db=None, **kwargs):
    """List all compute nodes with capabilities."""
    if not db:
        return "Database connection required for compute_list", False

    from ..db import operations as ops
    nodes = await ops.get_compute_nodes(db, user_id)

    if not nodes:
        return "No compute nodes configured. Add nodes in Settings > Compute.", True

    lines = ["## Available Compute Nodes\n"]
    for node in nodes:
        caps = node.capabilities or {}
        status = "●" if node.health_status == "online" else "○"
        gpu = ""
        if caps.get("gpu_available"):
            gpu_info = caps.get("gpu_info", [])
            if gpu_info:
                gpu = f" — GPU: {gpu_info[0].get('model', 'unknown')}"
            else:
                gpu = " — GPU: yes"

        ram = ""
        if caps.get("available_ram_gb"):
            ram = f" — RAM: {caps['available_ram_gb']:.0f}GB"

        default = " ★" if node.is_default else ""
        lines.append(f"{status} {node.name} ({node.type}){default}{gpu}{ram}")

    return "\n".join(lines), True


async def _handle_probe(node_name: str, user_id: int = None, db=None, **kwargs):
    """Probe a compute node for capabilities."""
    if not db:
        return "Database connection required for compute_probe", False

    from ..db import operations as ops
    node = await ops.get_compute_node_by_name(db, user_id, node_name)
    if not node:
        return f"Node '{node_name}' not found", False

    # Create sandbox and probe
    from ..compute import WorkspaceManager
    from ..sandbox.manager import SandboxManager

    try:
        wm = WorkspaceManager()
        sm = SandboxManager(workspace_manager=wm)
        await sm.create(node.type, node.config)
        sandbox = sm.get_active()
        if not sandbox:
            return f"Failed to create sandbox for {node_name}", False

        caps = await probe_sandbox(sandbox)

        # Update node in database
        await ops.update_compute_node(
            db, node.id, user_id,
            capabilities=caps.to_dict(),
            health_status="online",
            last_probed_at=datetime.now(UTC),
        )

        await sm.destroy()

        # Format response
        lines = [f"## {node.name} Capabilities\n"]
        lines.append(f"Platform: {caps.platform}")
        lines.append(f"CPU: {caps.cpu_cores} cores ({caps.cpu_arch})")
        lines.append(f"RAM: {caps.available_ram_gb:.1f} GB available / {caps.total_ram_gb:.1f} GB total")
        lines.append(f"Disk: {caps.available_disk_gb:.1f} GB available / {caps.total_disk_gb:.1f} GB total")

        if caps.gpu_available:
            for gpu in caps.gpu_info:
                lines.append(f"GPU: {gpu.model} ({gpu.vram_gb:.0f} GB VRAM)")
                if gpu.cuda_version:
                    lines.append(f"  CUDA: {gpu.cuda_version}, Driver: {gpu.driver_version}")

        if caps.python_versions:
            lines.append(f"Python: {', '.join(caps.python_versions)}")

        if caps.docker_available:
            lines.append("Docker: available")

        if caps.installed_packages:
            lines.append(f"\nKey packages: {', '.join(caps.installed_packages[:10])}")
            if len(caps.installed_packages) > 10:
                lines.append(f"... and {len(caps.installed_packages) - 10} more")

        return "\n".join(lines), True

    except Exception as e:
        try:
            await sm.destroy()
        except Exception:
            pass
        await ops.update_compute_node(
            db, node.id, user_id,
            health_status="offline",
        )
        return f"Probe failed for {node_name}: {str(e)}", False


async def _handle_select(node_name: str, user_id: int = None, db=None, session=None, **kwargs):
    """Select a compute node as active for this conversation."""
    if not db:
        return "Database connection required for compute_select", False

    from ..db import operations as ops
    node = await ops.get_compute_node_by_name(db, user_id, node_name)
    if not node:
        return f"Node '{node_name}' not found", False

    # If session is provided, update the active sandbox
    if session and hasattr(session, 'conversation_id'):
        # Update conversation extra
        conv_id = session.conversation_id
        conv = await ops.get_conversation_by_id(db, conv_id)
        if conv:
            extra = conv.extra or {}
            extra["compute_node_id"] = node.id
            extra["compute_node_name"] = node.name
            await ops.update_conversation_extra(db, conv_id, extra)

    return f"Active compute switched to: {node.name} ({node.type})", True


async def _handle_plan(task: str, requirements: dict = None, user_id: int = None, db=None, **kwargs):
    """Recommend the best compute node for a task."""
    if not db:
        return "Database connection required for compute_plan", False

    requirements = requirements or {}
    from ..db import operations as ops
    nodes = await ops.get_compute_nodes(db, user_id)

    if not nodes:
        return "No compute nodes configured.", False

    # Score each node
    scores = []
    for node in nodes:
        if node.health_status != "online":
            continue

        caps = node.capabilities or {}
        score = 0
        reasons = []

        # GPU requirement
        if requirements.get("gpu"):
            if not caps.get("gpu_available"):
                continue
            score += 10
            vram = 0
            for gpu in caps.get("gpu_info", []):
                vram = max(vram, gpu.get("vram_gb", 0))
            min_vram = requirements.get("min_vram_gb", 0)
            if vram < min_vram:
                continue
            score += min(vram / 10, 5)
            reasons.append(f"GPU with {vram:.0f}GB VRAM")

        # RAM requirement
        min_ram = requirements.get("min_ram_gb", 0)
        available_ram = caps.get("available_ram_gb", 0)
        if available_ram < min_ram:
            continue
        score += min(available_ram / max(min_ram, 1), 3)
        if available_ram > 0:
            reasons.append(f"{available_ram:.0f}GB RAM")

        # Disk requirement
        min_disk = requirements.get("min_disk_gb", 0)
        available_disk = caps.get("available_disk_gb", 0)
        if available_disk < min_disk:
            continue
        if available_disk > 0:
            reasons.append(f"{available_disk:.0f}GB disk")

        # Prefer local > ssh > modal
        if node.type == "local":
            score += 5
            reasons.append("local (low latency)")
        elif node.type == "ssh":
            score += 2
            reasons.append("ssh (LAN)")
        elif node.type == "modal":
            reasons.append("modal (cloud)")

        scores.append({
            "node": node,
            "score": score,
            "reasons": reasons,
        })

    if not scores:
        return "No compute nodes meet the requirements.", False

    scores.sort(key=lambda x: x["score"], reverse=True)
    best = scores[0]

    lines = [f"## Recommended Compute for: {task}\n"]
    lines.append(f"**Best choice: {best['node'].name}** ({best['node'].type})")
    lines.append(f"Score: {best['score']:.1f}")
    lines.append(f"Reasons: {', '.join(best['reasons'])}")

    if len(scores) > 1:
        lines.append("\n### Alternatives")
        for alt in scores[1:3]:
            lines.append(f"- {alt['node'].name} (score: {alt['score']:.1f}, {', '.join(alt['reasons'])})")

    return "\n".join(lines), True


async def _get_sync_context(user_id, db, session):
    """Helper: resolve conversation UUID and workspace path for sync ops."""
    from ..db import operations as ops
    conv_uuid = None
    if session and hasattr(session, 'conversation_id'):
        conv = await ops.get_conversation_by_id(db, session.conversation_id)
        if conv:
            conv_uuid = conv.uuid
    if not conv_uuid:
        return None, None, "No active conversation workspace found"
    from ..compute import WorkspaceManager
    wm = WorkspaceManager()
    local_ws = wm.get_workspace_path(conv_uuid)
    return conv_uuid, local_ws, None


async def _handle_sync_up(paths: list, node_name: str, user_id: int = None, db=None, session=None, **kwargs):
    """Sync files from local workspace to remote compute node."""
    if not db:
        return "Database connection required", False

    from ..db import operations as ops
    node = await ops.get_compute_node_by_name(db, user_id, node_name)
    if not node:
        return f"Node '{node_name}' not found", False

    conv_uuid, local_ws, err = await _get_sync_context(user_id, db, session)
    if err:
        return err, False
    if not local_ws.exists():
        return f"Local workspace not found: {local_ws}", False

    if node.type == "local":
        return "Local sync: files are already in the same workspace", True

    elif node.type == "ssh":
        from ..sandbox.ssh import SSHSandbox
        ssh_sandbox = SSHSandbox()
        try:
            config = dict(node.config)
            config["conversation_uuid"] = conv_uuid
            await ssh_sandbox.create(config)

            transferred = 0
            for rel_path in paths:
                # Path traversal check
                local_path, path_err = _validate_sync_path(local_ws, rel_path)
                if path_err:
                    return path_err, False
                if not local_path.exists():
                    continue

                remote_base = ssh_sandbox.workdir

                if local_path.is_dir():
                    for root, _, files in os.walk(local_path):
                        for file in files:
                            src = Path(root) / file
                            rel = src.relative_to(local_ws)
                            dst = f"{remote_base}/{rel}"
                            dst_dir = str(Path(dst).parent)
                            await ssh_sandbox.execute(f"mkdir -p '{dst_dir}'", timeout=5)
                            content = src.read_bytes()
                            await asyncio.to_thread(
                                lambda d=dst, c=content: ssh_sandbox._sftp.putfo(io.BytesIO(c), d)
                            )
                            transferred += 1
                else:
                    rel = local_path.relative_to(local_ws)
                    dst = f"{remote_base}/{rel}"
                    dst_dir = str(Path(dst).parent)
                    await ssh_sandbox.execute(f"mkdir -p '{dst_dir}'", timeout=5)
                    content = local_path.read_bytes()
                    await asyncio.to_thread(
                        lambda d=dst, c=content: ssh_sandbox._sftp.putfo(io.BytesIO(c), d)
                    )
                    transferred += 1

            return f"Synced {transferred} item(s) to {node.name}", True
        except Exception as e:
            return f"Sync failed: {str(e)}", False
        finally:
            await ssh_sandbox.destroy()

    elif node.type == "modal":
        return "File sync not supported for Modal nodes (ephemeral)", False

    return "Unsupported node type", False


async def _handle_sync_down(paths: list, node_name: str, user_id: int = None, db=None, session=None, **kwargs):
    """Sync files from remote compute node to local workspace."""
    if not db:
        return "Database connection required", False

    from ..db import operations as ops
    node = await ops.get_compute_node_by_name(db, user_id, node_name)
    if not node:
        return f"Node '{node_name}' not found", False

    conv_uuid, local_ws, err = await _get_sync_context(user_id, db, session)
    if err:
        return err, False
    local_ws.mkdir(parents=True, exist_ok=True)

    if node.type == "local":
        return "Local sync: files are already in the same workspace", True

    elif node.type == "ssh":
        from ..sandbox.ssh import SSHSandbox
        ssh_sandbox = SSHSandbox()
        try:
            config = dict(node.config)
            config["conversation_uuid"] = conv_uuid
            await ssh_sandbox.create(config)

            transferred = 0
            for rel_path in paths:
                # Path traversal check
                local_path, path_err = _validate_sync_path(local_ws, rel_path)
                if path_err:
                    return path_err, False

                remote_path = f"{ssh_sandbox.workdir}/{rel_path}"

                # Check remote type
                result = await ssh_sandbox.execute(
                    f"test -d '{remote_path}' && echo dir || test -f '{remote_path}' && echo file || echo none",
                    timeout=5,
                )
                remote_type = result.output.strip()
                if remote_type == "none":
                    continue

                if remote_type == "file":
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    rp = remote_path  # bind for closure

                    def _do_get(rpath=rp):
                        buf = io.BytesIO()
                        ssh_sandbox._sftp.getfo(rpath, buf)
                        buf.seek(0)
                        return buf.read()

                    data = await asyncio.to_thread(_do_get)
                    local_path.write_bytes(data)
                    transferred += 1

                elif remote_type == "dir":
                    result = await ssh_sandbox.execute(f"find '{remote_path}' -type f", timeout=10)
                    remote_files = [ln.strip() for ln in result.output.strip().split("\n") if ln.strip()]
                    for rf in remote_files:
                        rel = rf.replace(remote_path + "/", "", 1)
                        dst = local_path / rel
                        # Path traversal check on each individual file
                        _, inner_err = _validate_sync_path(local_ws, str(Path(rel_path) / rel))
                        if inner_err:
                            continue
                        dst.parent.mkdir(parents=True, exist_ok=True)

                        # Bind rf in default arg to avoid closure-in-loop bug
                        def _do_get_file(rpath=rf):
                            buf = io.BytesIO()
                            ssh_sandbox._sftp.getfo(rpath, buf)
                            buf.seek(0)
                            return buf.read()

                        data = await asyncio.to_thread(_do_get_file)
                        dst.write_bytes(data)
                        transferred += 1

            return f"Synced {transferred} item(s) from {node.name}", True
        except Exception as e:
            return f"Sync failed: {str(e)}", False
        finally:
            await ssh_sandbox.destroy()

    elif node.type == "modal":
        return "File sync not supported for Modal nodes (ephemeral)", False

    return "Unsupported node type", False


def create_compute_tools() -> list[ToolSpec]:
    """Create agent tools for compute node management."""
    return [
        ToolSpec(
            name="compute_list",
            description="List all configured compute nodes with their capabilities and health status.",
            parameters={"type": "object", "properties": {}},
            handler=_handle_list,
        ),
        ToolSpec(
            name="compute_probe",
            description="Probe a compute node to discover its capabilities (CPU, GPU, RAM, installed packages).",
            parameters={
                "type": "object",
                "properties": {
                    "node_name": {
                        "type": "string",
                        "description": "Name of the compute node to probe",
                    },
                },
                "required": ["node_name"],
            },
            handler=_handle_probe,
        ),
        ToolSpec(
            name="compute_select",
            description="Switch the active compute node for this conversation. Use this before running tasks that need specific hardware.",
            parameters={
                "type": "object",
                "properties": {
                    "node_name": {
                        "type": "string",
                        "description": "Name of the compute node to activate",
                    },
                },
                "required": ["node_name"],
            },
            handler=_handle_select,
        ),
        ToolSpec(
            name="compute_plan",
            description="Recommend the best compute node for a given task based on requirements.",
            parameters={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "Description of the task (e.g., 'Train a ResNet-50 with mixed precision')",
                    },
                    "requirements": {
                        "type": "object",
                        "description": "Hardware requirements",
                        "properties": {
                            "gpu": {"type": "boolean", "description": "GPU required"},
                            "min_vram_gb": {"type": "number", "description": "Minimum GPU VRAM in GB"},
                            "min_ram_gb": {"type": "number", "description": "Minimum RAM in GB"},
                            "min_disk_gb": {"type": "number", "description": "Minimum free disk in GB"},
                        },
                    },
                },
                "required": ["task"],
            },
            handler=_handle_plan,
        ),
        ToolSpec(
            name="compute_sync_up",
            description="Sync files from local workspace to a remote compute node. Use before running code that needs data on the remote.",
            parameters={
                "type": "object",
                "properties": {
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Relative paths to sync (e.g., ['data/', 'code/train.py'])",
                    },
                    "node_name": {
                        "type": "string",
                        "description": "Name of the target compute node",
                    },
                },
                "required": ["paths", "node_name"],
            },
            handler=_handle_sync_up,
        ),
        ToolSpec(
            name="compute_sync_down",
            description="Sync files from a remote compute node to local workspace. Use after training to download models, logs, and results.",
            parameters={
                "type": "object",
                "properties": {
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Relative paths to sync (e.g., ['models/', 'outputs/'])",
                    },
                    "node_name": {
                        "type": "string",
                        "description": "Name of the source compute node",
                    },
                },
                "required": ["paths", "node_name"],
            },
            handler=_handle_sync_down,
        ),
    ]
