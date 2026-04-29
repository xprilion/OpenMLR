"""Terminal WebSocket endpoint — interactive PTY connected to compute resource.

Provides a real terminal experience via xterm.js on the frontend,
connected to the project workspace's compute environment.

Security:
- Minimal environment (no server secrets leaked)
- Workspace path validated against WORKSPACES_ROOT
- Shell spawned via subprocess (not os.fork) to avoid async corruption
- --norc --noprofile to prevent .bashrc injection
- Proper zombie process cleanup with SIGKILL escalation
"""

import asyncio
import fcntl
import json
import logging
import os
import pty
import signal
import struct
import subprocess
import termios
from pathlib import Path

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from ..auth.security import decode_access_token
from ..db import operations as ops
from ..db.engine import get_async_session
from ..db.models import User

router = APIRouter(tags=["terminal"])

log = logging.getLogger(__name__)

# Allowlisted environment variables for the PTY process.
# Server secrets (DATABASE_URL, API keys, JWT_SECRET_KEY, etc.) are NOT passed.
_SAFE_ENV_KEYS = {"LANG", "LC_ALL", "LC_CTYPE", "TZ"}


def _build_safe_env(workspace_path: str) -> dict[str, str]:
    """Build a minimal, safe environment for the PTY child process."""
    env = {
        "TERM": "xterm-256color",
        "HOME": workspace_path,
        "PWD": workspace_path,
        "PATH": "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        "SHELL": "/bin/bash",
        "USER": "openmlr",
    }
    # Copy only safe locale/timezone vars from parent
    for key in _SAFE_ENV_KEYS:
        val = os.environ.get(key)
        if val:
            env[key] = val
    return env


def _validate_workspace_path(workspace_path: str) -> bool:
    """Validate that a workspace path is within the expected root."""
    from .projects import WORKSPACES_ROOT

    try:
        resolved = Path(workspace_path).resolve()
        resolved.relative_to(WORKSPACES_ROOT.resolve())
        return True
    except (ValueError, RuntimeError):
        return False


