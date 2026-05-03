"""Local tools — bash (via Docker), read, write, edit.

bash commands run inside a Docker container for isolation when running locally.
When running inside a container (Docker Compose), commands run directly since
the container itself provides isolation.

read/write/edit operate on the host filesystem (for project files).
"""

import asyncio
import logging
import os
import re
from contextvars import ContextVar
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

# Per-async-context project workspace override.  When a project is active its
# workspace path is injected here so that read/write/edit/bash tools
# automatically target the project directory (files then appear in the
# frontend FileTree).
_project_workspace_var: ContextVar[str | None] = ContextVar("project_workspace", default=None)


def set_project_workspace(path: str | None) -> None:
    """Set the active project workspace for the current async context."""
    _project_workspace_var.set(path)


def _get_effective_root() -> Path:
    """Return the effective workspace root for file operations.

    Priority: project workspace > WORKSPACE_ROOT env var > cwd.
    """
    project_ws = _project_workspace_var.get(None)
    if project_ws:
        return Path(project_ws).resolve()
    if WORKSPACE_ROOT:
        return Path(WORKSPACE_ROOT).resolve()
    return Path.cwd().resolve()


def _running_in_container() -> bool:
    """Detect if we're running inside a Docker container.

    This is useful for determining whether to use Docker-in-Docker or direct execution.
    When running in a container, the container already provides isolation.
    """
    # Check for common container indicators
    if os.path.exists("/.dockerenv"):
        return True

    # Check cgroup for docker/container runtime
    try:
        with open("/proc/1/cgroup") as f:
            content = f.read()
            if "docker" in content or "containerd" in content or "kubepods" in content:
                return True
    except (FileNotFoundError, PermissionError):
        pass

    # Check for container-related environment variables
    if os.environ.get("KUBERNETES_SERVICE_HOST"):
        return True

    return False


def _validate_path(path: Path) -> tuple[Path, str | None]:
    """Validate path is within allowed workspace. Returns (resolved_path, error_or_none)."""
    try:
        resolved = path.resolve()
        effective_root = _get_effective_root()

        try:
            resolved.relative_to(effective_root)
            return resolved, None
        except ValueError:
            pass

        # Also allow CWD even when project workspace is active (for read-only
        # access to project configuration files etc.)
        cwd = Path.cwd().resolve()
        try:
            resolved.relative_to(cwd)
            return resolved, None
        except ValueError:
            pass

        # Block obvious dangerous paths
        dangerous_prefixes = [
            "/etc",
            "/root",
            "/var",
            "/usr",
            "/bin",
            "/sbin",
            "/boot",
            "/sys",
            "/proc",
        ]
        for prefix in dangerous_prefixes:
            if str(resolved).startswith(prefix):
                return (
                    resolved,
                    f"Access denied: {resolved} is in a protected system directory",
                )

        # If none of the above matched, reject unless under effective root
        return resolved, f"Path {resolved} is outside workspace {effective_root}"
    except Exception as e:
        return path, f"Path validation error: {e}"


# ── Dangerous command detection ──────────────────────────

DANGEROUS_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Recursive deletes
    (
        re.compile(r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f|(-[a-zA-Z]*f[a-zA-Z]*r))\b"),
        "recursive force delete",
    ),
    (re.compile(r"\brm\s+-rf\s+/\s*$"), "delete root filesystem"),
    # Filesystem destruction
    (re.compile(r"\bmkfs\b"), "filesystem format"),
    (re.compile(r"\bdd\s+.*of=/dev/"), "raw disk write"),
    # SQL destructive operations
    (re.compile(r"\bDROP\s+(TABLE|DATABASE|SCHEMA)\b", re.IGNORECASE), "SQL drop"),
    (re.compile(r"\bDELETE\s+FROM\s+\w+\s*;", re.IGNORECASE), "SQL delete without WHERE"),
    (re.compile(r"\bTRUNCATE\s+TABLE\b", re.IGNORECASE), "SQL truncate"),
    # System config overwrites
    (re.compile(r">\s*/etc/"), "system config overwrite"),
    # Remote code execution
    (re.compile(r"curl\s+.*\|\s*(bash|sh|zsh)\b"), "remote code execution (curl pipe)"),
    (re.compile(r"wget\s+.*\|\s*(bash|sh|zsh)\b"), "remote code execution (wget pipe)"),
    # Service manipulation
    (re.compile(r"\bsystemctl\s+(stop|disable|mask)\b"), "service stop/disable"),
    # Process killing — only block mass-kill commands, not targeted kill -9
    # (researchers need kill -9 for hung training processes)
    (re.compile(r"\bkillall\b"), "kill all processes by name"),
    (re.compile(r"\bpkill\b"), "kill processes by pattern"),
    # Fork bombs
    (re.compile(r":\(\)\s*\{.*\}"), "fork bomb"),
    # GPU operations (ML-research-specific)
    (re.compile(r"\bnvidia-smi\s+(-r|--gpu-reset)\b"), "GPU reset"),
    # Dangerous git operations
    (re.compile(r"\bgit\s+push\s+.*--force\b"), "force push"),
    (re.compile(r"\bgit\s+reset\s+--hard\b"), "hard reset"),
    # Chmod dangerous
    (re.compile(r"\bchmod\s+(-R\s+)?777\b"), "world-writable permissions"),
]


