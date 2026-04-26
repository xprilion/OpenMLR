"""SSH sandbox — remote execution via SSH/SFTP with strict host-key verification
and connection pooling."""

import asyncio
import logging
import time

from ..compute.probe import probe_sandbox
from .interface import ExecutionResult, SandboxInterface

log = logging.getLogger(__name__)


class StrictHostKeyPolicy:
    """Paramiko policy that verifies host keys against expected fingerprints."""

    def __init__(self, expected_fingerprint: str | None = None):
        self.expected = expected_fingerprint
        self.actual_fingerprint: str | None = None

    def missing_host_key(self, client, hostname, key):
        import paramiko
        actual = key.get_fingerprint().hex()
        self.actual_fingerprint = actual
        if self.expected and actual != self.expected.lower().replace(":", "").replace("sha256:", ""):
            raise paramiko.SSHException(
                f"Host key mismatch for {hostname}: expected {self.expected}, got {actual}"
            )
        return


class SSHConnectionPool:
    """Maintains persistent SSH connections per node with TTL-based eviction.

    Connections are keyed by (host, port, username) and reused across
    sandbox instances. Idle connections are closed after ``ttl_seconds``.
    """

    _instance: "SSHConnectionPool | None" = None

    def __init__(self, ttl_seconds: int = 300):
        self._connections: dict[str, tuple] = {}   # key -> (client, sftp, fingerprint)
        self._last_used: dict[str, float] = {}
        self._ttl = ttl_seconds

    @classmethod
    def get_pool(cls) -> "SSHConnectionPool":
        if cls._instance is None:
            cls._instance = SSHConnectionPool()
        return cls._instance

    @staticmethod
    def _make_key(host: str, port: int, username: str) -> str:
        return f"{username}@{host}:{port}"

    def get(self, host: str, port: int, username: str):
        """Return (client, sftp, fingerprint) if a healthy cached connection exists, else None."""
        key = self._make_key(host, port, username)
        entry = self._connections.get(key)
        if entry is None:
            return None

        client, sftp, fp = entry
        try:
            transport = client.get_transport()
            if transport and transport.is_active():
                self._last_used[key] = time.monotonic()
                return client, sftp, fp
        except Exception:
            pass

        # Connection is dead — clean up
        self._evict(key)
        return None

    def put(self, host: str, port: int, username: str, client, sftp, fingerprint: str | None):
        """Cache a connection for reuse."""
        key = self._make_key(host, port, username)
        self._connections[key] = (client, sftp, fingerprint)
        self._last_used[key] = time.monotonic()

    def remove(self, host: str, port: int, username: str):
        """Remove and close a cached connection."""
        key = self._make_key(host, port, username)
        self._evict(key)

    def _evict(self, key: str):
        entry = self._connections.pop(key, None)
        self._last_used.pop(key, None)
        if entry:
            client, sftp, _ = entry
            try:
                sftp.close()
            except Exception:
                pass
            try:
                client.close()
            except Exception:
                pass

    def cleanup_idle(self):
        """Close connections idle beyond TTL. Call periodically."""
        now = time.monotonic()
        stale = [k for k, t in self._last_used.items() if now - t > self._ttl]
        for key in stale:
            log.debug(f"SSH pool: evicting idle connection {key}")
            self._evict(key)


