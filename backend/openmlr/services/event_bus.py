"""Event bus — SSE broadcasting to connected clients."""

import asyncio
import json
import logging
from typing import AsyncGenerator
from ..agent.types import AgentEvent

logger = logging.getLogger("openmlr.sse")


class EventBus:
    """Manages SSE event broadcasting to multiple clients."""

    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        queue = asyncio.Queue(maxsize=1000)
        self._subscribers.append(queue)
        logger.info(f"SSE subscriber added (total: {len(self._subscribers)})")
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        try:
            self._subscribers.remove(queue)
            logger.info(f"SSE subscriber removed (total: {len(self._subscribers)})")
        except ValueError:
            pass

    async def broadcast(self, event: AgentEvent | dict) -> None:
        if isinstance(event, AgentEvent):
            data = {"event_type": event.event_type, "data": event.data}
        elif isinstance(event, dict):
            data = event
        else:
            return

        et = data.get("event_type", "?")
        if et not in ("assistant_chunk",):  # don't spam chunk logs
            logger.info(f"Broadcasting [{et}] to {len(self._subscribers)} subscribers")

        dead = []
        for queue in self._subscribers:
            try:
                queue.put_nowait(data)
            except asyncio.QueueFull:
                dead.append(queue)

        for q in dead:
            self.unsubscribe(q)

    def broadcast_sync(self, event: AgentEvent | dict) -> None:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast(event))
        except RuntimeError:
            pass

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


async def sse_generator(queue: asyncio.Queue) -> AsyncGenerator[str, None]:
    """Generate SSE events from a subscriber queue."""
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30)
                payload = f"data: {json.dumps(event)}\n\n"
                yield payload
            except asyncio.TimeoutError:
                yield ":ping\n\n"
    except asyncio.CancelledError:
        pass
    except GeneratorExit:
        pass
