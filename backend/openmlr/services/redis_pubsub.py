"""Redis pub/sub for cross-worker event broadcasting."""

import os
import json
import asyncio
import logging
from contextvars import ContextVar
from typing import Optional, AsyncIterator
import redis.asyncio as redis
from ..agent.types import AgentEvent

logger = logging.getLogger("openmlr.services.redis_pubsub")

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CHANNEL_NAME = "openmlr:events"

# Context-local Redis client to handle different event loops (Celery workers)
_redis_client: ContextVar[Optional[redis.Redis]] = ContextVar("redis_client", default=None)


async def get_redis() -> redis.Redis:
    """Get a Redis client for the current context/event loop."""
    client = _redis_client.get()
    if client is None:
        # Create a new client for this context
        client = redis.from_url(REDIS_URL, decode_responses=True)
        _redis_client.set(client)
    return client


async def publish_event(event: AgentEvent) -> None:
    """Publish an event to the Redis channel."""
    try:
        client = await get_redis()
        event_data = {
            "event_type": event.event_type,
            "data": event.data,
        }
        await client.publish(CHANNEL_NAME, json.dumps(event_data))
    except Exception as e:
        logger.warning(f"Failed to publish event to Redis: {e}")


async def subscribe_events() -> AsyncIterator[AgentEvent]:
    """Subscribe to events from the Redis channel."""
    client = await get_redis()
    pubsub = client.pubsub()
    await pubsub.subscribe(CHANNEL_NAME)
    
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    yield AgentEvent(
                        event_type=data.get("event_type", "unknown"),
                        data=data.get("data"),
                    )
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in Redis message: {message['data']}")
    finally:
        await pubsub.unsubscribe(CHANNEL_NAME)
        await pubsub.close()


class RedisEventBridge:
    """
    Bridge between Redis pub/sub and local event bus.
    
    This class subscribes to Redis events and forwards them to local
    SSE subscribers, allowing background Celery workers to communicate
    with connected browser clients.
    """
    
    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._local_subscribers: list[asyncio.Queue] = []
        self._running = False
    
    async def start(self) -> None:
        """Start listening to Redis events."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._listen_loop())
        logger.info("Redis event bridge started")
    
    async def stop(self) -> None:
        """Stop listening to Redis events."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Redis event bridge stopped")
    
    def subscribe(self) -> asyncio.Queue:
        """Subscribe to receive events. Returns a queue that receives events."""
        queue: asyncio.Queue = asyncio.Queue()
        self._local_subscribers.append(queue)
        return queue
    
    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Unsubscribe from events."""
        if queue in self._local_subscribers:
            self._local_subscribers.remove(queue)
    
    async def _listen_loop(self) -> None:
        """Internal loop that listens to Redis and forwards events."""
        while self._running:
            try:
                async for event in subscribe_events():
                    if not self._running:
                        break
                    # Forward to all local subscribers
                    for queue in self._local_subscribers:
                        try:
                            queue.put_nowait(event)
                        except asyncio.QueueFull:
                            pass  # Drop event if queue is full
            except Exception as e:
                logger.warning(f"Redis subscription error: {e}")
                if self._running:
                    await asyncio.sleep(1)  # Reconnect delay


# Global instance
_redis_bridge: Optional[RedisEventBridge] = None


async def get_redis_bridge() -> RedisEventBridge:
    """Get or create the global Redis event bridge."""
    global _redis_bridge
    if _redis_bridge is None:
        _redis_bridge = RedisEventBridge()
        await _redis_bridge.start()
    return _redis_bridge
