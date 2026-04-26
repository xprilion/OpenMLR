"""Local tools — bash (via Docker), read, write, edit.

bash commands run inside a Docker container for isolation.
read/write/edit operate on the host filesystem (for project files).
"""

import os
import asyncio
import logging
from pathlib import Path
from ..agent.types import ToolSpec

logger = logging.getLogger(__name__)

DOCKER_IMAGE = os.environ.get("OPEN_MLR_DOCKER_IMAGE", "python:3.12-slim")
CONTAINER_PREFIX = "openmlr-sandbox"

# Security: Disable direct host execution fallback (set to "true" to allow)
ALLOW_DIRECT_EXEC = os.environ.get("OPENMLR_ALLOW_DIRECT_EXEC", "false").lower() == "true"

# Security: Base directory for file operations (default: current working directory)
# Files outside this directory cannot be read/written/edited
WORKSPACE_ROOT = os.environ.get("OPENMLR_WORKSPACE_ROOT", "")


def _validate_path(path: Path) -> tuple[Path, str | None]:
    """Validate path is within allowed workspace. Returns (resolved_path, error_or_none)."""
    try:
        resolved = path.resolve()
        
        # If WORKSPACE_ROOT is set, enforce it
        if WORKSPACE_ROOT:
            workspace = Path(WORKSPACE_ROOT).resolve()
            try:
                resolved.relative_to(workspace)
            except ValueError:
                return resolved, f"Path {resolved} is outside workspace {workspace}"
        else:
            # Default: allow paths under current working directory
            cwd = Path.cwd().resolve()
            try:
                resolved.relative_to(cwd)
            except ValueError:
                # Also allow paths that are explicitly absolute and exist (for reading configs etc)
                # But block obvious dangerous paths
                dangerous_prefixes = ["/etc", "/root", "/var", "/usr", "/bin", "/sbin", "/boot", "/sys", "/proc"]
                for prefix in dangerous_prefixes:
                    if str(resolved).startswith(prefix):
                        return resolved, f"Access denied: {resolved} is in a protected system directory"
        
        return resolved, None
    except Exception as e:
        return path, f"Path validation error: {e}"


def create_local_tools() -> list[ToolSpec]:
    return [
        ToolSpec(
            name="bash",
            description=(
                "Execute a shell command inside a Docker container for safe isolation. "
                "The container has access to a /workspace volume mapped to the project directory. "
                "Use for running scripts, installing packages, training models, etc. "
                "If Docker is unavailable, falls back to direct execution with a warning."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds (default 120, max 3600)"},
                    "workdir": {"type": "string", "description": "Working directory inside container (default /workspace)"},
                },
                "required": ["command"],
            },
            handler=_handle_bash,
        ),
        ToolSpec(
            name="read",
            description="Read a file from the local filesystem with line numbers.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"},
                    "offset": {"type": "integer", "description": "Start line (1-indexed, default 1)"},
                    "limit": {"type": "integer", "description": "Max lines (default 2000)"},
                },
                "required": ["path"],
            },
            handler=_handle_read,
        ),
        ToolSpec(
            name="write",
            description="Write content to a file. Creates parent directories if needed.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to write"},
                    "content": {"type": "string", "description": "Content to write"},
                },
                "required": ["path", "content"],
            },
            handler=_handle_write,
        ),
        ToolSpec(
            name="edit",
            description="Edit a file by replacing a specific string with another.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to edit"},
                    "old_string": {"type": "string", "description": "Exact string to find"},
                    "new_string": {"type": "string", "description": "Replacement string"},
                    "replace_all": {"type": "boolean", "description": "Replace all occurrences (default false)"},
                },
                "required": ["path", "old_string", "new_string"],
            },
            handler=_handle_edit,
        ),
    ]


# ── Docker bash ──────────────────────────────────────────

