"""Event bus — SSE broadcasting to connected clients with replay buffer and channel scoping."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections import deque
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from ..agent.types import AgentEvent

logger = logging.getLogger("openmlr.sse")

# Check if Redis is available for pub/sub
USE_REDIS = os.environ.get("USE_REDIS_PUBSUB", "false").lower() in ("true", "1", "yes")
EVENT_BUFFER_SIZE = int(os.environ.get("EVENT_BUFFER_SIZE", "2000"))


@dataclass
class BufferedEvent:
    """An event stored in the EventBus replay ring buffer with sequence metadata."""

    seq: int
    event_type: str
    data: Any
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    conv_id: str | None = None
    project_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "seq": self.seq,
            "event_type": self.event_type,
            "data": self.data,
            "timestamp": self.timestamp,
            "conv_id": self.conv_id,
            "project_id": self.project_id,
        }

    def to_sse(self) -> str:
        payload = json.dumps(self.to_dict())
        return f"id: {self.seq}\nevent: {self.event_type}\ndata: {payload}\n\n"


@dataclass
class Subscription:
    """Internal subscription record for scoped client routing."""

    queue: asyncio.Queue
    conv_id: str | None = None
    project_id: str | None = None
    event_types: set[str] | None = None

    def matches(self, event: BufferedEvent) -> bool:
        if self.conv_id and event.conv_id and self.conv_id != event.conv_id:
            return False
        if self.project_id and event.project_id and self.project_id != event.project_id:
            return False
        if self.event_types and event.event_type not in self.event_types:
            return False
        return True


class EventBus:
    """Manages SSE event broadcasting to multiple clients with replay buffer & scoped routing."""

    def __init__(self, buffer_size: int = EVENT_BUFFER_SIZE):
        self._subscriptions: list[Subscription] = []
        self._subscribers: list[asyncio.Queue] = []  # Backwards compatibility
        self._buffer: deque[BufferedEvent] = deque(maxlen=buffer_size)
        self._seq_counter: int = 0
        self._redis_bridge_task: asyncio.Task | None = None
        self._total_broadcasted: int = 0

    def subscribe(
        self,
        conv_id: str | None = None,
        project_id: str | None = None,
        event_types: list[str] | None = None,
        last_event_id: int | None = None,
    ) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        types_set = set(event_types) if event_types else None
        sub = Subscription(
            queue=queue,
            conv_id=conv_id,
            project_id=project_id,
            event_types=types_set,
        )

        # Replay missed events if requested
        if last_event_id is not None and last_event_id >= 0:
            for event in self._buffer:
                if event.seq > last_event_id and sub.matches(event):
                    try:
                        queue.put_nowait(event.to_dict())
                    except asyncio.QueueFull:
                        break

        self._subscriptions.append(sub)
        self._subscribers.append(queue)
        logger.info(
            "SSE subscriber added (conv_id=%s, total: %d)",
            conv_id,
            len(self._subscriptions),
        )
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscriptions = [s for s in self._subscriptions if s.queue is not queue]
        try:
            self._subscribers.remove(queue)
        except ValueError:
            pass
        logger.info("SSE subscriber removed (total: %d)", len(self._subscriptions))

    async def broadcast(self, event: AgentEvent | dict) -> BufferedEvent | None:
        if isinstance(event, AgentEvent):
            data = event.data
            et = event.event_type
        elif isinstance(event, dict):
            data = event.get("data")
            et = event.get("event_type", "?")
        else:
            return None

        # Extract context routing metadata
        conv_id = None
        project_id = None
        if isinstance(data, dict):
            conv_id = data.get("conv_id") or data.get("conversation_id")
            project_id = data.get("project_id")

        self._seq_counter += 1
        self._total_broadcasted += 1
        buffered = BufferedEvent(
            seq=self._seq_counter,
            event_type=et,
            data=data,
            conv_id=conv_id,
            project_id=project_id,
        )
        self._buffer.append(buffered)

        payload_dict = buffered.to_dict()

        if et not in ("assistant_chunk",):  # don't spam chunk logs
            logger.info(
                "Broadcasting [#%d %s] to %d subscribers",
                buffered.seq,
                et,
                len(self._subscriptions),
            )

        dead_subs = []
        for sub in self._subscriptions:
            if sub.matches(buffered):
                try:
                    sub.queue.put_nowait(payload_dict)
                except asyncio.QueueFull:
                    dead_subs.append(sub)

        for s in dead_subs:
            self.unsubscribe(s.queue)

        # Also publish to Redis if enabled
        if USE_REDIS:
            try:
                from .redis_pubsub import publish_event

                await publish_event(AgentEvent(event_type=et, data=data))
            except Exception as e:
                logger.warning("Failed to publish to Redis: %s", e)

        return buffered

    def broadcast_sync(self, event: AgentEvent | dict) -> None:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast(event))
        except RuntimeError:
            pass

    def get_replay_events(
        self,
        since_seq: int,
        conv_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Retrieve recent events from the ring buffer after a given sequence ID."""
        events = []
        for ev in self._buffer:
            if ev.seq > since_seq:
                if conv_id and ev.conv_id and ev.conv_id != conv_id:
                    continue
                events.append(ev.to_dict())
                if len(events) >= limit:
                    break
        return events

    def get_metrics(self) -> dict[str, Any]:
        """Return runtime health and throughput statistics."""
        oldest = self._buffer[0].seq if self._buffer else 0
        newest = self._buffer[-1].seq if self._buffer else 0
        return {
            "total_broadcasted": self._total_broadcasted,
            "active_subscribers": len(self._subscriptions),
            "buffer_size": len(self._buffer),
            "buffer_capacity": self._buffer.maxlen,
            "oldest_seq": oldest,
            "newest_seq": newest,
        }

    async def start_redis_bridge(self) -> None:
        """Start listening to Redis events and forwarding to local subscribers."""
        if not USE_REDIS:
            logger.info("USE_REDIS_PUBSUB not enabled, skipping Redis bridge")
            return

        if self._redis_bridge_task is not None:
            return

        async def _listen():
            from .redis_pubsub import subscribe_events

            logger.info("Redis subscription loop started")
            try:
                async for event in subscribe_events():
                    await self.broadcast(event)
            except Exception as e:
                logger.warning("Redis bridge error: %s", e)

        self._redis_bridge_task = asyncio.create_task(_listen())
        logger.info("Redis event bridge started")

    async def stop_redis_bridge(self) -> None:
        """Stop the Redis bridge."""
        if self._redis_bridge_task:
            self._redis_bridge_task.cancel()
            try:
                await self._redis_bridge_task
            finally:
                self._redis_bridge_task = None

    @property
    def subscriber_count(self) -> int:
        return len(self._subscriptions)


async def sse_generator(
    queue: asyncio.Queue,
    heartbeat_interval: float = 25.0,
) -> AsyncGenerator[str, None]:
    """Generate SSE formatted events from a subscriber queue."""
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=heartbeat_interval)
                seq = event.get("seq")
                event_type = event.get("event_type", "message")
                payload = json.dumps(event)
                if seq is not None:
                    yield f"id: {seq}\nevent: {event_type}\ndata: {payload}\n\n"
                else:
                    yield f"data: {payload}\n\n"
            except TimeoutError:
                yield ":ping\n\n"
    except asyncio.CancelledError:
        raise
    except GeneratorExit:
        pass
