"""SSH sandbox — remote execution via SSH/SFTP."""

import asyncio
import time

from .interface import EnvironmentInfo, ExecutionResult, SandboxInterface


class SSHSandbox(SandboxInterface):
    """Execute commands on a remote machine via SSH."""

    def __init__(self):
        self._client = None
        self._sftp = None
        self.host: str = ""
        self.port: int = 22
        self.username: str = ""
        self.key_path: str | None = None
        self.password: str | None = None
        self.workdir: str = "~"

    async def create(self, config: dict) -> "SSHSandbox":
        self.host = config.get("host", "")
        self.port = config.get("port", 22)
        self.username = config.get("username", "root")
        self.key_path = config.get("key_path")
        self.password = config.get("password")
        self.workdir = config.get("workdir", "~")

        if not self.host:
            raise ValueError("SSH config requires 'host'")

        await self._connect()
        return self

    async def _connect(self):
        """Establish SSH connection (run in thread to avoid blocking)."""
        def _do_connect():
            import paramiko
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            connect_kwargs = {
                "hostname": self.host,
                "port": self.port,
                "username": self.username,
                "timeout": 30,
            }

            if self.key_path:
                connect_kwargs["key_filename"] = self.key_path
            elif self.password:
                connect_kwargs["password"] = self.password

            client.connect(**connect_kwargs)
            sftp = client.open_sftp()
            return client, sftp

        self._client, self._sftp = await asyncio.to_thread(_do_connect)

    def _ensure_connected(self):
        if not self._client or not self._client.get_transport() or not self._client.get_transport().is_active():
            raise RuntimeError("SSH connection lost. Recreate the sandbox.")

    async def execute(self, command: str, timeout: int = 120) -> ExecutionResult:
        self._ensure_connected()
        start = time.monotonic()

        def _do_exec():
            full_cmd = f"cd {self.workdir} && {command}"
            stdin, stdout, stderr = self._client.exec_command(full_cmd, timeout=timeout)
            exit_code = stdout.channel.recv_exit_status()
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
            return out, err, exit_code

        try:
            out, err, exit_code = await asyncio.to_thread(_do_exec)
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
        except Exception as e:
            return ExecutionResult(output=f"SSH exec error: {str(e)}", success=False, exit_code=-1)

    async def read_file(self, path: str) -> str:
        self._ensure_connected()

        def _do_read():
            import io
            buf = io.BytesIO()
            self._sftp.getfo(path, buf)
            buf.seek(0)
            return buf.read().decode("utf-8", errors="replace")

        return await asyncio.to_thread(_do_read)

    async def write_file(self, path: str, content: str) -> bool:
        self._ensure_connected()

        def _do_write():
            import io
            buf = io.BytesIO(content.encode("utf-8"))
            self._sftp.putfo(buf, path)

        await asyncio.to_thread(_do_write)
        return True

    async def edit_file(self, path: str, old: str, new: str) -> bool:
        content = await self.read_file(path)
        if old not in content:
            return False
        content = content.replace(old, new, 1)
        await self.write_file(path, content)
        return True

    async def file_exists(self, path: str) -> bool:
        self._ensure_connected()

        def _do_check():
            try:
                self._sftp.stat(path)
                return True
            except FileNotFoundError:
                return False

        return await asyncio.to_thread(_do_check)

    async def list_files(self, path: str = ".") -> list[str]:
        self._ensure_connected()

        def _do_list():
            try:
                entries = self._sftp.listdir_attr(path)
                result = []
                for e in sorted(entries, key=lambda x: x.filename):
                    import stat
                    suffix = "/" if stat.S_ISDIR(e.st_mode) else ""
                    result.append(f"{e.filename}{suffix}")
                return result
            except Exception:
                return []

        return await asyncio.to_thread(_do_list)

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
            timeout=5,
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
            "free -g 2>/dev/null | grep Mem | awk '{print $7}'",
            timeout=5,
        )
        if result.success:
            try:
                info.available_ram_gb = float(result.output.strip())
            except ValueError:
                pass

        result = await self.execute(
            "pip list --format=freeze 2>/dev/null | head -30",
            timeout=10,
        )
        if result.success:
            info.installed_packages = [
                line.split("==")[0] for line in result.output.strip().split("\n")
                if "==" in line
            ]

        return info

    async def destroy(self) -> None:
        if self._sftp:
            try:
                self._sftp.close()
            except Exception:
                pass
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
        self._client = None
        self._sftp = None
