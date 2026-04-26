"""Modal sandbox — ephemeral cloud execution environment."""

import asyncio
import time

from .interface import EnvironmentInfo, ExecutionResult, SandboxInterface


class ModalSandbox(SandboxInterface):
    """Execute commands in a Modal sandbox (ephemeral cloud container)."""

    def __init__(self):
        self._sandbox = None
        self._app = None
        self.image_name: str = "python:3.12"
        self.gpu: str | None = None
        self.packages: list[str] = []

    async def create(self, config: dict) -> "ModalSandbox":
        self.image_name = config.get("image", "python:3.12")
        self.gpu = config.get("gpu")  # e.g., "T4", "A100", "A10G"
        self.packages = config.get("packages", [])

        try:
            import modal
        except ImportError:
            raise RuntimeError(
                "Modal is not installed. Install with: pip install modal-client"
            )

        def _do_create():
            app = modal.App.lookup("openmlr-sandbox", create_if_missing=True)

            # Build image
            image = modal.Image.debian_slim(python_version="3.12")
            if self.packages:
                image = image.pip_install(*self.packages)

            # Create sandbox
            sandbox_kwargs = {"image": image, "timeout": 3600}
            if self.gpu:
                sandbox_kwargs["gpu"] = self.gpu

            sandbox = modal.Sandbox.create(**sandbox_kwargs)
            return app, sandbox

        self._app, self._sandbox = await asyncio.to_thread(_do_create)
        return self

    def _ensure_active(self):
        if not self._sandbox:
            raise RuntimeError("Modal sandbox not created. Call create() first.")

    async def execute(self, command: str, timeout: int = 120) -> ExecutionResult:
        self._ensure_active()
        start = time.monotonic()

        def _do_exec():
            process = self._sandbox.exec("bash", "-c", command)
            stdout_lines = []
            stderr_lines = []

            for line in process.stdout:
                stdout_lines.append(line)
            for line in process.stderr:
                stderr_lines.append(line)

            process.wait()
            return (
                "\n".join(stdout_lines),
                "\n".join(stderr_lines),
                process.returncode,
            )

        try:
            out, err, exit_code = await asyncio.wait_for(
                asyncio.to_thread(_do_exec), timeout=timeout
            )

            output_parts = []
            if out:
                output_parts.append(out)
            if err:
                output_parts.append(f"STDERR:\n{err}")
            output = "\n".join(output_parts) if output_parts else "(no output)"

            if len(output) > 50000:
                output = output[:50000] + "\n...[truncated]"

            return ExecutionResult(
                output=output,
                success=exit_code == 0,
                exit_code=exit_code,
                duration_seconds=time.monotonic() - start,
            )
        except TimeoutError:
            return ExecutionResult(
                output=f"Command timed out after {timeout}s",
                success=False,
                exit_code=-1,
                duration_seconds=timeout,
            )
        except Exception as e:
            return ExecutionResult(
                output=f"Modal exec error: {str(e)}",
                success=False,
                exit_code=-1,
            )

    async def read_file(self, path: str) -> str:
        self._ensure_active()
        result = await self.execute(f"cat '{path}'", timeout=10)
        if not result.success:
            raise FileNotFoundError(f"Cannot read {path}: {result.output}")
        return result.output

    async def write_file(self, path: str, content: str) -> bool:
        self._ensure_active()
        # Use heredoc for safe content transfer
        content.replace("'", "'\\''")
        result = await self.execute(
            f"mkdir -p $(dirname '{path}') && cat > '{path}' << 'OPEN_MLR_EOF'\n{content}\nOPEN_MLR_EOF",
            timeout=10,
        )
        return result.success

    async def edit_file(self, path: str, old: str, new: str) -> bool:
        content = await self.read_file(path)
        if old not in content:
            return False
        content = content.replace(old, new, 1)
        return await self.write_file(path, content)

    async def file_exists(self, path: str) -> bool:
        self._ensure_active()
        result = await self.execute(f"test -f '{path}' && echo yes || echo no", timeout=5)
        return result.output.strip() == "yes"

    async def list_files(self, path: str = ".") -> list[str]:
        self._ensure_active()
        result = await self.execute(f"ls -1 '{path}'", timeout=5)
        if not result.success:
            return []
        return [line for line in result.output.strip().split("\n") if line]

    async def probe_environment(self) -> EnvironmentInfo:
        info = EnvironmentInfo()

        result = await self.execute("uname -s -r", timeout=5)
        if result.success:
            info.os = result.output.strip()

        result = await self.execute("python3 --version", timeout=5)
        if result.success:
            info.python_version = result.output.strip()

        result = await self.execute(
            "nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null",
            timeout=10,
        )
        if result.success and result.output.strip():
            info.gpu_available = True
            info.gpu_info = result.output.strip()

        result = await self.execute("df -BG --output=avail / 2>/dev/null | tail -1", timeout=5)
        if result.success:
            try:
                info.available_disk_gb = float(result.output.strip().replace("G", ""))
            except ValueError:
                pass

        result = await self.execute(
            "free -g 2>/dev/null | grep Mem | awk '{print $7}'", timeout=5
        )
        if result.success:
            try:
                info.available_ram_gb = float(result.output.strip())
            except ValueError:
                pass

        result = await self.execute("pip list --format=freeze 2>/dev/null | head -30", timeout=10)
        if result.success:
            info.installed_packages = [
                line.split("==")[0] for line in result.output.strip().split("\n")
                if "==" in line
            ]

        return info

    async def destroy(self) -> None:
        if self._sandbox:
            try:
                def _terminate():
                    self._sandbox.terminate()
                await asyncio.to_thread(_terminate)
            except Exception:
                pass
            self._sandbox = None
