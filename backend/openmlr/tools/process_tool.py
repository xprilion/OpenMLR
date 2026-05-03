"""Background process management tool — start, poll, log, wait, kill long-running tasks."""

import asyncio
import logging
import os
import signal
from datetime import UTC, datetime
from pathlib import Path

from ..agent.types import ToolSpec

logger = logging.getLogger(__name__)

# In-memory tracking of active subprocess handles (for the current worker)
_active_processes: dict[str, asyncio.subprocess.Process] = {}


async def _start_background(
    command: str, cwd: str, output_path: str
) -> tuple[asyncio.subprocess.Process, int]:
    """Start a subprocess with output redirected to a log file."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(output_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=fd,
            stderr=asyncio.subprocess.STDOUT,
            cwd=cwd,
        )
    finally:
        os.close(fd)

    return proc, proc.pid


def _read_log_file(output_path: str, tail: int | None = None) -> str:
    """Synchronous helper to read a log file (called via asyncio.to_thread)."""
    with open(output_path) as f:
        if tail is not None:
            lines = f.readlines()
            content = "".join(lines[-tail:])
            if len(content) > 5000:
                content = content[-5000:]
            return content
        content = f.read()
        if len(content) > 50000:
            content = "[...truncated...]\n" + content[-50000:]
        return content


async def _action_start(command, session, user_id, db, ops, **kwargs) -> tuple[str, bool]:
    """Handle 'start' action: launch a background process."""
    if not command:
        return "Error: 'command' is required for start action.", False

    conv_id = getattr(session, "conversation_id", None)
    if not conv_id:
        return "No active conversation for background process.", False

    from .local import _get_effective_root

    cwd = str(_get_effective_root())

    project_id = None
    try:
        conv = await ops.get_conversation_by_id(db, conv_id)
        if conv:
            project_id = conv.project_id
    except Exception:
        pass

    proc_record = await ops.create_background_process(
        db,
        conversation_id=conv_id,
        user_id=user_id,
        command=command,
        host="local",
        project_id=project_id,
    )
    proc_uuid = proc_record.uuid

    output_path = os.path.join(cwd, "logs", "processes", f"{proc_uuid}.log")
    await ops.update_background_process(db, proc_uuid, output_path=output_path)

    try:
        proc, pid = await _start_background(command, cwd, output_path)
        _active_processes[proc_uuid] = proc
        await ops.update_background_process(db, proc_uuid, pid=pid)

        return (
            f"Background process started:\n"
            f"  session_id: {proc_uuid}\n"
            f"  pid: {pid}\n"
            f"  command: {command}\n"
            f"  log: {output_path}\n\n"
            f"Use process(action='poll', session_id='{proc_uuid}') to check status."
        ), True
    except Exception as e:
        await ops.update_background_process(
            db, proc_uuid, status="failed", completed_at=datetime.now(UTC)
        )
        return f"Failed to start process: {e}", False


def _format_duration(started_at, completed_at) -> str:
    """Format a human-readable duration string."""
    if not started_at:
        return ""
    end = completed_at or datetime.now(UTC)
    secs = (end - started_at).total_seconds()
    if secs > 3600:
        return f" ({secs / 3600:.1f}h)"
    if secs > 60:
        return f" ({secs / 60:.0f}m)"
    return f" ({secs:.0f}s)"


async def _action_list(session, user_id, db, ops, **kwargs) -> tuple[str, bool]:
    """Handle 'list' action: show all background processes."""
    conv_id = getattr(session, "conversation_id", None)
    processes = await ops.get_background_processes(db, user_id, conversation_id=conv_id)
    if not processes:
        return "No background processes found.", True

    lines = [f"Background processes ({len(processes)}):\n"]
    for p in processes:
        duration = _format_duration(p.started_at, p.completed_at)
        lines.append(
            f"  [{p.status.upper()}] {p.uuid[:8]}  pid={p.pid}  "
            f"{p.command[:60]}{'...' if len(p.command) > 60 else ''}{duration}"
        )
    return "\n".join(lines), True


async def _action_poll(session_id, tail, user_id, db, ops, **kwargs) -> tuple[str, bool]:
    """Handle 'poll' action: check status and recent output."""
    if not session_id:
        return "Error: 'session_id' is required for poll action.", False

    proc_record = await ops.get_background_process_by_uuid(db, session_id)
    if not proc_record:
        return f"Process '{session_id}' not found.", False

    if proc_record.status == "running" and proc_record.pid:
        if not _is_pid_alive(proc_record.pid):
            exit_code = _get_exit_code(session_id)
            new_status = "completed" if exit_code == 0 else "failed"
            await ops.update_background_process(
                db,
                session_id,
                status=new_status,
                exit_code=exit_code,
                completed_at=datetime.now(UTC),
            )
            proc_record = await ops.get_background_process_by_uuid(db, session_id)

    recent = ""
    if proc_record.output_path and os.path.exists(proc_record.output_path):
        try:
            recent = await asyncio.to_thread(_read_log_file, proc_record.output_path, tail)
        except Exception:
            pass

    return (
        f"Process {session_id[:8]}:\n"
        f"  Status: {proc_record.status}\n"
        f"  PID: {proc_record.pid}\n"
        f"  Exit code: {proc_record.exit_code}\n"
        f"  Command: {proc_record.command}\n\n"
        f"Recent output:\n{recent or '(no output yet)'}"
    ), True


async def _action_log(session_id, user_id, db, ops, **kwargs) -> tuple[str, bool]:
    """Handle 'log' action: read full log output."""
    if not session_id:
        return "Error: 'session_id' is required for log action.", False

    proc_record = await ops.get_background_process_by_uuid(db, session_id)
    if not proc_record:
        return f"Process '{session_id}' not found.", False

    if not proc_record.output_path or not os.path.exists(proc_record.output_path):
        return "No log file available.", True

    try:
        content = await asyncio.to_thread(_read_log_file, proc_record.output_path)
        return content or "(empty log)", True
    except Exception as e:
        return f"Error reading log: {e}", False


async def _action_kill(session_id, user_id, db, ops, **kwargs) -> tuple[str, bool]:
    """Handle 'kill' action: terminate a running process."""
    if not session_id:
        return "Error: 'session_id' is required for kill action.", False

    proc_record = await ops.get_background_process_by_uuid(db, session_id)
    if not proc_record:
        return f"Process '{session_id}' not found.", False

    if proc_record.status != "running":
        return f"Process is not running (status: {proc_record.status}).", False

    killed = False
    if session_id in _active_processes:
        try:
            _active_processes[session_id].terminate()
            await asyncio.sleep(2)
            if _active_processes[session_id].returncode is None:
                _active_processes[session_id].kill()
            killed = True
        except Exception:
            pass

    if not killed and proc_record.pid:
        try:
            os.kill(proc_record.pid, signal.SIGTERM)
            await asyncio.sleep(2)
            if _is_pid_alive(proc_record.pid):
                os.kill(proc_record.pid, signal.SIGKILL)
            killed = True
        except ProcessLookupError:
            killed = True
        except Exception as e:
            return f"Failed to kill process: {e}", False

    await ops.update_background_process(
        db,
        session_id,
        status="killed",
        completed_at=datetime.now(UTC),
    )
    _active_processes.pop(session_id, None)

    return f"Process {session_id[:8]} killed.", True


async def _action_wait(session_id, timeout, user_id, db, ops, **kwargs) -> tuple[str, bool]:
    """Handle 'wait' action: block until process completes.

    The timeout parameter is used with asyncio.sleep polling, capped at 300s.
    """
    if not session_id:
        return "Error: 'session_id' is required for wait action.", False

    proc_record = await ops.get_background_process_by_uuid(db, session_id)
    if not proc_record:
        return f"Process '{session_id}' not found.", False

    if proc_record.status != "running":
        return (
            f"Process already {proc_record.status} (exit code: {proc_record.exit_code}).",
            True,
        )

    timeout = min(timeout, 300)
    elapsed = 0
    while elapsed < timeout:
        await asyncio.sleep(5)
        elapsed += 5
        if proc_record.pid and not _is_pid_alive(proc_record.pid):
            exit_code = _get_exit_code(session_id)
            new_status = "completed" if exit_code == 0 else "failed"
            await ops.update_background_process(
                db,
                session_id,
                status=new_status,
                exit_code=exit_code,
                completed_at=datetime.now(UTC),
            )
            return f"Process finished ({new_status}, exit code: {exit_code}).", True

    return f"Timed out after {timeout}s — process still running.", True


# Action dispatch table
_ACTION_DISPATCH = {
    "start": _action_start,
    "list": _action_list,
    "poll": _action_poll,
    "log": _action_log,
    "kill": _action_kill,
    "wait": _action_wait,
}


async def _handle_process(
    action: str,
    session_id: str = "",
    command: str = "",
    timeout: int = 120,
    tail: int = 50,
    session=None,
    user_id: int | None = None,
    db=None,
    **kwargs,
) -> tuple[str, bool]:
    """Handle process management actions by dispatching to action-specific functions."""
    if not user_id or not db:
        return "Process tool requires authentication context.", False

    from ..db import operations as ops

    handler = _ACTION_DISPATCH.get(action)
    if not handler:
        return f"Unknown action '{action}'. Use: start, list, poll, log, kill, wait.", False

    return await handler(
        session_id=session_id,
        command=command,
        timeout=timeout,
        tail=tail,
        session=session,
        user_id=user_id,
        db=db,
        ops=ops,
        **kwargs,
    )


def _is_pid_alive(pid: int) -> bool:
    """Check if a PID is still running."""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # Process exists but owned by different user


def _get_exit_code(session_id: str) -> int | None:
    """Get exit code from in-memory process handle if available."""
    proc = _active_processes.get(session_id)
    if proc and proc.returncode is not None:
        return proc.returncode
    return None


def create_process_tool() -> ToolSpec:
    return ToolSpec(
        name="process",
        description=(
            "Manage background processes (e.g., ML training runs).\n\n"
            "Background processes persist across sessions — they keep running even "
            "if you close the browser tab.\n\n"
            "Actions:\n"
            "- start: Start a command in the background. Returns a session_id.\n"
            "- list: Show all background processes for this conversation.\n"
            "- poll: Check status and recent output of a process.\n"
            "- log: Read the full log output of a process.\n"
            "- wait: Block until a process completes (with timeout).\n"
            "- kill: Terminate a running process.\n\n"
            "Example workflow:\n"
            "1. process(action='start', command='python train.py --epochs 100')\n"
            "2. ... do other work ...\n"
            "3. process(action='poll', session_id='abc123')\n"
            "4. process(action='log', session_id='abc123')"
        ),
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["start", "list", "poll", "log", "kill", "wait"],
                    "description": "Action to perform",
                },
                "session_id": {
                    "type": "string",
                    "description": "Process session ID (from start action)",
                },
                "command": {
                    "type": "string",
                    "description": "Shell command to run (for start action)",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Wait timeout in seconds (for wait action, max 300)",
                },
                "tail": {
                    "type": "integer",
                    "description": "Number of recent log lines (for poll action, default 50)",
                },
            },
            "required": ["action"],
        },
        handler=_handle_process,
    )
