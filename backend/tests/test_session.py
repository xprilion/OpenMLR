"""Tests for openmlr.agent.session.Session."""

import asyncio

import pytest

from openmlr.agent.context import ContextManager
from openmlr.agent.session import Session
from openmlr.agent.types import AgentEvent
from openmlr.config import AgentConfig

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def config() -> AgentConfig:
    return AgentConfig(model_name="test-model")


@pytest.fixture
def session(config: AgentConfig) -> Session:
    return Session(config=config)


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

class TestInit:
    def test_session_creates_context_manager(self, session: Session):
        assert isinstance(session.context_manager, ContextManager)

    def test_context_manager_shares_config(self, session: Session, config: AgentConfig):
        assert session.context_manager.config is config

    def test_event_queue_created(self, session: Session):
        assert isinstance(session.event_queue, asyncio.Queue)

    def test_submission_queue_created(self, session: Session):
        assert isinstance(session.submission_queue, asyncio.Queue)

    def test_defaults(self, session: Session):
        assert session.conversation_id is None
        assert session.pending_approval is None
        assert session.pending_answers is None
        assert session.sandbox is None
        assert session.turn_count == 0


# ---------------------------------------------------------------------------
# emit
# ---------------------------------------------------------------------------

class TestEmit:
    @pytest.mark.asyncio
    async def test_emit_puts_event_in_queue(self, session: Session):
        event = AgentEvent(event_type="test", data={"x": 1})
        await session.emit(event)
        item = session.event_queue.get_nowait()
        assert item is event

    @pytest.mark.asyncio
    async def test_emit_calls_sync_listener(self, session: Session):
        received = []
        session.on_event(lambda e: received.append(e))

        event = AgentEvent(event_type="hello")
        await session.emit(event)
        assert len(received) == 1
        assert received[0] is event

    @pytest.mark.asyncio
    async def test_emit_calls_async_listener(self, session: Session):
        received = []

        async def listener(e: AgentEvent):
            received.append(e)

        session.on_event(listener)

        event = AgentEvent(event_type="async_test")
        await session.emit(event)
        assert len(received) == 1
        assert received[0] is event

    @pytest.mark.asyncio
    async def test_emit_calls_multiple_listeners(self, session: Session):
        calls_a = []
        calls_b = []

        session.on_event(lambda e: calls_a.append(e))
        session.on_event(lambda e: calls_b.append(e))

        await session.emit(AgentEvent(event_type="multi"))
        assert len(calls_a) == 1
        assert len(calls_b) == 1

    @pytest.mark.asyncio
    async def test_emit_swallows_listener_exception(self, session: Session):
        """A failing listener must not prevent the event from being queued."""

        def bad_listener(e):
            raise RuntimeError("boom")

        received = []
        session.on_event(bad_listener)
        session.on_event(lambda e: received.append(e))

        event = AgentEvent(event_type="resilient")
        await session.emit(event)

        # Event should still be in the queue
        assert session.event_queue.get_nowait() is event
        # Second listener should still have been called
        assert len(received) == 1


# ---------------------------------------------------------------------------
# cancel / is_cancelled / clear_cancel
# ---------------------------------------------------------------------------

class TestCancellation:
    def test_not_cancelled_initially(self, session: Session):
        assert session.is_cancelled() is False

    def test_cancel_sets_flag(self, session: Session):
        session.cancel()
        assert session.is_cancelled() is True

    def test_clear_cancel_resets_flag(self, session: Session):
        session.cancel()
        assert session.is_cancelled() is True
        session.clear_cancel()
        assert session.is_cancelled() is False

    def test_cancel_clear_cancel_cycle(self, session: Session):
        """Can cancel and clear multiple times."""
        for _ in range(3):
            session.cancel()
            assert session.is_cancelled() is True
            session.clear_cancel()
            assert session.is_cancelled() is False


# ---------------------------------------------------------------------------
# on_event
# ---------------------------------------------------------------------------

class TestOnEvent:
    def test_registers_listener(self, session: Session):
        assert len(session._listeners) == 0
        session.on_event(lambda e: None)
        assert len(session._listeners) == 1

    def test_registers_multiple_listeners(self, session: Session):
        session.on_event(lambda e: None)
        session.on_event(lambda e: None)
        session.on_event(lambda e: None)
        assert len(session._listeners) == 3


# ---------------------------------------------------------------------------
# update_model
# ---------------------------------------------------------------------------

class TestUpdateModel:
    def test_update_model_changes_config(self, session: Session):
        assert session.config.model_name == "test-model"
        session.update_model("anthropic/claude-sonnet-4")
        assert session.config.model_name == "anthropic/claude-sonnet-4"

    def test_update_model_reflected_in_context_manager(self, session: Session):
        """ContextManager shares the config object, so the change propagates."""
        session.update_model("openai/gpt-4o")
        assert session.context_manager.config.model_name == "openai/gpt-4o"