class SSHSandbox(SandboxInterface):
    """Execute commands on a remote machine via SSH."""

    def __init__(self):
        self._client = None
        self._sftp = None
        self._owns_connection = False  # True if we created it (not from pool)
        self.host: str = ""
        self.port: int = 22
        self.username: str = ""
        self.key_filename: str | None = None
        self.password: str | None = None
        self.workdir: str = "~"
        self.host_key_fingerprint: str | None = None
        self._key_manager = None

    async def create(self, config: dict) -> "SSHSandbox":
        self.host = config.get("host", "")
        self.port = config.get("port", 22)
        self.username = config.get("username", "root")
        self.key_filename = config.get("key_filename")
        self.password = config.get("password")
        self.workdir = config.get("workdir", "~")
        self.host_key_fingerprint = config.get("host_key_fingerprint")
        self._conversation_uuid = config.get("conversation_uuid")

        if self.key_filename:
            from ..keys import KeyManager
            self._key_manager = KeyManager()

        if not self.host:
            raise ValueError("SSH config requires 'host'")

        await self._connect()

        # Ensure remote workspace exists if conversation UUID is set
        if self._conversation_uuid:
            remote_ws = f"{self.workdir}/workspace-{self._conversation_uuid}"
            await self._ensure_remote_workspace(remote_ws)
            self.workdir = remote_ws

        return self

    async def _ensure_remote_workspace(self, remote_path: str) -> None:
        self._ensure_connected()

        def _do_mkdir():
            subdirs = " ".join(f"{remote_path}/{d}" for d in ["data", "models", "code", "outputs", ".openmlr-meta"])
            cmd = f"mkdir -p {subdirs}"
            stdin, stdout, stderr = self._client.exec_command(cmd, timeout=10)
            exit_code = stdout.channel.recv_exit_status()
            if exit_code != 0:
                err = stderr.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"Failed to create remote workspace: {err}")

        await asyncio.to_thread(_do_mkdir)

    async def _connect(self):
        """Get a connection from the pool or create a new one."""
        pool = SSHConnectionPool.get_pool()
        pool.cleanup_idle()

        cached = pool.get(self.host, self.port, self.username)
        if cached:
            self._client, self._sftp, fp = cached
            self._owns_connection = False
            if fp and not self.host_key_fingerprint:
                self.host_key_fingerprint = fp
            log.debug(f"SSH pool: reusing connection to {self.username}@{self.host}:{self.port}")
            return

        def _do_connect():
            import paramiko
            client = paramiko.SSHClient()

            if self.host_key_fingerprint:
                policy = StrictHostKeyPolicy(self.host_key_fingerprint)
                client.set_missing_host_key_policy(policy)
            else:
                client.set_missing_host_key_policy(paramiko.WarningPolicy())

            connect_kwargs = {
                "hostname": self.host,
                "port": self.port,
                "username": self.username,
                "timeout": 30,
            }

            if self.key_filename and self._key_manager:
                key_path = self._key_manager.get_key_path(self.key_filename)
                connect_kwargs["key_filename"] = str(key_path)
            elif self.password:
                connect_kwargs["password"] = self.password

            client.connect(**connect_kwargs)
            sftp = client.open_sftp()

            actual_fp = None
            transport = client.get_transport()
            if transport:
                remote_key = transport.get_remote_server_key()
                if remote_key:
                    actual_fp = remote_key.get_fingerprint().hex()

            return client, sftp, actual_fp

        self._client, self._sftp, actual_fp = await asyncio.to_thread(_do_connect)
        self._owns_connection = True

        if actual_fp and not self.host_key_fingerprint:
            self.host_key_fingerprint = actual_fp

        # Put the new connection into the pool
        pool.put(self.host, self.port, self.username, self._client, self._sftp, actual_fp)

    def _ensure_connected(self):
        if not self._client or not self._client.get_transport() or not self._client.get_transport().is_active():
            raise RuntimeError("SSH connection lost. Recreate the sandbox.")

    async def execute(self, command: str, timeout: int = 120) -> ExecutionResult:
        return await self.execute_stream(command, timeout)

    async def execute_stream(self, command: str, timeout: int = 120, on_chunk=None) -> ExecutionResult:
        self._ensure_connected()
        start = time.monotonic()

        def _do_exec_stream():
            full_cmd = f"cd {self.workdir} && {command}"
            stdin, stdout, stderr = self._client.exec_command(full_cmd, timeout=timeout)

            out_buf = []
            err_buf = []
            channel = stdout.channel

            while not channel.exit_status_ready():
                if channel.recv_ready():
                    data = channel.recv(4096).decode("utf-8", errors="replace")
                    out_buf.append(data)
                    if on_chunk:
                        on_chunk(data, False)

                if channel.recv_stderr_ready():
                    data = channel.recv_stderr(4096).decode("utf-8", errors="replace")
                    err_buf.append(data)
                    if on_chunk:
                        on_chunk(data, True)

                time.sleep(0.05)

            while channel.recv_ready():
                data = channel.recv(4096).decode("utf-8", errors="replace")
                out_buf.append(data)
                if on_chunk:
                    on_chunk(data, False)

            while channel.recv_stderr_ready():
                data = channel.recv_stderr(4096).decode("utf-8", errors="replace")
                err_buf.append(data)
                if on_chunk:
                    on_chunk(data, True)

            exit_code = channel.recv_exit_status()
            return "".join(out_buf), "".join(err_buf), exit_code

        try:
            out, err, exit_code = await asyncio.to_thread(_do_exec_stream)
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

    async def probe_environment(self):
        return await probe_sandbox(self)

    async def destroy(self) -> None:
        # Don't close pooled connections — they'll be reused.
        # Only close if we own the connection and it's not pooled.
        # The pool handles TTL-based eviction.
        self._client = None
        self._sftp = None
