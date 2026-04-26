"""Abstract sandbox interface and data types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class EnvironmentInfo:
    """Information about a sandbox environment."""
    os: str = "unknown"
    python_version: str = "unknown"
    gpu_available: bool = False
    gpu_info: str | None = None
    installed_packages: list[str] = field(default_factory=list)
    available_disk_gb: float = 0.0
    available_ram_gb: float = 0.0


@dataclass
class ExecutionResult:
    """Result of a command execution."""
    output: str
    success: bool
    exit_code: int = 0
    duration_seconds: float = 0.0


class SandboxInterface(ABC):
    """
    Abstract interface for code execution environments.
    Providers: local, ssh, modal.
    """

    @abstractmethod
    async def create(self, config: dict) -> "SandboxInterface":
        """Initialize the sandbox with configuration."""
        ...

    @abstractmethod
    async def execute(self, command: str, timeout: int = 120) -> ExecutionResult:
        """Execute a shell command in the sandbox."""
        ...

    @abstractmethod
    async def read_file(self, path: str) -> str:
        """Read a file from the sandbox filesystem."""
        ...

    @abstractmethod
    async def write_file(self, path: str, content: str) -> bool:
        """Write a file to the sandbox filesystem."""
        ...

    @abstractmethod
    async def edit_file(self, path: str, old: str, new: str) -> bool:
        """Edit a file by string replacement."""
        ...

    @abstractmethod
    async def file_exists(self, path: str) -> bool:
        """Check if a file exists in the sandbox."""
        ...

    @abstractmethod
    async def list_files(self, path: str = ".") -> list[str]:
        """List files in a directory."""
        ...

    @abstractmethod
    async def probe_environment(self) -> EnvironmentInfo:
        """Probe the sandbox environment for capabilities."""
        ...

    @abstractmethod
    async def destroy(self) -> None:
        """Tear down the sandbox and clean up resources."""
        ...