async def _authenticate_ws(token: str | None) -> User | None:
    """Authenticate WebSocket connection via token query param."""
    if not token:
        return None

    payload = decode_access_token(token)
    if not payload:
        return None

    async with get_async_session() as db:
        from sqlalchemy import select

        result = await db.execute(
            select(User).where(
                User.id == int(payload["sub"]),
                User.is_active == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()


async def _cleanup_process(pid: int, master_fd: int) -> None:
    """Clean up PTY process with SIGKILL escalation to prevent zombies."""
    loop = asyncio.get_event_loop()

    # Close the master fd first
    try:
        await loop.run_in_executor(None, os.close, master_fd)
    except OSError:
        pass

    if pid <= 0:
        return

    # Send SIGTERM and wait with timeout
    try:
        await loop.run_in_executor(None, os.kill, pid, signal.SIGTERM)
    except ProcessLookupError:
        return

    # Poll up to 2 seconds for graceful exit
    for _ in range(20):
        try:
            result, _ = await loop.run_in_executor(None, os.waitpid, pid, os.WNOHANG)
            if result != 0:
                return  # Process exited
        except ChildProcessError:
            return  # Already reaped
        await asyncio.sleep(0.1)

    # Escalate to SIGKILL
    try:
        await loop.run_in_executor(None, os.kill, pid, signal.SIGKILL)
        await loop.run_in_executor(None, os.waitpid, pid, 0)  # Blocking wait after SIGKILL
    except (ProcessLookupError, ChildProcessError):
        pass


@router.websocket("/api/terminal/{project_uuid}")
@router.websocket("/api/terminal")
async def terminal_websocket(
    websocket: WebSocket,
    project_uuid: str | None = None,
    token: str = Query(default=None),
):
    """WebSocket endpoint for interactive terminal sessions.

    Spawns a PTY process in the project workspace directory.
    If no project_uuid is provided, uses the user's default project workspace.

    Messages from the client are written to the PTY stdin.
    Output from the PTY is sent back to the client.

    Special messages (JSON):
    - {"type": "resize", "cols": 80, "rows": 24} - resize the terminal
    - {"type": "input", "data": "..."} - send input to the PTY
    - Plain text messages are treated as input
    """
    # Authenticate
    user = await _authenticate_ws(token)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    # Look up the project to get the workspace path
    async with get_async_session() as db:
        if project_uuid:
            project = await ops.get_project_by_uuid(db, project_uuid, user.id)
        else:
            # Legacy fallback — terminal should always receive a project UUID
            # from the frontend. This path will be removed in a future version.
            from .projects import get_or_create_default_project

            project = await get_or_create_default_project(db, user.id)

        if not project or not project.workspace_path:
            await websocket.close(code=4004, reason="Project not found")
            return
        workspace_path = project.workspace_path

    # Validate workspace path is within allowed root
    if not _validate_workspace_path(workspace_path):
        log.warning(
            f"Terminal rejected: workspace path {workspace_path} "
            f"is outside allowed root (user={user.id})"
        )
        await websocket.close(code=4003, reason="Invalid workspace path")
        return

    # Verify workspace exists
    if not Path(workspace_path).exists():
        await websocket.close(code=4004, reason="Workspace not found")
        return

    await websocket.accept()

    # Spawn PTY using subprocess instead of os.fork() to avoid
    # corrupting the async event loop and leaking file descriptors.
    master_fd, slave_fd = pty.openpty()
    env = _build_safe_env(workspace_path)
    shell = "/bin/bash"

    try:
        loop = asyncio.get_event_loop()
        proc = await loop.run_in_executor(
            None,
            lambda: subprocess.Popen(
                [shell, "--norc", "--noprofile"],
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                cwd=workspace_path,
                env=env,
                start_new_session=True,
                close_fds=True,
            ),
        )
        pid = proc.pid
    except Exception as e:
        log.error(f"Failed to spawn terminal: {e}")
        os.close(master_fd)
        os.close(slave_fd)
        await websocket.close(code=4500, reason="Failed to spawn shell")
        return

    # Close slave fd in parent — only the child uses it
    os.close(slave_fd)

    # Keep master fd blocking — reads happen in a thread pool executor
    # so blocking is fine and avoids premature EAGAIN exits.

    def _blocking_read(fd: int) -> bytes:
        """Read from PTY fd. Blocks in the thread pool until data is available."""
        import select as _select

        while True:
            # Wait for data with a 0.5s timeout so the thread can be interrupted
            ready, _, _ = _select.select([fd], [], [], 0.5)
            if ready:
                return os.read(fd, 4096)
            # Check if the child process is still alive
            try:
                pid_result, _ = os.waitpid(proc.pid, os.WNOHANG)
                if pid_result != 0:
                    return b""  # Child exited
            except ChildProcessError:
                return b""

    async def read_pty():
        """Read from PTY and send to WebSocket."""
        loop = asyncio.get_event_loop()
        try:
            while True:
                try:
                    data = await loop.run_in_executor(None, lambda: _blocking_read(master_fd))
                    if not data:
                        break
                    await websocket.send_bytes(data)
                except OSError:
                    break
                except WebSocketDisconnect:
                    break
        except Exception as e:
            log.debug(f"PTY read ended: {e}")

    async def write_pty():
        """Read from WebSocket and write to PTY."""
        try:
            while True:
                msg = await websocket.receive()
                if msg.get("type") == "websocket.disconnect":
                    break

                if "text" in msg:
                    try:
                        data = json.loads(msg["text"])
                        if isinstance(data, dict):
                            if data.get("type") == "resize":
                                cols = min(int(data.get("cols", 80)), 500)
                                rows = min(int(data.get("rows", 24)), 200)
                                winsize = struct.pack("HHHH", rows, cols, 0, 0)
                                fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
                                continue
                            elif data.get("type") == "input":
                                input_data = data.get("data", "")
                                if isinstance(input_data, str):
                                    os.write(master_fd, input_data.encode()[:4096])
                                continue
                    except (json.JSONDecodeError, ValueError):
                        pass
                    # Plain text input — cap at 4KB per message
                    os.write(master_fd, msg["text"].encode()[:4096])

                elif "bytes" in msg:
                    os.write(master_fd, msg["bytes"][:4096])

        except WebSocketDisconnect:
            pass
        except Exception as e:
            log.debug(f"PTY write ended: {e}")

    # Run reader and writer concurrently
    try:
        reader_task = asyncio.create_task(read_pty())
        writer_task = asyncio.create_task(write_pty())
        done, pending = await asyncio.wait(
            [reader_task, writer_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
    finally:
        await _cleanup_process(pid, master_fd)
        try:
            await websocket.close()
        except Exception:
            pass
