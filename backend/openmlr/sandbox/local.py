"""Local sandbox — direct filesystem and shell execution."""

import asyncio
import os
import platform
import shutil
import time
from pathlib import Path

from .interface import EnvironmentInfo, ExecutionResult, SandboxInterface


class LocalSandbox(SandboxInterface):
    """Execute commands directly on the local machine."""

    def __init__(self, workdir: str = None):
        self.workdir = workdir or os.getcwd()

    async def create(self, config: dict) -> "LocalSandbox":
        self.workdir = config.get("workdir", os.getcwd())
        return self

    async def execute(self, command: str, timeout: int = 120) -> ExecutionResult:
        start = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.workdir,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )

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
                exit_code=proc.returncode,
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

    async def read_file(self, path: str) -> str:
        target = Path(path).expanduser()
        if not target.is_absolute():
            target = Path(self.workdir) / target
        return target.read_text(encoding="utf-8", errors="replace")

    async def write_file(self, path: str, content: str) -> bool:
        target = Path(path).expanduser()
        if not target.is_absolute():
            target = Path(self.workdir) / target
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
        target = Path(path).expanduser()
        if not target.is_absolute():
            target = Path(self.workdir) / target
        return target.exists()

    async def list_files(self, path: str = ".") -> list[str]:
        target = Path(path).expanduser()
        if not target.is_absolute():
            target = Path(self.workdir) / target
        return sorted([
            f"{e.name}{'/' if e.is_dir() else ''}"
            for e in target.iterdir()
        ])

    async def probe_environment(self) -> EnvironmentInfo:
        info = EnvironmentInfo(
            os=f"{platform.system()} {platform.release()}",
        )

        # Python version
        result = await self.execute("python3 --version", timeout=5)
        if result.success:
            info.python_version = result.output.strip()

        # GPU
        result = await self.execute(
            "nvidia-smi --query-gpu=name,memory.total --format=csv,noheader",
            timeout=5,
        )
        if result.success and result.output.strip():
            info.gpu_available = True
            info.gpu_info = result.output.strip()

        # Disk
        total, used, free = shutil.disk_usage(self.workdir)
        info.available_disk_gb = free / (1024 ** 3)

        # RAM
        try:
            import psutil
            info.available_ram_gb = psutil.virtual_memory().available / (1024 ** 3)
        except ImportError:
            pass

        # Key packages
        result = await self.execute("pip list --format=freeze 2>/dev/null | head -30", timeout=10)
        if result.success:
            info.installed_packages = [
                line.split("==")[0] for line in result.output.strip().split("\n")
                if "==" in line
            ]

        return info

    async def destroy(self) -> None:
        pass  # Local sandbox has nothing to clean up
