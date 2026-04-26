"""Tests for Redis pub/sub — event publishing, answer relay, interrupt signaling."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
class TestPublishEvent:
    async def test_publishes_json_to_redis(self):
        from openmlr.agent.types import AgentEvent
        from openmlr.services.redis_pubsub import publish_event

        mock_redis = AsyncMock()
        with patch("openmlr.services.redis_pubsub.get_redis", return_value=mock_redis):
            event = AgentEvent(event_type="status", data={"status": "ready"})
            await publish_event(event)

        mock_redis.publish.assert_called_once()
        call_args = mock_redis.publish.call_args[0]
        assert call_args[0] == "openmlr:events"
        assert "status" in call_args[1]

    async def test_handles_redis_error(self):
        from openmlr.agent.types import AgentEvent
        from openmlr.services.redis_pubsub import publish_event

        mock_redis = AsyncMock()
        mock_redis.publish.side_effect = Exception("Redis down")
        with patch("openmlr.services.redis_pubsub.get_redis", return_value=mock_redis):
            event = AgentEvent(event_type="status")
            await publish_event(event)  # should not raise


@pytest.mark.asyncio
class TestPublishAnswers:
    async def test_sets_answers_key_in_redis(self):
        from openmlr.services.redis_pubsub import publish_answers

        mock_redis = AsyncMock()
        with patch("openmlr.services.redis_pubsub.get_redis", return_value=mock_redis):
            await publish_answers(conversation_id=42, answers={"q1": "Option A"})

        assert mock_redis.set.called
        key = mock_redis.set.call_args[0][0]
        assert "openmlr:answers:" in key
        assert "42" in key

    async def test_handles_redis_error(self):
        from openmlr.services.redis_pubsub import publish_answers

        mock_redis = AsyncMock()
        mock_redis.set.side_effect = Exception("Redis down")
        with patch("openmlr.services.redis_pubsub.get_redis", return_value=mock_redis):
            await publish_answers(conversation_id=1, answers={"q": "a"})  # should not raise


@pytest.mark.asyncio
class TestPublishInterrupt:
    async def test_sets_interrupt_key(self):
        from openmlr.services.redis_pubsub import publish_interrupt

        mock_redis = AsyncMock()
        with patch("openmlr.services.redis_pubsub.get_redis", return_value=mock_redis):
            await publish_interrupt(conversation_id=99)

        assert mock_redis.set.called
        key = mock_redis.set.call_args[0][0]
        assert "openmlr:interrupt:" in key
        assert "99" in key

    async def test_uses_60s_expiry(self):
        from openmlr.services.redis_pubsub import publish_interrupt

        mock_redis = AsyncMock()
        with patch("openmlr.services.redis_pubsub.get_redis", return_value=mock_redis):
            await publish_interrupt(conversation_id=1)

        call_kwargs = mock_redis.set.call_args[1]
        assert call_kwargs.get("ex") == 60


@pytest.mark.asyncio
class TestCheckInterrupt:
    async def test_returns_true_when_key_exists(self):
        from openmlr.services.redis_pubsub import check_interrupt

        mock_redis = AsyncMock()
        mock_redis.exists.return_value = 1
        with patch("openmlr.services.redis_pubsub.get_redis", return_value=mock_redis):
            result = await check_interrupt(conversation_id=5)

        assert result is True

    async def test_returns_false_when_not_found(self):
        from openmlr.services.redis_pubsub import check_interrupt

        mock_redis = AsyncMock()
        mock_redis.exists.return_value = 0
        with patch("openmlr.services.redis_pubsub.get_redis", return_value=mock_redis):
            result = await check_interrupt(conversation_id=5)

        assert result is False

    async def test_returns_false_on_redis_error(self):
        from openmlr.services.redis_pubsub import check_interrupt

        mock_redis = AsyncMock()
        mock_redis.exists.side_effect = Exception("Redis down")
        with patch("openmlr.services.redis_pubsub.get_redis", return_value=mock_redis):
            result = await check_interrupt(conversation_id=5)

        assert result is False


@pytest.mark.asyncio
class TestClearInterrupt:
    async def test_deletes_key(self):
        from openmlr.services.redis_pubsub import clear_interrupt

        mock_redis = AsyncMock()
        with patch("openmlr.services.redis_pubsub.get_redis", return_value=mock_redis):
            await clear_interrupt(conversation_id=5)

        assert mock_redis.delete.called


@pytest.mark.asyncio
class TestWaitForAnswers:
    async def test_returns_answers_when_set(self):
        from openmlr.services.redis_pubsub import wait_for_answers

        mock_redis = AsyncMock()
        mock_redis.get.return_value = '{"q1": "Option A"}'
        with patch("openmlr.services.redis_pubsub.get_redis", return_value=mock_redis):
            result = await wait_for_answers(conversation_id=1, timeout=0.5)

        assert result == {"q1": "Option A"}
        mock_redis.delete.assert_called_once()

    async def test_returns_none_on_timeout(self):
        from openmlr.services.redis_pubsub import wait_for_answers

        mock_redis = AsyncMock()
        mock_redis.get.return_value = None  # never gets set
        with patch("openmlr.services.redis_pubsub.get_redis", return_value=mock_redis):
            with patch("openmlr.services.redis_pubsub.asyncio.sleep", return_value=None):
                result = await wait_for_answers(conversation_id=1, timeout=0.1)

        assert result is None

    async def test_returns_none_on_redis_error(self):
        from openmlr.services.redis_pubsub import wait_for_answers

        mock_redis = AsyncMock()
        mock_redis.get.side_effect = Exception("Redis down")
        with patch("openmlr.services.redis_pubsub.get_redis", return_value=mock_redis):
            result = await wait_for_answers(conversation_id=1, timeout=0.1)

        assert result is None


class TestModuleConstants:
    def test_channel_name(self):
        from openmlr.services.redis_pubsub import CHANNEL_NAME
        assert CHANNEL_NAME == "openmlr:events"

    def test_answers_key_prefix(self):
        from openmlr.services.redis_pubsub import ANSWERS_KEY_PREFIX
        assert ANSWERS_KEY_PREFIX == "openmlr:answers:"

    def test_interrupt_key_prefix(self):
        from openmlr.services.redis_pubsub import INTERRUPT_KEY_PREFIX
        assert INTERRUPT_KEY_PREFIX == "openmlr:interrupt:"

    def test_redis_url_from_env(self, monkeypatch):
        monkeypatch.setenv("REDIS_URL", "redis://custom:6379/1")
        from importlib import reload

        import openmlr.services.redis_pubsub
        reload(openmlr.services.redis_pubsub)
        assert openmlr.services.redis_pubsub.REDIS_URL == "redis://custom:6379/1"
        # Restore
        monkeypatch.delenv("REDIS_URL", raising=False)
        reload(openmlr.services.redis_pubsub)
