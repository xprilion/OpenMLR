"""SandboxManager — lifecycle management and provider selection.

The sandbox handles code execution on a compute resource.
The workspace (project-scoped) is decoupled: it persists independently
of which compute resource is active. The sandbox receives the workspace
path so it can operate within the project directory.
"""

from .interface import SandboxInterface
from .local import LocalSandbox
from .modal_sandbox import ModalSandbox
from .ssh import SSHSandbox


class SandboxManager:
    """Manages sandbox lifecycle: create, switch, destroy.

    Workspace and compute are decoupled:
    - project_workspace_path: persistent project directory (survives compute changes)
    - provider/config: determines WHERE code executes (local, ssh, modal)
    """

    def __init__(
        self,
        workspace_manager=None,
        conversation_uuid: str = None,
        project_workspace_path: str = None,
    ):
        self._active: SandboxInterface | None = None
        self.active_type: str = "none"
        self._workspace_manager = workspace_manager
        self._conversation_uuid = conversation_uuid
        self._project_workspace_path = project_workspace_path

    def get_active(self) -> SandboxInterface | None:
        return self._active

    async def create(self, provider: str, config: dict = None) -> SandboxInterface:
        """Create a new sandbox of the specified type."""
        # Destroy existing sandbox first
        if self._active:
            await self.destroy()

        config = config or {}

        # Inject workspace and conversation context
        config["conversation_uuid"] = self._conversation_uuid
        if self._project_workspace_path:
            config["project_workspace_path"] = self._project_workspace_path

        if provider == "local":
            sandbox = LocalSandbox(workspace_manager=self._workspace_manager)
        elif provider == "ssh":
            sandbox = SSHSandbox()
        elif provider == "modal":
            sandbox = ModalSandbox()
        elif provider == "singularity":
            from .singularity import SingularitySandbox

            sandbox = SingularitySandbox()
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
