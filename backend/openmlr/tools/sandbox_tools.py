"""Sandbox tools — expose execution environments to the agent."""

import asyncio

from ..agent.types import AgentEvent, ToolSpec


def create_sandbox_tools(sandbox_manager) -> list[ToolSpec]:
    """Create tools that operate on sandbox execution environments."""
    return [
        ToolSpec(
            name="sandbox_probe",
            description=(
                "Probe the current sandbox environment. Returns OS, Python version, "
                "GPU availability, installed packages, disk/RAM info. "
                "Always run this before executing code in a sandbox."
            ),
            parameters={
                "type": "object",
                "properties": {},
            },
            handler=lambda **kwargs: _handle_probe(sandbox_manager, **kwargs),
        ),
        ToolSpec(
            name="sandbox_create",
            description=(
                "Create a new sandbox execution environment. Choose a provider "
                "(local, ssh, modal) and configure it. Requires approval."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "provider": {
                        "type": "string",
                        "enum": ["local", "ssh", "modal"],
                        "description": "Sandbox provider type",
                    },
                    "config": {
                        "type": "object",
                        "description": "Provider-specific configuration",
                        "properties": {
                            "host": {"type": "string", "description": "SSH hostname"},
                            "port": {"type": "integer", "description": "SSH port (default 22)"},
                            "username": {"type": "string", "description": "SSH username"},
                            "key_path": {"type": "string", "description": "Path to SSH private key"},
                            "gpu": {"type": "string", "description": "Modal GPU type (e.g. T4, A100)"},
                            "image": {"type": "string", "description": "Modal container image"},
                            "workdir": {"type": "string", "description": "Working directory"},
                        },
                    },
                },
                "required": ["provider"],
            },
            handler=lambda **kwargs: _handle_create(sandbox_manager, **kwargs),
            needs_approval=lambda args: True,  # Always require approval
        ),
        ToolSpec(
            name="sandbox_exec",
            description=(
                "Execute a command in the active sandbox. If no sandbox is active, "
                "falls back to local execution. Use stream=true for long-running commands."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds (default 120, max 3600)"},
                    "stream": {"type": "boolean", "description": "Stream output in real-time for long-running commands (default false)"},
                },
                "required": ["command"],
            },
            handler=lambda **kwargs: _handle_exec(sandbox_manager, **kwargs),
        ),
        ToolSpec(
            name="sandbox_read",
            description="Read a file from the active sandbox.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"},
                },
                "required": ["path"],
            },
            handler=lambda **kwargs: _handle_read(sandbox_manager, **kwargs),
        ),
        ToolSpec(
            name="sandbox_write",
            description="Write a file to the active sandbox.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to write"},
                    "content": {"type": "string", "description": "File content"},
                },
                "required": ["path", "content"],
            },
            handler=lambda **kwargs: _handle_write(sandbox_manager, **kwargs),
        ),
    ]


async def _handle_probe(sandbox_manager, session=None, **kwargs) -> tuple[str, bool]:
    sandbox = sandbox_manager.get_active()
    if not sandbox:
        return "No active sandbox. Using local environment.\n" + await _local_probe(), True

    try:
        caps = await sandbox.probe_environment()
        lines = [
            f"## Sandbox Environment ({sandbox_manager.active_type})\n",
            f"Platform: {caps.platform}",
            f"CPU: {caps.cpu_cores} cores ({caps.cpu_arch})",
            f"Python: {', '.join(caps.python_versions) if caps.python_versions else 'unknown'}",
        ]
        if caps.gpu_available and caps.gpu_info:
            for gpu in caps.gpu_info:
                lines.append(f"GPU: {gpu.model} ({gpu.vram_gb:.0f} GB VRAM)")
        elif caps.gpu_available:
            lines.append("GPU: available")
        else:
            lines.append("GPU: not available")
        lines.append(f"Disk: {caps.available_disk_gb:.1f} GB free")
        lines.append(f"RAM: {caps.available_ram_gb:.1f} GB free")
        if caps.installed_packages:
            lines.append(f"\nKey packages: {', '.join(caps.installed_packages[:20])}")
        return "\n".join(lines), True
    except Exception as e:
        return f"Probe failed: {str(e)}", False


async def _local_probe() -> str:
    """Quick local environment probe."""
    import platform
    import shutil
    import subprocess

    lines = [f"OS: {platform.system()} {platform.release()}"]

    try:
        py = subprocess.run(["python3", "--version"], capture_output=True, text=True, timeout=5)
        lines.append(f"Python: {py.stdout.strip()}")
    except Exception:
        lines.append("Python: unknown")

    try:
        gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                           capture_output=True, text=True, timeout=5)
        if gpu.returncode == 0:
            lines.append(f"GPU: {gpu.stdout.strip()}")
        else:
            lines.append("GPU: not available")
    except Exception:
        lines.append("GPU: not available (nvidia-smi not found)")

    total, used, free = shutil.disk_usage("/")
    lines.append(f"Disk: {free // (1024**3)} GB free")

    return "\n".join(lines)


async def _handle_create(sandbox_manager, provider: str, config: dict = None, session=None, **kwargs) -> tuple[str, bool]:
    try:
        await sandbox_manager.create(provider, config or {})
        return f"Sandbox created: {provider} ({sandbox_manager.active_type})", True
    except Exception as e:
        return f"Failed to create sandbox: {str(e)}", False


async def _handle_exec(sandbox_manager, command: str, timeout: int = 120, stream: bool = False, session=None, **kwargs) -> tuple[str, bool]:
    sandbox = sandbox_manager.get_active()
    if not sandbox:
        # Fall back to local execution
        from .local import _handle_bash
        return await _handle_bash(command=command, timeout=timeout)

    try:
        if stream and session:
            # Stream output via tool_log events
            # on_chunk may be called from a worker thread (SSH), so use
            # call_soon_threadsafe to schedule the coroutine on the event loop.
            loop = asyncio.get_running_loop()

            def on_chunk(text: str, is_stderr: bool):
                prefix = "STDERR: " if is_stderr else ""
                event = AgentEvent(
                    event_type="tool_log",
                    data={"message": f"{prefix}{text.rstrip()}"},
                )
                loop.call_soon_threadsafe(asyncio.ensure_future, session.emit(event))

            result = await sandbox.execute_stream(command, timeout=timeout, on_chunk=on_chunk)
            return result.output, result.success
        else:
            result = await sandbox.execute(command, timeout=timeout)
            return result.output, result.success
    except Exception as e:
        return f"Execution error: {str(e)}", False


async def _handle_read(sandbox_manager, path: str, session=None, **kwargs) -> tuple[str, bool]:
    sandbox = sandbox_manager.get_active()
    if not sandbox:
        from .local import _handle_read as local_read
        return await local_read(path=path)

    try:
        content = await sandbox.read_file(path)
        return content, True
    except Exception as e:
        return f"Read error: {str(e)}", False


async def _handle_write(sandbox_manager, path: str, content: str, session=None, **kwargs) -> tuple[str, bool]:
    sandbox = sandbox_manager.get_active()
    if not sandbox:
        from .local import _handle_write as local_write
        return await local_write(path=path, content=content)

    try:
        success = await sandbox.write_file(path, content)
        return f"Wrote {len(content)} chars to {path}", success
    except Exception as e:
        return f"Write error: {str(e)}", False