def _detect_dangerous_command(command: str) -> str | None:
    """Check if a command matches dangerous patterns.

    Returns a description of the danger if matched, None if safe.
    """
    for pattern, description in DANGEROUS_PATTERNS:
        if pattern.search(command):
            return description
    return None


def create_local_tools() -> list[ToolSpec]:
    return [
        ToolSpec(
            name="bash",
            description=(
                "Execute a shell command in the project workspace.\n\n"
                "Commands run in Docker isolation with: 8GB memory limit, 256 process limit, "
                "read-only root filesystem (/tmp is writable), bridge network.\n\n"
                "Use for: running scripts, installing packages (pip/conda), training models, "
                "data processing, system commands.\n\n"
                "The working directory is the project workspace. Files created here appear "
                "in the Files tab.\n\n"
                "Common patterns:\n"
                "- Install deps: bash(command='pip install torch transformers')\n"
                "- Run script: bash(command='python train.py --epochs 10')\n"
                "- Check env: bash(command='python --version && pip list')"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute"},
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default 120, max 3600)",
                    },
                    "workdir": {
                        "type": "string",
                        "description": "Working directory inside container (default /workspace)",
                    },
                },
                "required": ["command"],
            },
            handler=_handle_bash,
        ),
        ToolSpec(
            name="read",
            description=(
                "Read a file from the project workspace with line numbers.\n\n"
                "Returns up to 2000 lines starting from the given offset. "
                "Use to inspect code, data files, logs, or configuration.\n"
                "Relative paths resolve from the project workspace root.\n\n"
                "For large files use offset/limit:\n"
                "- read(path='train.py', offset=100, limit=50) reads lines 100-149"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"},
                    "offset": {
                        "type": "integer",
                        "description": "Start line (1-indexed, default 1)",
                    },
                    "limit": {"type": "integer", "description": "Max lines (default 2000)"},
                },
                "required": ["path"],
            },
            handler=_handle_read,
        ),
        ToolSpec(
            name="write",
            description=(
                "Write content to a file in the project workspace. Creates parent "
                "directories automatically.\n\n"
                "Use for: source code, configuration files, scripts, data files.\n"
                "Do NOT use for academic papers — use the 'writing' tool instead.\n\n"
                "Relative paths resolve from the project workspace root. "
                "Written files appear in the Files tab immediately."
            ),
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
            description=(
                "Edit an existing file by replacing a specific string with another.\n\n"
                "Provide the exact string to find (old_string) and its replacement "
                "(new_string). Use replace_all=true to replace all occurrences.\n\n"
                "If old_string matches multiple times and replace_all is false, the "
                "edit fails — provide more surrounding context to make it unique."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to edit"},
                    "old_string": {"type": "string", "description": "Exact string to find"},
                    "new_string": {"type": "string", "description": "Replacement string"},
                    "replace_all": {
                        "type": "boolean",
                        "description": "Replace all occurrences (default false)",
                    },
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
            "docker",
            "info",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=5)
        return proc.returncode == 0
    except Exception:
        return False


async def _handle_bash(
    command: str, timeout: int = 120, workdir: str = None, **kwargs
) -> tuple[str, bool]:
    timeout = min(int(timeout), 3600)
    cwd = workdir or str(_get_effective_root())

    # Check for dangerous commands
    danger = _detect_dangerous_command(command)
    if danger:
        return (
            f"DANGEROUS COMMAND DETECTED: {danger}\n\n"
            f"Command: {command}\n\n"
            f"This command has been blocked for safety. If you need to run this command, "
            f"explain why it is necessary and the user can approve it through the approval flow."
        ), False

    # If we're already running inside a container, execute directly
    # The container itself provides isolation, so no need for Docker-in-Docker
    if _running_in_container():
        logger.debug(f"Running in container, executing directly: {command[:100]}")
        return await _direct_exec(command, timeout, cwd)

    # When running on host, try Docker for isolation
    if await _docker_available():
        return await _docker_exec(command, timeout, cwd, workdir)
    else:
        # Fallback to direct execution only if explicitly allowed
        if ALLOW_DIRECT_EXEC:
            logger.warning(
                f"Docker unavailable, falling back to direct host execution for: {command[:100]}"
            )
            output, success = await _direct_exec(command, timeout, cwd)
            warning = "[WARNING: Docker not available — running directly on host]\n\n"
            return warning + output, success
        else:
            return (
                "Docker is not available and direct host execution is disabled for security.\n"
                "Please ensure Docker is running, or set OPENMLR_ALLOW_DIRECT_EXEC=true to enable fallback.",
                False,
            )


async def _docker_exec(
    command: str, timeout: int, host_cwd: str, workdir: str = None
) -> tuple[str, bool]:
    """Run command in a Docker container with workspace mount."""
    container_workdir = workdir or "/workspace"

    # Security: Use bridge network (default) instead of host network
    # This isolates container networking from the host
    docker_cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{host_cwd}:/workspace",
        "-w",
        container_workdir,
        "--memory",
        "8g",
        "--pids-limit",
        "256",  # Prevent fork bombs
        "--read-only",  # Read-only root filesystem
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=1g",  # Writable /tmp
        "--security-opt",
        "no-new-privileges:true",
        DOCKER_IMAGE,
        "bash",
        "-c",
        command,
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

    except TimeoutError:
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
    except TimeoutError:
        return f"Timed out after {timeout}s", False
    except Exception as e:
        return f"Error: {str(e)}", False


# ── File tools (host filesystem) ─────────────────────────


def _read_file_lines(path: Path) -> list[str]:
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.readlines()


async def _handle_read(path: str, offset: int = 1, limit: int = 2000, **kwargs) -> tuple[str, bool]:
    try:
        target = Path(path).expanduser()
        if not target.is_absolute():
            target = _get_effective_root() / target

        # Security: Validate path is within allowed workspace
        target, error = _validate_path(target)
        if error:
            return error, False

        if target.is_dir():
            entries = sorted(target.iterdir())
            return "\n".join(
                f"{e.name}{'/' if e.is_dir() else ''}" for e in entries
            ) or "(empty directory)", True

        if not target.exists():
            return f"File not found: {target}", False

        loop = asyncio.get_event_loop()
        all_lines = await loop.run_in_executor(None, _read_file_lines, target)

        start = max(0, offset - 1)
        end = start + limit
        selected = all_lines[start:end]
        result = "\n".join(
            f"{i}: {line.rstrip()}" for i, line in enumerate(selected, start=start + 1)
        )
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
            target = _get_effective_root() / target

        # Security: Validate path is within allowed workspace
        target, error = _validate_path(target)
        if error:
            return error, False

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} chars to {target}", True
    except Exception as e:
        return f"Error writing: {str(e)}", False


async def _handle_edit(
    path: str, old_string: str, new_string: str, replace_all: bool = False, **kwargs
) -> tuple[str, bool]:
    try:
        target = Path(path).expanduser()
        if not target.is_absolute():
            target = _get_effective_root() / target

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

        new_content = (
            content.replace(old_string, new_string)
            if replace_all
            else content.replace(old_string, new_string, 1)
        )
        target.write_text(new_content, encoding="utf-8")
        return f"Replaced {count if replace_all else 1} occurrence(s) in {target}", True
    except Exception as e:
        return f"Error editing: {str(e)}", False
