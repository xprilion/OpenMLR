"""SandboxManager — lifecycle management and provider selection."""

from typing import Optional
from .interface import SandboxInterface
from .local import LocalSandbox
from .ssh import SSHSandbox
from .modal_sandbox import ModalSandbox


class SandboxManager:
    """Manages sandbox lifecycle: create, switch, destroy."""

    def __init__(self):
        self._active: Optional[SandboxInterface] = None
        self.active_type: str = "none"

    def get_active(self) -> Optional[SandboxInterface]:
        return self._active

    async def create(self, provider: str, config: dict = None) -> SandboxInterface:
        """Create a new sandbox of the specified type."""
        # Destroy existing sandbox first
        if self._active:
            await self.destroy()

        config = config or {}

        if provider == "local":
            sandbox = LocalSandbox()
        elif provider == "ssh":
            sandbox = SSHSandbox()
        elif provider == "modal":
            sandbox = ModalSandbox()
        else:
            raise ValueError(f"Unknown sandbox provider: {provider}")

        await sandbox.create(config)
        self._active = sandbox
        self.active_type = provider
        return sandbox

    async def destroy(self) -> None:
        """Destroy the active sandbox."""
        if self._active:
            try:
                await self._active.destroy()
            except Exception:
                pass
            self._active = None
            self.active_type = "none"

    async def ensure_local(self) -> LocalSandbox:
        """Ensure a local sandbox is active (convenience)."""
        if not self._active or self.active_type != "local":
            return await self.create("local")
        return self._active
