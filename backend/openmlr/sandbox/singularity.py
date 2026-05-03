"""Singularity/Apptainer sandbox — HPC-friendly container execution.

Apptainer (formerly Singularity) is the standard container runtime on
institutional HPC clusters where Docker is not available. It runs as a
non-root user and provides reproducible environments without requiring
daemon privileges.

Usage:
  - Pre-build SIF: apptainer build image.sif docker://python:3.12-slim
  - Or pull directly: apptainer pull docker://python:3.12-slim
"""

import asyncio
import logging
import shutil
import time
from pathlib import Path

from ..compute.capabilities import ComputeCapabilities, GPUInfo
from .interface import ExecutionResult, SandboxInterface

logger = logging.getLogger(__name__)


class SingularitySandbox(SandboxInterface):
    """Sandbox implementation using Apptainer/Singularity containers."""

    def __init__(self):
        self._image: str = ""
        self._bind_paths: list[str] = []
        self._gpu: bool = False
        self._workdir: str = "/workspace"
        self._host_workdir: str = ""

    async def create(self, config: dict) -> "SingularitySandbox":
        """Initialize sandbox from configuration.

        Config keys:
          - image: Path to .sif file or docker:// URI
          - bind_paths: Additional bind mounts (list of "host:container" strings)
          - gpu: Whether to enable GPU passthrough (--nv flag)
          - workdir: Host working directory to bind as /workspace
          - project_workspace_path: Alternative key for host working directory
        """
        self._image = config.get("image", "docker://python:3.12-slim")
        self._bind_paths = config.get("bind_paths", [])
        self._gpu = config.get("gpu", False)
        self._host_workdir = config.get("workdir", config.get("project_workspace_path", ""))

        # Verify apptainer/singularity is available
        binary = self._find_binary()
        if not binary:
            raise RuntimeError(
                "Neither 'apptainer' nor 'singularity' found in PATH. "
                "Install Apptainer: https://apptainer.org/docs/admin/main/installation.html"
            )
        logger.info(
            f"Singularity sandbox initialized: image={self._image}, "
            f"gpu={self._gpu}, binary={binary}"
        )
        return self

    def _find_binary(self) -> str | None:
        """Find apptainer or singularity binary."""
        for name in ("apptainer", "singularity"):
            if shutil.which(name):
                return name
        return None

    def _build_exec_cmd(self, command: str) -> list[str]:
        """Build the apptainer exec command with all flags."""
        binary = self._find_binary()
        if not binary:
            raise RuntimeError("Apptainer/Singularity not found")

        cmd = [binary, "exec"]

        # GPU passthrough
        if self._gpu:
            cmd.append("--nv")

        # Bind workspace
        if self._host_workdir:
            cmd.extend(["--bind", f"{self._host_workdir}:{self._workdir}"])

        # Additional bind paths
        for bind in self._bind_paths:
            cmd.extend(["--bind", bind])

        # Working directory
        cmd.extend(["--pwd", self._workdir])

        # Writable tmpfs for /tmp
        cmd.append("--writable-tmpfs")

        # Container image
        cmd.append(self._image)

        # Command
        cmd.extend(["bash", "-c", command])

        return cmd

    async def execute(self, command: str, timeout: int = 120) -> ExecutionResult:
        """Execute a command inside the Singularity container."""
        start = time.monotonic()

        try:
            cmd = self._build_exec_cmd(command)
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

            output_parts = []
            if stdout:
                output_parts.append(stdout.decode("utf-8", errors="replace"))
            if stderr:
                output_parts.append(f"STDERR:\n{stderr.decode('utf-8', errors='replace')}")
            output = "\n".join(output_parts) if output_parts else "(no output)"

            if len(output) > 50000:
                output = output[:50000] + "\n...[truncated]"

            duration = time.monotonic() - start
            return ExecutionResult(
                output=output,
                success=proc.returncode == 0,
                exit_code=proc.returncode or 0,
                duration_seconds=duration,
            )
        except TimeoutError:
            duration = time.monotonic() - start
            return ExecutionResult(
                output=f"Command timed out after {timeout}s",
                success=False,
                exit_code=-1,
                duration_seconds=duration,
            )
        except Exception as e:
            duration = time.monotonic() - start
            return ExecutionResult(
                output=f"Singularity exec error: {str(e)}",
                success=False,
                exit_code=-1,
                duration_seconds=duration,
            )

    async def execute_stream(
        self, command: str, timeout: int = 120, on_chunk=None
    ) -> ExecutionResult:
        """Execute with streaming output via callback."""
        start = time.monotonic()
        output_buffer: list[str] = []

        try:
            cmd = self._build_exec_cmd(command)
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            async def read_stream():
                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        break
                    text = line.decode("utf-8", errors="replace")
                    output_buffer.append(text)
                    if on_chunk:
                        on_chunk(text, False)

            await asyncio.wait_for(read_stream(), timeout=timeout)
            await proc.wait()

            output = "".join(output_buffer)
            if len(output) > 50000:
                output = output[:50000] + "\n...[truncated]"

            duration = time.monotonic() - start
            return ExecutionResult(
                output=output or "(no output)",
                success=proc.returncode == 0,
                exit_code=proc.returncode or 0,
                duration_seconds=duration,
            )
        except TimeoutError:
            duration = time.monotonic() - start
            return ExecutionResult(
                output=f"Command timed out after {timeout}s",
                success=False,
                exit_code=-1,
                duration_seconds=duration,
            )
        except Exception as e:
            duration = time.monotonic() - start
            return ExecutionResult(
                output=f"Singularity stream error: {str(e)}",
                success=False,
                exit_code=-1,
                duration_seconds=duration,
            )

    def _resolve_path(self, path: str) -> Path:
        """Resolve a path relative to host workdir with traversal protection."""
        target = Path(path)
        if not target.is_absolute():
            target = Path(self._host_workdir) / path
        resolved = target.resolve()
        root = Path(self._host_workdir).resolve()
        if not str(resolved).startswith(str(root) + "/") and resolved != root:
            raise PermissionError(f"Path {resolved} is outside workspace {root}")
        return resolved

    async def read_file(self, path: str) -> str:
        """Read a file from the host bind-mount directory."""
        target = self._resolve_path(path)
        if not target.exists():
            raise FileNotFoundError(f"File not found: {target}")
        return target.read_text(encoding="utf-8", errors="replace")

    async def write_file(self, path: str, content: str) -> bool:
        """Write a file to the host bind-mount directory."""
        target = self._resolve_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return True

    async def edit_file(self, path: str, old: str, new: str) -> bool:
        """Edit a file by replacing text."""
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
        if not target.is_dir():
            return []
        return sorted(f"{e.name}{'/' if e.is_dir() else ''}" for e in target.iterdir())

    async def probe_environment(self) -> ComputeCapabilities:
        """Probe the container for hardware/software capabilities."""
        result = await self.execute(
            "uname -s && python3 --version 2>&1 && "
            "(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo 'no-gpu') && "
            "nproc && "
            "free -g 2>/dev/null | awk '/^Mem:/{print $2}' || echo 'unknown'",
            timeout=30,
        )

        # Parse output (best effort)
        lines = result.output.strip().split("\n") if result.success else []
        caps = ComputeCapabilities()
        if len(lines) >= 1:
            caps.platform = lines[0].strip()
        if len(lines) >= 2 and "Python" in lines[1]:
            version = lines[1].replace("Python ", "").strip()
            caps.python_versions = [version]
        if len(lines) >= 3 and "no-gpu" not in lines[2]:
            caps.gpu_available = True
            parts = lines[2].split(",")
            if len(parts) >= 2:
                try:
                    vram = float(parts[1].strip().replace("MiB", "").replace("GiB", "").strip())
                    # nvidia-smi reports in MiB by default
                    if "GiB" not in parts[1]:
                        vram = vram / 1024.0
                except (ValueError, IndexError):
                    vram = 0.0
                caps.gpu_info = [GPUInfo(model=parts[0].strip(), vram_gb=vram)]
                caps.gpu_count = 1
        if len(lines) >= 4:
            try:
                caps.cpu_cores = int(lines[3].strip())
            except ValueError:
                pass
        if len(lines) >= 5 and lines[4].strip() != "unknown":
            try:
                caps.total_ram_gb = float(lines[4].strip())
            except ValueError:
                pass

        return caps

    async def destroy(self) -> None:
        """No-op — Singularity containers are ephemeral by design."""
        pass
