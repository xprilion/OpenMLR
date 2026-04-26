"""Session manager — manages per-conversation agent sessions."""

import asyncio
from typing import Optional
from ..agent.session import Session
from ..agent.types import AgentEvent
from ..agent.loop import run_agent_turn
from ..agent.llm import LLMProvider
from ..agent.prompts import build_system_prompt
from ..config import AgentConfig
from ..tools.registry import create_tool_router, ToolRouter
from ..sandbox.manager import SandboxManager
from .event_bus import EventBus


class ActiveSession:
    """Container for a single active session and its supporting objects."""

    def __init__(
        self,
        session: Session,
        tool_router: ToolRouter,
        sandbox_manager: SandboxManager,
        conversation_id: int,
        uuid: str,
    ):
        self.session = session
        self.tool_router = tool_router
        self.sandbox_manager = sandbox_manager
        self.conversation_id = conversation_id
        self.uuid = uuid
        self._persist_wired = False


class SessionManager:
    """Manages multiple agent sessions keyed by conversation ID."""

    def __init__(self, event_bus: EventBus, default_config: AgentConfig):
        self.sessions: dict[int, ActiveSession] = {}
        self.event_bus = event_bus
        self.default_config = default_config
        self.current_conversation_id: Optional[int] = None
        self._is_processing: bool = False
        self._message_queues: dict[int, list[str]] = {}

    def get_session(self, conversation_id: int) -> Optional[ActiveSession]:
        return self.sessions.get(conversation_id)

    def get_current_session(self) -> Optional[ActiveSession]:
        if self.current_conversation_id:
            return self.sessions.get(self.current_conversation_id)
        return None

    async def get_or_create_session(
        self,
        conversation_id: int,
        uuid: str,
        model: Optional[str] = None,
        mode: str = "general",
        existing_messages: list[dict] = None,
        username: str = "user",
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
        sandbox_manager = SandboxManager()
        tool_router = create_tool_router(sandbox_manager)

        # Build and set system prompt
        session.context_manager.system_prompt = build_system_prompt(
            tool_specs=tool_router.get_raw_specs(),
            mode=mode,
            username=username,
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
    ) -> Optional[str]:
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