async def _docker_available() -> bool:
    """Check if Docker is running."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "info",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=5)
        return proc.returncode == 0
    except Exception:
        return False


async def _handle_bash(command: str, timeout: int = 120, workdir: str = None, **kwargs) -> tuple[str, bool]:
    timeout = min(int(timeout), 3600)
    cwd = os.getcwd()

    if await _docker_available():
        return await _docker_exec(command, timeout, cwd, workdir)
    else:
        # Fallback to direct execution only if explicitly allowed
        if ALLOW_DIRECT_EXEC:
            logger.warning(f"Docker unavailable, falling back to direct host execution for: {command[:100]}")
            output, success = await _direct_exec(command, timeout, cwd)
            warning = "[WARNING: Docker not available — running directly on host]\n\n"
            return warning + output, success
        else:
            return (
                "Docker is not available and direct host execution is disabled for security.\n"
                "Please ensure Docker is running, or set OPENMLR_ALLOW_DIRECT_EXEC=true to enable fallback.",
                False
            )


async def _docker_exec(command: str, timeout: int, host_cwd: str, workdir: str = None) -> tuple[str, bool]:
    """Run command in a Docker container with workspace mount."""
    container_workdir = workdir or "/workspace"

    # Security: Use bridge network (default) instead of host network
    # This isolates container networking from the host
    docker_cmd = [
        "docker", "run", "--rm",
        "-v", f"{host_cwd}:/workspace",
        "-w", container_workdir,
        "--memory", "8g",
        "--pids-limit", "256",  # Prevent fork bombs
        "--read-only",  # Read-only root filesystem
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=1g",  # Writable /tmp
        "--security-opt", "no-new-privileges:true",
        DOCKER_IMAGE,
        "bash", "-c", command,
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *docker_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

        parts = []
        if stdout:
            parts.append(stdout.decode("utf-8", errors="replace"))
        if stderr:
            parts.append(f"STDERR:\n{stderr.decode('utf-8', errors='replace')}")
        output = "\n".join(parts) if parts else "(no output)"

        if len(output) > 50000:
            output = output[:50000] + "\n...[truncated]"

        success = proc.returncode == 0
        if not success:
            output = f"Exit code: {proc.returncode}\n{output}"
        return output, success

    except asyncio.TimeoutError:
        return f"Command timed out after {timeout}s", False
    except Exception as e:
        return f"Docker exec error: {str(e)}", False


async def _direct_exec(command: str, timeout: int, cwd: str) -> tuple[str, bool]:
    """Direct host execution (fallback)."""
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

        parts = []
        if stdout:
            parts.append(stdout.decode("utf-8", errors="replace"))
        if stderr:
            parts.append(f"STDERR:\n{stderr.decode('utf-8', errors='replace')}")
        output = "\n".join(parts) if parts else "(no output)"

        if len(output) > 50000:
            output = output[:50000] + "\n...[truncated]"

        success = proc.returncode == 0
        if not success:
            output = f"Exit code: {proc.returncode}\n{output}"
        return output, success
    except asyncio.TimeoutError:
        return f"Timed out after {timeout}s", False
    except Exception as e:
        return f"Error: {str(e)}", False


# ── File tools (host filesystem) ─────────────────────────

async def _handle_read(path: str, offset: int = 1, limit: int = 2000, **kwargs) -> tuple[str, bool]:
    try:
        target = Path(path).expanduser()
        if not target.is_absolute():
            target = Path.cwd() / target

        # Security: Validate path is within allowed workspace
        target, error = _validate_path(target)
        if error:
            return error, False

        if target.is_dir():
            entries = sorted(target.iterdir())
            return "\n".join(f"{e.name}{'/' if e.is_dir() else ''}" for e in entries) or "(empty directory)", True

        if not target.exists():
            return f"File not found: {target}", False

        with open(target, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()

        start = max(0, offset - 1)
        end = start + limit
        selected = all_lines[start:end]
        result = "\n".join(f"{i}: {line.rstrip()}" for i, line in enumerate(selected, start=start + 1))
        total = len(all_lines)
        if end < total:
            result += f"\n\n[Showing lines {start + 1}-{min(end, total)} of {total}]"
        return result, True
    except Exception as e:
        return f"Error reading: {str(e)}", False


async def _handle_write(path: str = "", content: str = "", **kwargs) -> tuple[str, bool]:
    # Handle models that abbreviate argument names (e.g., 'p' for 'path', 'c' for 'content')
    if not path:
        path = kwargs.get("p", kwargs.get("file", kwargs.get("filepath", "")))
    if not content:
        content = kwargs.get("c", kwargs.get("text", kwargs.get("data", "")))
    
    if not path:
        return "Error: 'path' argument is required.", False
    if not content:
        return "Error: 'content' argument is required.", False
    
    try:
        target = Path(path).expanduser()
        if not target.is_absolute():
            target = Path.cwd() / target
        
        # Security: Validate path is within allowed workspace
        target, error = _validate_path(target)
        if error:
            return error, False
        
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} chars to {target}", True
    except Exception as e:
        return f"Error writing: {str(e)}", False


async def _handle_edit(path: str, old_string: str, new_string: str, replace_all: bool = False, **kwargs) -> tuple[str, bool]:
    try:
        target = Path(path).expanduser()
        if not target.is_absolute():
            target = Path.cwd() / target
        
        # Security: Validate path is within allowed workspace
        target, error = _validate_path(target)
        if error:
            return error, False
        
        if not target.exists():
            return f"File not found: {target}", False

        content = target.read_text(encoding="utf-8")
        count = content.count(old_string)
        if count == 0:
            return "old_string not found in file.", False
        if count > 1 and not replace_all:
            return f"Found {count} matches. Use replace_all=true or provide more context.", False

        new_content = content.replace(old_string, new_string) if replace_all else content.replace(old_string, new_string, 1)
        target.write_text(new_content, encoding="utf-8")
        return f"Replaced {count if replace_all else 1} occurrence(s) in {target}", True
    except Exception as e:
        return f"Error editing: {str(e)}", False
