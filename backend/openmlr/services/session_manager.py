"""Session manager — manages per-conversation agent sessions."""

import logging

from ..agent.llm import LLMProvider
from ..agent.loop import run_agent_turn
from ..agent.prompts import build_system_prompt
from ..agent.session import Session
from ..agent.types import AgentEvent
from ..config import AgentConfig
from ..sandbox.manager import SandboxManager
from ..tools.mcp import MCPManager
from ..tools.registry import ToolRouter, create_tool_router
from .event_bus import EventBus

log = logging.getLogger(__name__)


class ActiveSession:
    """Container for a single active session and its supporting objects."""

    def __init__(
        self,
        session: Session,
        tool_router: ToolRouter,
        sandbox_manager: SandboxManager,
        mcp_manager: MCPManager,
        conversation_id: int,
        uuid: str,
    ):
        self.session = session
        self.tool_router = tool_router
        self.sandbox_manager = sandbox_manager
        self.mcp_manager = mcp_manager
        self.conversation_id = conversation_id
        self.uuid = uuid
        self._persist_wired = False


class SessionManager:
    """Manages multiple agent sessions keyed by conversation ID."""

    def __init__(self, event_bus: EventBus, default_config: AgentConfig):
        self.sessions: dict[int, ActiveSession] = {}
        self.event_bus = event_bus
        self.default_config = default_config
        self.current_conversation_id: int | None = None
        self._is_processing: bool = False
        self._message_queues: dict[int, list[str]] = {}

    def get_session(self, conversation_id: int) -> ActiveSession | None:
        return self.sessions.get(conversation_id)

    def get_current_session(self) -> ActiveSession | None:
        if self.current_conversation_id:
            return self.sessions.get(self.current_conversation_id)
        return None

    async def get_or_create_session(
        self,
        conversation_id: int,
        uuid: str,
        model: str | None = None,
        mode: str = "general",
        existing_messages: list[dict] = None,
        username: str = "user",
        user_id: int | None = None,
        db = None,
    ) -> ActiveSession:
        """Get existing session or create a new one with system prompt."""
        existing = self.sessions.get(conversation_id)
        if existing:
            return existing

        config = AgentConfig(
            model_name=model or self.default_config.model_name,
            max_iterations=self.default_config.max_iterations,
            stream=self.default_config.stream,
            yolo_mode=self.default_config.yolo_mode,
            compact_threshold_ratio=self.default_config.compact_threshold_ratio,
            untouched_messages=self.default_config.untouched_messages,
            default_max_tokens=self.default_config.default_max_tokens,
            research_model=self.default_config.research_model,
            title_model=self.default_config.title_model,
        )

        session = Session(config=config, conversation_id=conversation_id)

        # Import here (not at module level) to avoid circular imports
        from ..db import operations as ops

        # Determine effective compute node
        effective_node = None
        if user_id and db:
            try:
                # Check conversation override
                conv = await ops.get_conversation_by_id(db, conversation_id)
                if conv and conv.extra:
                    override_node_id = conv.extra.get("compute_node_id")
                    if override_node_id:
                        effective_node = await ops.get_compute_node_by_id(db, override_node_id, user_id)

                # Fall back to user default
                if not effective_node:
                    effective_node = await ops.get_default_compute_node(db, user_id)

                if effective_node:
                    log.info(f"Session {conversation_id}: using compute node '{effective_node.name}' ({effective_node.type})")
            except Exception as e:
                log.warning(f"Session {conversation_id}: failed to load compute node - {e}")

        # Initialize workspace manager and sandbox manager
        from ..compute import WorkspaceManager
        workspace_manager = WorkspaceManager()
        sandbox_manager = SandboxManager(
            workspace_manager=workspace_manager,
            conversation_uuid=uuid,
        )

        # If a compute node is configured, activate it
        if effective_node:
            try:
                await sandbox_manager.create(effective_node.type, effective_node.config)
            except Exception as e:
                log.warning(f"Session {conversation_id}: failed to create sandbox for node '{effective_node.name}' - {e}")

        tool_router = create_tool_router(sandbox_manager)
        # Inject user/db context for compute tools
        tool_router.set_context(user_id=user_id, db=db)
        mcp_manager = MCPManager()

        # Load MCP servers from user settings if available
        if user_id and db:
            try:
                user_settings = await ops.get_all_settings(db, user_id, category="mcp")
                mcp_settings = user_settings.get("mcp", {})
                mcp_servers = mcp_settings.get("servers", {})

                if mcp_servers:
                    count = await mcp_manager.connect_servers(
                        mcp_servers,
                        tool_router,
                        blocklist=set(),
                    )
                    if count > 0:
                        log.info(f"Session {conversation_id}: loaded {count} MCP tools")
            except Exception as e:
                log.warning(f"Session {conversation_id}: failed to load MCP servers - {e}")

        # Build compute environment info for system prompt
        compute_env = ""
        if effective_node:
            caps = effective_node.capabilities or {}
            lines = [f"\n## Active Compute Environment: {effective_node.name} ({effective_node.type})"]
            if caps.get("platform"):
                lines.append(f"- Platform: {caps['platform']}")
            if caps.get("cpu_cores"):
                lines.append(f"- CPU: {caps['cpu_cores']} cores ({caps.get('cpu_arch', 'unknown')})")
            if caps.get("available_ram_gb"):
                lines.append(f"- RAM: {caps['available_ram_gb']:.1f} GB available")
            if caps.get("gpu_available"):
                gpu_info = caps.get("gpu_info", [])
                for gpu in gpu_info[:1]:
                    lines.append(f"- GPU: {gpu.get('model', 'unknown')} ({gpu.get('vram_gb', 0):.0f} GB VRAM)")
                    if gpu.get("cuda_version"):
                        lines.append(f"  - CUDA: {gpu['cuda_version']}")
            if caps.get("python_versions"):
                lines.append(f"- Python: {', '.join(caps['python_versions'])}")
            if caps.get("docker_available"):
                lines.append("- Docker: available")
            if caps.get("installed_packages"):
                pkgs = caps["installed_packages"][:10]
                lines.append(f"- Key packages: {', '.join(pkgs)}")

            # Add available nodes for context
            all_nodes = []
            if user_id and db:
                try:
                    all_nodes = await ops.get_compute_nodes(db, user_id)
                except Exception:
                    pass
            if len(all_nodes) > 1:
                lines.append("\n### Other Available Nodes")
                for node in all_nodes:
                    if node.id != effective_node.id:
                        status = "online" if node.health_status == "online" else "offline"
                        lines.append(f"- {node.name} ({node.type}): {status}")

            compute_env = "\n".join(lines)

        # Build and set system prompt (after MCP tools are registered)
        session.context_manager.system_prompt = build_system_prompt(
            tool_specs=tool_router.get_raw_specs(),
            mode=mode,
            username=username,
            compute_env=compute_env,
        )

        # Wire event broadcasting
        async def _broadcast(event: AgentEvent):
            await self.event_bus.broadcast(event)
        session.on_event(_broadcast)

        # Load existing messages (but skip user messages that would be re-added)
        if existing_messages:
            for msg in existing_messages:
                session.context_manager.add_message(msg)

        active = ActiveSession(
            session=session,
            tool_router=tool_router,
            sandbox_manager=sandbox_manager,
            mcp_manager=mcp_manager,
            conversation_id=conversation_id,
            uuid=uuid,
        )
        self.sessions[conversation_id] = active
        return active

    async def remove_session(self, conversation_id: int) -> None:
        active = self.sessions.pop(conversation_id, None)
        if active:
            # Cancel any running agent turn
            active.session.cancel()
            # Resolve any pending question/approval futures to unblock the loop
            if hasattr(active.session, 'pending_answers') and active.session.pending_answers:
                try:
                    if not active.session.pending_answers.done():
                        active.session.pending_answers.cancel()
                except Exception:
                    pass
            try:
                await active.sandbox_manager.destroy()
            except Exception:
                pass
            # Disconnect MCP servers
            try:
                await active.mcp_manager.disconnect_all()
            except Exception:
                pass
        if self.current_conversation_id == conversation_id:
            self.current_conversation_id = None

    async def process_message(
        self,
        conversation_id: int,
        message: str,
        mode: str = None,
    ) -> None:
        """Queue and process a user message."""
        queue = self._message_queues.setdefault(conversation_id, [])
        queue.append((message, mode))

        if self._is_processing:
            return

        self._is_processing = True
        await self.event_bus.broadcast(
            AgentEvent(event_type="status", data={"status": "thinking..."})
        )

        try:
            active = self.sessions.get(conversation_id)
            if not active:
                return

            while queue:
                msg, msg_mode = queue.pop(0)
                try:
                    await run_agent_turn(active.session, active.tool_router, msg, mode=msg_mode)
                except Exception as e:
                    await self.event_bus.broadcast(
                        AgentEvent(event_type="error", data={"error": str(e)})
                    )
        finally:
            self._is_processing = False
            await self.event_bus.broadcast(
                AgentEvent(event_type="status", data={"status": "ready"})
            )

    async def generate_title(
        self,
        conversation_id: int,
        messages: list[dict],
    ) -> str | None:
        active = self.sessions.get(conversation_id)
        if not active:
            return None
        try:
            return await LLMProvider.generate_title(messages, active.session.config)
        except Exception:
            return None

    @property
    def is_processing(self) -> bool:
        return self._is_processing
