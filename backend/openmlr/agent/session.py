"""Session — per-conversation state container."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ..config import AgentConfig
from .context import ContextManager
from .types import AgentEvent


@dataclass
class Session:
    """Holds all state for a single agent conversation."""

    config: AgentConfig
    context_manager: ContextManager = field(init=False)
    event_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    submission_queue: asyncio.Queue = field(default_factory=asyncio.Queue)

    # Conversation reference (for database operations in tools)
    conversation_id: int | None = None

    # Cancellation
    _cancelled: asyncio.Event = field(default_factory=asyncio.Event)

    # Approval flow
    pending_approval: dict | None = None

    # Question/answer flow (ask_user tool)
    pending_answers: Any | None = None

    # Sandbox reference
    sandbox: Any | None = None

    # Turn counter (for title generation etc.)
    turn_count: int = 0

    # Event listeners
    _listeners: list[Callable] = field(default_factory=list)

    def __post_init__(self):
        self.context_manager = ContextManager(config=self.config)

    def on_event(self, callback: Callable) -> None:
        """Register an event listener."""
        self._listeners.append(callback)

    async def emit(self, event: AgentEvent) -> None:
        """Emit an event to the queue and all listeners."""
        await self.event_queue.put(event)
        for listener in self._listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(event)
                else:
                    listener(event)
            except Exception:
                pass

    def emit_sync(self, event: AgentEvent) -> None:
        """Non-async emit — schedules emission on the event loop."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.emit(event))
        except RuntimeError:
            # No event loop — just put in queue directly
            self.event_queue.put_nowait(event)

    def cancel(self) -> None:
        """Signal cancellation of the current agent turn."""
        self._cancelled.set()

    def is_cancelled(self) -> bool:
        return self._cancelled.is_set()

    def clear_cancel(self) -> None:
        self._cancelled.clear()

    def update_model(self, model_name: str) -> None:
        """Switch the model for this session."""
        self.config.model_name = model_name
