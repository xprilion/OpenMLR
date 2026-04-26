"""Tests for openmlr.services.event_bus.EventBus."""

import asyncio

import pytest

from openmlr.agent.types import AgentEvent
from openmlr.services.event_bus import EventBus

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def bus() -> EventBus:
    return EventBus()


# ---------------------------------------------------------------------------
# subscribe
# ---------------------------------------------------------------------------

class TestSubscribe:
    def test_subscribe_returns_queue(self, bus: EventBus):
        queue = bus.subscribe()
        assert isinstance(queue, asyncio.Queue)

    def test_subscribe_adds_to_subscribers(self, bus: EventBus):
        assert bus.subscriber_count == 0
        q1 = bus.subscribe()
        assert bus.subscriber_count == 1
        q2 = bus.subscribe()
        assert bus.subscriber_count == 2

    def test_subscribe_queue_has_maxsize(self, bus: EventBus):
        queue = bus.subscribe()
        assert queue.maxsize == 1000


# ---------------------------------------------------------------------------
# unsubscribe
# ---------------------------------------------------------------------------

class TestUnsubscribe:
    def test_unsubscribe_removes_queue(self, bus: EventBus):
        q = bus.subscribe()
        assert bus.subscriber_count == 1
        bus.unsubscribe(q)
        assert bus.subscriber_count == 0

    def test_unsubscribe_unknown_queue_is_noop(self, bus: EventBus):
        unknown = asyncio.Queue()
        bus.unsubscribe(unknown)  # should not raise
        assert bus.subscriber_count == 0

    def test_unsubscribe_only_removes_target(self, bus: EventBus):
        q1 = bus.subscribe()
        q2 = bus.subscribe()
        bus.unsubscribe(q1)
        assert bus.subscriber_count == 1
        # The remaining subscriber should be q2
        assert bus._subscribers[0] is q2


# ---------------------------------------------------------------------------
# subscriber_count
# ---------------------------------------------------------------------------

class TestSubscriberCount:
    def test_starts_at_zero(self, bus: EventBus):
        assert bus.subscriber_count == 0

    def test_increments_on_subscribe(self, bus: EventBus):
        bus.subscribe()
        bus.subscribe()
        bus.subscribe()
        assert bus.subscriber_count == 3

    def test_decrements_on_unsubscribe(self, bus: EventBus):
        q = bus.subscribe()
        bus.subscribe()
        bus.unsubscribe(q)
        assert bus.subscriber_count == 1


# ---------------------------------------------------------------------------
# broadcast
# ---------------------------------------------------------------------------

class TestBroadcast:
    @pytest.mark.asyncio
    async def test_broadcast_dict_event(self, bus: EventBus):
        q = bus.subscribe()
        event = {"event_type": "test", "data": {"msg": "hello"}}
        await bus.broadcast(event)
        item = q.get_nowait()
        assert item == event

    @pytest.mark.asyncio
    async def test_broadcast_agent_event_serialized_to_dict(self, bus: EventBus):
        q = bus.subscribe()
        agent_event = AgentEvent(event_type="status", data={"key": "val"})
        await bus.broadcast(agent_event)
        item = q.get_nowait()
        assert isinstance(item, dict)
        assert item["event_type"] == "status"
        assert item["data"] == {"key": "val"}

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all_subscribers(self, bus: EventBus):
        q1 = bus.subscribe()
        q2 = bus.subscribe()
        q3 = bus.subscribe()
        await bus.broadcast({"event_type": "ping", "data": None})
        for q in (q1, q2, q3):
            assert not q.empty()
            item = q.get_nowait()
            assert item["event_type"] == "ping"

    @pytest.mark.asyncio
    async def test_broadcast_removes_dead_subscribers_on_full_queue(self, bus: EventBus):
        """When a subscriber's queue is full, broadcast drops it."""
        # Create a queue with maxsize=1 to force QueueFull quickly
        tiny_q = asyncio.Queue(maxsize=1)
        bus._subscribers.append(tiny_q)
        healthy_q = bus.subscribe()

        assert bus.subscriber_count == 2

        # Fill the tiny queue
        tiny_q.put_nowait({"event_type": "fill", "data": None})

        # Now broadcast — tiny_q is full, should be removed
        await bus.broadcast({"event_type": "boom", "data": None})

        assert bus.subscriber_count == 1
        assert bus._subscribers[0] is healthy_q
        # healthy_q should have received the event
        assert healthy_q.get_nowait()["event_type"] == "boom"

    @pytest.mark.asyncio
    async def test_broadcast_ignores_non_dict_non_event(self, bus: EventBus):
        """Passing something that is neither dict nor AgentEvent does nothing."""
        q = bus.subscribe()
        await bus.broadcast("not an event")  # type: ignore[arg-type]
        assert q.empty()

    @pytest.mark.asyncio
    async def test_broadcast_agent_event_with_none_data(self, bus: EventBus):
        q = bus.subscribe()
        await bus.broadcast(AgentEvent(event_type="heartbeat", data=None))
        item = q.get_nowait()
        assert item["event_type"] == "heartbeat"
        assert item["data"] is None


# ---------------------------------------------------------------------------
# AgentEvent serialization (to_sse)
# ---------------------------------------------------------------------------

class TestAgentEventSerialization:
    def test_to_sse_format(self):
        event = AgentEvent(event_type="done", data={"result": 42})
        sse = event.to_sse()
        assert sse.startswith("data: ")
        assert sse.endswith("\n\n")

        import json
        payload = json.loads(sse[len("data: "):-2])
        assert payload["event_type"] == "done"
        assert payload["data"]["result"] == 42

    def test_to_sse_none_data(self):
        event = AgentEvent(event_type="ping")
        sse = event.to_sse()
        import json
        payload = json.loads(sse[len("data: "):-2])
        assert payload["data"] is None
