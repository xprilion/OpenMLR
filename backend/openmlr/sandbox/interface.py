"""Abstract sandbox interface and data types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..compute.capabilities import ComputeCapabilities


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

    async def execute_stream(self, command: str, timeout: int = 120, on_chunk=None):
        """Execute a command and stream output chunks via callback.

        Args:
            command: Shell command to execute
            timeout: Timeout in seconds
            on_chunk: Callback function(text: str, is_stderr: bool) called for each chunk

        Returns:
            ExecutionResult with full output
        """
        # Default implementation falls back to regular execute
        result = await self.execute(command, timeout)
        if on_chunk and result.output:
            on_chunk(result.output, False)
        return result

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
    async def probe_environment(self) -> ComputeCapabilities:
        """Probe the sandbox environment for capabilities."""
        ...

    @abstractmethod
    async def destroy(self) -> None:
        """Tear down the sandbox and clean up resources."""
        ...
