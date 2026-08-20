"""Tests for openmlr.services.event_bus.EventBus, replay buffer, and scoped subscription."""

import asyncio

import pytest

from openmlr.agent.types import AgentEvent
from openmlr.services.event_bus import BufferedEvent, EventBus, sse_generator

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def bus() -> EventBus:
    return EventBus(buffer_size=10)


# ---------------------------------------------------------------------------
# subscribe & unsubscribe
# ---------------------------------------------------------------------------


class TestSubscribe:
    def test_subscribe_returns_queue(self, bus: EventBus):
        queue = bus.subscribe()
        assert isinstance(queue, asyncio.Queue)

    def test_subscribe_adds_to_subscribers(self, bus: EventBus):
        assert bus.subscriber_count == 0
        _ = bus.subscribe()
        assert bus.subscriber_count == 1
        _ = bus.subscribe()
        assert bus.subscriber_count == 2

    def test_subscribe_queue_has_maxsize(self, bus: EventBus):
        queue = bus.subscribe()
        assert queue.maxsize == 1000


class TestUnsubscribe:
    def test_unsubscribe_removes_queue(self, bus: EventBus):
        q = bus.subscribe()
        assert bus.subscriber_count == 1
        bus.unsubscribe(q)
        assert bus.subscriber_count == 0

    def test_unsubscribe_unknown_queue_is_noop(self, bus: EventBus):
        unknown = asyncio.Queue()
        bus.unsubscribe(unknown)
        assert bus.subscriber_count == 0

    def test_unsubscribe_only_removes_target(self, bus: EventBus):
        q1 = bus.subscribe()
        _ = bus.subscribe()
        bus.unsubscribe(q1)
        assert bus.subscriber_count == 1


# ---------------------------------------------------------------------------
# broadcast & sequence tracking
# ---------------------------------------------------------------------------


class TestBroadcast:
    @pytest.mark.asyncio
    async def test_broadcast_dict_event(self, bus: EventBus):
        q = bus.subscribe()
        event = {"event_type": "test", "data": {"msg": "hello"}}
        buffered = await bus.broadcast(event)
        assert isinstance(buffered, BufferedEvent)
        assert buffered.seq == 1
        item = q.get_nowait()
        assert item["event_type"] == "test"
        assert item["data"] == {"msg": "hello"}
        assert item["seq"] == 1
        assert "timestamp" in item

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
        # Create a queue with maxsize=1 to force QueueFull quickly
        from openmlr.services.event_bus import Subscription

        tiny_q = asyncio.Queue(maxsize=1)
        bus._subscriptions.append(Subscription(queue=tiny_q))
        bus._subscribers.append(tiny_q)
        healthy_q = bus.subscribe()

        assert bus.subscriber_count == 2

        # Fill the tiny queue
        tiny_q.put_nowait({"event_type": "fill", "data": None})

        # Now broadcast — tiny_q is full, should be removed
        await bus.broadcast({"event_type": "boom", "data": None})

        assert bus.subscriber_count == 1
        assert bus.subscriber_count == 1
        assert healthy_q.get_nowait()["event_type"] == "boom"

    @pytest.mark.asyncio
    async def test_broadcast_ignores_non_dict_non_event(self, bus: EventBus):
        q = bus.subscribe()
        res = await bus.broadcast("not an event")  # type: ignore[arg-type]
        assert res is None
        assert q.empty()


# ---------------------------------------------------------------------------
# Replay Buffer, Scoping, and Metrics
# ---------------------------------------------------------------------------


class TestReplayAndScoping:
    @pytest.mark.asyncio
    async def test_replay_on_subscribe(self, bus: EventBus):
        # Broadcast 3 events before subscriber connects
        await bus.broadcast({"event_type": "step1", "data": {"step": 1}})
        await bus.broadcast({"event_type": "step2", "data": {"step": 2}})
        await bus.broadcast({"event_type": "step3", "data": {"step": 3}})

        # Client reconnects with last_event_id=1, should receive step2 and step3
        reconnect_q = bus.subscribe(last_event_id=1)
        assert reconnect_q.qsize() == 2

        ev2 = reconnect_q.get_nowait()
        assert ev2["seq"] == 2
        assert ev2["event_type"] == "step2"

        ev3 = reconnect_q.get_nowait()
        assert ev3["seq"] == 3
        assert ev3["event_type"] == "step3"

    @pytest.mark.asyncio
    async def test_conversation_scoped_filtering(self, bus: EventBus):
        conv_q = bus.subscribe(conv_id="conv-123")
        other_q = bus.subscribe(conv_id="conv-456")
        global_q = bus.subscribe()

        # Broadcast event for conv-123
        await bus.broadcast({"event_type": "msg", "data": {"conv_id": "conv-123", "text": "Hi"}})

        # conv_q and global_q should receive it, other_q should not
        assert conv_q.qsize() == 1
        assert global_q.qsize() == 1
        assert other_q.qsize() == 0

    @pytest.mark.asyncio
    async def test_event_type_filtering(self, bus: EventBus):
        metric_q = bus.subscribe(event_types=["metric", "checkpoint"])
        await bus.broadcast({"event_type": "thought", "data": {"text": "Thinking..."}})
        await bus.broadcast({"event_type": "metric", "data": {"loss": 0.25}})

        assert metric_q.qsize() == 1
        ev = metric_q.get_nowait()
        assert ev["event_type"] == "metric"

    @pytest.mark.asyncio
    async def test_metrics_and_buffer_eviction(self):
        small_bus = EventBus(buffer_size=3)
        for i in range(5):
            await small_bus.broadcast({"event_type": f"ev{i}", "data": {"i": i}})

        metrics = small_bus.get_metrics()
        assert metrics["total_broadcasted"] == 5
        assert metrics["buffer_size"] == 3
        assert metrics["oldest_seq"] == 3
        assert metrics["newest_seq"] == 5

        replay = small_bus.get_replay_events(since_seq=3)
        assert len(replay) == 2
        assert replay[0]["seq"] == 4
        assert replay[1]["seq"] == 5


# ---------------------------------------------------------------------------
# SSE Generator
# ---------------------------------------------------------------------------


class TestSSEGenerator:
    @pytest.mark.asyncio
    async def test_sse_generator_formats_output(self):
        q: asyncio.Queue = asyncio.Queue()
        q.put_nowait({"seq": 101, "event_type": "tool_call", "data": {"tool": "search"}})

        gen = sse_generator(q, heartbeat_interval=0.1)
        chunk = await gen.asend(None)
        assert "id: 101\n" in chunk
        assert "event: tool_call\n" in chunk
        assert "data: " in chunk

        # Next timeout should yield ping
        ping = await gen.asend(None)
        assert ping == ":ping\n\n"
        await gen.aclose()
