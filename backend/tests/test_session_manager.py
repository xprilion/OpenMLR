"""Tests for SessionManager — multi-session lifecycle and message queuing."""

import pytest

from openmlr.services.session_manager import SessionManager

pytestmark = pytest.mark.asyncio
from openmlr.config import AgentConfig
from openmlr.services.event_bus import EventBus


@pytest.fixture
def config():
    return AgentConfig(
        model_name="test/model",
        max_iterations=10,
        stream=False,
        yolo_mode=False,
    )


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def session_manager(event_bus, config):
    return SessionManager(event_bus=event_bus, default_config=config)


class TestSessionManager:
    async def test_initial_state(self, session_manager):
        assert session_manager.current_conversation_id is None
        assert session_manager.is_processing is False
        assert session_manager.get_current_session() is None

    async def test_get_session_nonexistent(self, session_manager):
        assert session_manager.get_session(999) is None

    async def test_get_or_create_session(self, session_manager):
        active = await session_manager.get_or_create_session(
            conversation_id=1,
            uuid="test-uuid-1",
            model="test/model",
            mode="general",
            username="tester",
        )
        assert active is not None
        assert active.conversation_id == 1
        assert active.uuid == "test-uuid-1"
        assert active.session is not None
        assert active.tool_router is not None

    async def test_get_or_create_returns_existing(self, session_manager):
        s1 = await session_manager.get_or_create_session(1, "u1")
        s2 = await session_manager.get_or_create_session(1, "u1")
        assert s1 is s2

    async def test_get_session_after_create(self, session_manager):
        await session_manager.get_or_create_session(1, "u1")
        s = session_manager.get_session(1)
        assert s is not None
        assert s.conversation_id == 1

    async def test_remove_session(self, session_manager):
        await session_manager.get_or_create_session(1, "u1")
        await session_manager.remove_session(1)
        assert session_manager.get_session(1) is None

    async def test_remove_nonexistent_session(self, session_manager):
        await session_manager.remove_session(999)

    async def test_multiple_sessions(self, session_manager):
        s1 = await session_manager.get_or_create_session(1, "u1")
        s2 = await session_manager.get_or_create_session(2, "u2")
        assert s1.conversation_id == 1
        assert s2.conversation_id == 2
        assert s1 is not s2

    async def test_session_loads_existing_messages(self, session_manager):
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        active = await session_manager.get_or_create_session(
            1,
            "u1",
            existing_messages=messages,
        )
        msgs = active.session.context_manager.get_messages()
        assert len(msgs) >= 2  # includes system prompt + existing messages

    async def test_generate_title_no_session(self, session_manager):
        title = await session_manager.generate_title(999, [])
        assert title is None

    async def test_remove_session_clears_current(self, session_manager):
        await session_manager.get_or_create_session(42, "u42")
        session_manager.current_conversation_id = 42
        await session_manager.remove_session(42)
        assert session_manager.current_conversation_id is None
