"""Local sandbox — direct filesystem and shell execution."""

import asyncio
import os
import time
from pathlib import Path

from ..compute.probe import probe_sandbox
from .interface import ExecutionResult, SandboxInterface


class LocalSandbox(SandboxInterface):
    """Execute commands directly on the local machine."""

    def __init__(self, workdir: str = None, workspace_manager=None):
        self._workspace_manager = workspace_manager
        self._conversation_uuid = None
        self._project_workspace = None  # project workspace path (takes priority)
        self.workdir = workdir or os.getcwd()

    async def create(self, config: dict) -> "LocalSandbox":
        self.workdir = config.get("workdir", os.getcwd())
        self._conversation_uuid = config.get("conversation_uuid")
        self._project_workspace = config.get("project_workspace_path")

        # Priority: project workspace > conversation workspace > default workdir
        if self._project_workspace:
            # Validate the project workspace path is within the allowed root
            ws_path = Path(self._project_workspace).resolve()
            from ..compute.workspace import WORKSPACES_ROOT

            try:
                ws_path.relative_to(WORKSPACES_ROOT.resolve())
            except ValueError:
                raise ValueError("Project workspace path is outside allowed root")
            ws_path.mkdir(parents=True, exist_ok=True)
            self.workdir = str(ws_path)
        elif self._workspace_manager and self._conversation_uuid:
            ws_path = self._workspace_manager.create_workspace(self._conversation_uuid)
            self.workdir = str(ws_path)
        elif self._workspace_manager:
            ws_path = self._workspace_manager.create_workspace("default")
            self.workdir = str(ws_path)

        return self

    async def execute(self, command: str, timeout: int = 120) -> ExecutionResult:
        return await self.execute_stream(command, timeout)

    async def execute_stream(
        self, command: str, timeout: int = 120, on_chunk=None
    ) -> ExecutionResult:
        """Execute a command with optional streaming output."""
        start = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.workdir,
            )

            output_parts = []

            async def _read_stream(stream, is_stderr):
                """Read a stream and emit chunks."""
                while True:
                    try:
                        line = await asyncio.wait_for(stream.readline(), timeout=0.5)
                        if not line:
                            break
                        text = line.decode("utf-8", errors="replace")
                        if on_chunk:
                            on_chunk(text, is_stderr)
                        output_parts.append(text)
                    except TimeoutError:
                        # Check if process is done
                        if proc.returncode is not None:
                            break
                        continue

            # Read stdout and stderr concurrently
            await asyncio.gather(
                _read_stream(proc.stdout, False),
                _read_stream(proc.stderr, True),
            )

            # Wait for process to complete
            try:
                returncode = await asyncio.wait_for(proc.wait(), timeout=1.0)
            except TimeoutError:
                returncode = proc.returncode if proc.returncode is not None else -1

            output = "".join(output_parts) if output_parts else "(no output)"
            if len(output) > 50000:
                output = output[:50000] + "\n...[truncated]"

            duration = time.monotonic() - start
            return ExecutionResult(
                output=output,
                success=returncode == 0,
                exit_code=returncode,
                duration_seconds=duration,
            )
        except TimeoutError:
            return ExecutionResult(
                output=f"Command timed out after {timeout}s",
                success=False,
                exit_code=-1,
                duration_seconds=timeout,
            )
        except Exception as e:
            return ExecutionResult(output=f"Error: {str(e)}", success=False, exit_code=-1)

    def _resolve_path(self, path: str) -> Path:
        """Resolve a path relative to workdir, preventing traversal outside it."""
        target = Path(path).expanduser()
        if not target.is_absolute():
            target = Path(self.workdir) / target
        resolved = target.resolve()
        workdir_resolved = Path(self.workdir).resolve()
        # Allow paths within workdir, or absolute paths if no project workspace
        if self._project_workspace:
            try:
                resolved.relative_to(workdir_resolved)
            except ValueError:
                raise PermissionError("Access denied: path outside workspace")
        return resolved

    async def read_file(self, path: str) -> str:
        target = self._resolve_path(path)
        return target.read_text(encoding="utf-8", errors="replace")

    async def write_file(self, path: str, content: str) -> bool:
        target = self._resolve_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return True

    async def edit_file(self, path: str, old: str, new: str) -> bool:
        content = await self.read_file(path)
        if old not in content:
            return False
        content = content.replace(old, new, 1)
        await self.write_file(path, content)
        return True

    async def file_exists(self, path: str) -> bool:
        target = self._resolve_path(path)
        return target.exists()

    async def list_files(self, path: str = ".") -> list[str]:
        target = self._resolve_path(path)
        return sorted([f"{e.name}{'/' if e.is_dir() else ''}" for e in target.iterdir()])

    async def probe_environment(self):
        return await probe_sandbox(self)

    async def destroy(self) -> None:
        pass  # Local sandbox has nothing to clean up
