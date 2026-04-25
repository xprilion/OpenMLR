"""Event bus — SSE broadcasting to connected clients."""

import asyncio
import json
import logging
import os
from typing import AsyncGenerator, Optional
from ..agent.types import AgentEvent

logger = logging.getLogger("openmlr.sse")

# Check if Redis is available for pub/sub
USE_REDIS = os.environ.get("USE_REDIS_PUBSUB", "false").lower() in ("true", "1", "yes")


class EventBus:
    """Manages SSE event broadcasting to multiple clients.
    
    When USE_REDIS_PUBSUB is enabled, also forwards events to Redis
    for cross-worker communication.
    """

    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []
        self._redis_bridge_task: Optional[asyncio.Task] = None

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

        # Broadcast to local subscribers
        dead = []
        for queue in self._subscribers:
            try:
                queue.put_nowait(data)
            except asyncio.QueueFull:
                dead.append(queue)

        for q in dead:
            self.unsubscribe(q)
        
        # Also publish to Redis if enabled
        if USE_REDIS:
            try:
                from .redis_pubsub import publish_event
                await publish_event(AgentEvent(event_type=et, data=data.get("data")))
            except Exception as e:
                logger.warning(f"Failed to publish to Redis: {e}")

    def broadcast_sync(self, event: AgentEvent | dict) -> None:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast(event))
        except RuntimeError:
            pass

    async def start_redis_bridge(self) -> None:
        """Start listening to Redis events and forwarding to local subscribers."""
        if not USE_REDIS:
            return
        
        if self._redis_bridge_task is not None:
            return
        
        async def _listen():
            from .redis_pubsub import subscribe_events
            try:
                async for event in subscribe_events():
                    data = {"event_type": event.event_type, "data": event.data}
                    for queue in self._subscribers:
                        try:
                            queue.put_nowait(data)
                        except asyncio.QueueFull:
                            pass
            except Exception as e:
                logger.warning(f"Redis bridge error: {e}")
        
        self._redis_bridge_task = asyncio.create_task(_listen())
        logger.info("Redis event bridge started")

    async def stop_redis_bridge(self) -> None:
        """Stop the Redis bridge."""
        if self._redis_bridge_task:
            self._redis_bridge_task.cancel()
            try:
                await self._redis_bridge_task
            except asyncio.CancelledError:
                pass
            self._redis_bridge_task = None

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
