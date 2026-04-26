"""Tests for agent loop — tool execution, approval, undo, compact, submissions."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openmlr.agent.context import ContextManager
from openmlr.agent.loop import (
    _compact,
    _compact_llm_call,
    _execute_tool,
    _handle_approval,
    _non_stream_llm_call,
    _run_agent,
    _stream_llm_call,
    _undo,
    run_agent_turn,
    submission_loop,
)
from openmlr.agent.session import Session
from openmlr.agent.types import (
    AgentEvent,
    LLMResult,
    OpType,
    Submission,
    ToolCall,
)
from openmlr.config import AgentConfig
from openmlr.tools.registry import ToolRouter

pytestmark = pytest.mark.asyncio

# ── Test fixtures ──────────────────────────────────────────

@pytest.fixture
def config():
    return AgentConfig(model_name="test/model", max_iterations=10, stream=False)

@pytest.fixture
def mock_session(config):
    session = MagicMock(spec=Session)
    session.config = config
    session.submission_queue = MagicMock()
    session.context_manager = MagicMock(spec=ContextManager)
    session.emit = AsyncMock()
    session.cancel = MagicMock()
    session.clear_cancel = MagicMock()
    session.is_cancelled = MagicMock(return_value=False)
    session.pending_approval = None
    session.pending_answers = None
    session.turn_count = 0
    session.on_event = MagicMock()
    session.update_model = MagicMock()
    return session

@pytest.fixture
def mock_router():
    router = MagicMock(spec=ToolRouter)
    router.call_tool = AsyncMock(return_value=("tool output", True))
    router.set_mode = MagicMock()
    router.get_tool_specs_for_llm = MagicMock(return_value=[])
    router.get_tool = MagicMock(return_value=None)
    router.get_mode = MagicMock(return_value="execute")
    return router


# ── Tool Execution ─────────────────────────────────────────

class TestExecuteTool:
    async def test_executes_tool_and_returns_output(self, mock_session, mock_router):
        tc = ToolCall(id="tc1", name="bash", arguments={"cmd": "ls"})
        mock_router.call_tool.return_value = ("file list output", True)

        output, success = await _execute_tool(mock_session, mock_router, tc)

        assert output == "file list output"
        assert success is True
        mock_router.call_tool.assert_called_once_with("bash", {"cmd": "ls"}, session=mock_session)
        assert mock_session.emit.called

    async def test_handles_tool_error(self, mock_session, mock_router):
        tc = ToolCall(id="tc1", name="bad_tool", arguments={})
        mock_router.call_tool.side_effect = RuntimeError("execution failed")

        output, success = await _execute_tool(mock_session, mock_router, tc)

        assert success is False
        assert "Tool execution error" in output

    async def test_emits_both_state_changes(self, mock_session, mock_router):
        tc = ToolCall(id="tc1", name="test", arguments={})

        await _execute_tool(mock_session, mock_router, tc)

        emitted_event_types = []
        for call in mock_session.emit.call_args_list:
            args = call[0]
            if args and hasattr(args[0], 'event_type'):
                emitted_event_types.append(args[0].event_type)
        assert len(emitted_event_types) >= 2
        assert "tool_state_change" in emitted_event_types


# ── Approval Handling ──────────────────────────────────────

class TestHandleApproval:
    async def test_approves_tool_calls(self, mock_session, mock_router):
        tcs = [ToolCall(id="tc1", name="bash", arguments={"cmd": "ls"})]
        mock_session.pending_approval = {"tool_calls": tcs, "tool_router": mock_router}
        mock_session.context_manager = MagicMock()
        mock_session.context_manager.add_message = MagicMock()
        mock_session.context_manager.get_messages = MagicMock(return_value=[])
        mock_session.config.stream = False

        await _handle_approval(mock_session, mock_router, {"tc1": True})

        mock_router.call_tool.assert_called_once_with("bash", {"cmd": "ls"}, session=mock_session)

    async def test_rejects_tool_calls(self, mock_session, mock_router):
        tcs = [ToolCall(id="tc1", name="dangerous", arguments={})]
        mock_session.pending_approval = {"tool_calls": tcs, "tool_router": mock_router}
        mock_session.context_manager = MagicMock()
        mock_session.context_manager.add_message = MagicMock()
        mock_session.context_manager.get_messages = MagicMock(return_value=[])
        mock_session.config.stream = False

        await _handle_approval(mock_session, mock_router, {"tc1": False})

        assert mock_router.call_tool.called == False

    async def test_no_pending_approval_returns(self, mock_session, mock_router):
        mock_session.pending_approval = None
        await _handle_approval(mock_session, mock_router, {})
        # No exception, nothing happens


# ── Undo ───────────────────────────────────────────────────

class TestUndo:
    async def test_undo_calls_context_manager(self, mock_session):
        mock_session.context_manager.undo_last_turn.return_value = 3

        await _undo(mock_session)

        mock_session.context_manager.undo_last_turn.assert_called_once()
        mock_session.emit.assert_called()


# ── Compaction ─────────────────────────────────────────────

class TestCompact:
    async def test_compact_calls_context_manager(self, mock_session):
        mock_session.context_manager.compact = AsyncMock(return_value="Summary of conversation")

        await _compact(mock_session)

        mock_session.context_manager.compact.assert_called_once()
        mock_session.emit.assert_called()


# ── Run Agent ──────────────────────────────────────────────

class TestRunAgent:
    async def test_runs_with_no_tool_calls(self, mock_session, mock_router):
        """Agent processes a message, LLM returns content with no tool calls."""
        mock_session.context_manager.get_messages.return_value = []
        mock_session.context_manager.needs_compaction.return_value = False
        mock_session.context_manager.get_token_usage.return_value = {"used": 100, "max": 200000, "ratio": 0.0}
        mock_session.config.stream = False

        with patch("openmlr.agent.loop.LLMProvider.generate") as mock_gen:
            mock_gen.return_value = LLMResult(
                content="I can help with that!",
                tool_calls=[],
                finish_reason="stop",
                usage={"total_tokens": 50},
            )

            await _run_agent(mock_session, mock_router, "help me")

        assert mock_session.context_manager.add_message.called
        assert mock_session.emit.called

    async def test_handles_error_gracefully(self, mock_session, mock_router):
        mock_session.context_manager.get_messages.side_effect = RuntimeError("Something broke")

        await _run_agent(mock_session, mock_router, "test")

        # Should not raise, emits error event
        assert mock_session.emit.called

    async def test_cancelled_stops_early(self, mock_session, mock_router):
        mock_session.is_cancelled.return_value = True
        mock_session.context_manager.get_messages.return_value = []
        mock_session.context_manager.needs_compaction.return_value = False
        mock_session.context_manager.get_token_usage.return_value = {"used": 0, "max": 200000, "ratio": 0.0}

        await _run_agent(mock_session, mock_router, "test")

        mock_session.emit.assert_any_call(AgentEvent(event_type="interrupted"))


class TestRunAgentTurn:
    async def test_delegates_to_run_agent(self, mock_session, mock_router):
        mock_session.context_manager.get_messages.return_value = []
        mock_session.context_manager.needs_compaction.return_value = False
        mock_session.context_manager.get_token_usage.return_value = {"ratio": 0.0}
        mock_session.config.stream = False

        with patch("openmlr.agent.loop.LLMProvider.generate") as mock_gen:
            mock_gen.return_value = LLMResult(
                content="Hello!", tool_calls=[], finish_reason="stop",
            )

            await run_agent_turn(mock_session, mock_router, "Hi", mode="plan")

        mock_router.set_mode.assert_called_with("plan")

    async def test_default_mode_is_execute(self, mock_session, mock_router):
        mock_session.context_manager.get_messages.return_value = []
        mock_session.context_manager.needs_compaction.return_value = False
        mock_session.context_manager.get_token_usage.return_value = {"ratio": 0.0}
        mock_session.config.stream = False

        with patch("openmlr.agent.loop.LLMProvider.generate") as mock_gen:
            mock_gen.return_value = LLMResult(
                content="Ok", tool_calls=[], finish_reason="stop",
            )
            await run_agent_turn(mock_session, mock_router, "test", mode="unknown")

        mock_router.set_mode.assert_called_with("execute")


# ── Submissions ────────────────────────────────────────────

class TestSubmissionLoop:
    async def test_processes_user_input(self, mock_session, mock_router):
        mock_session.submission_queue.get = AsyncMock(side_effect=[
            Submission(op=OpType.USER_INPUT, data="hello"),
            Submission(op=OpType.SHUTDOWN),
        ])
        mock_session.context_manager.get_messages.return_value = []
        mock_session.context_manager.needs_compaction.return_value = False
        mock_session.context_manager.get_token_usage.return_value = {"ratio": 0.0}
        mock_session.config.stream = False

        with patch("openmlr.agent.loop.LLMProvider.generate") as mock_gen:
            mock_gen.return_value = LLMResult(
                content="Hi!", tool_calls=[], finish_reason="stop",
            )
            await submission_loop(mock_session, mock_router)

        assert mock_session.emit.called

    async def test_processes_compact(self, mock_session, mock_router):
        mock_session.submission_queue.get = AsyncMock(side_effect=[
            Submission(op=OpType.COMPACT),
            Submission(op=OpType.SHUTDOWN),
        ])
        mock_session.context_manager.compact = AsyncMock(return_value="Summary")

        await submission_loop(mock_session, mock_router)

        mock_session.context_manager.compact.assert_called_once()

    async def test_processes_undo(self, mock_session, mock_router):
        mock_session.submission_queue.get = AsyncMock(side_effect=[
            Submission(op=OpType.UNDO),
            Submission(op=OpType.SHUTDOWN),
        ])
        mock_session.context_manager.undo_last_turn.return_value = 3

        await submission_loop(mock_session, mock_router)

        mock_session.context_manager.undo_last_turn.assert_called_once()

    async def test_processes_interrupt(self, mock_session, mock_router):
        mock_session.submission_queue.get = AsyncMock(side_effect=[
            Submission(op=OpType.INTERRUPT),
            Submission(op=OpType.SHUTDOWN),
        ])

        await submission_loop(mock_session, mock_router)

        mock_session.cancel.assert_called_once()

    async def test_shutdown_exits(self, mock_session, mock_router):
        mock_session.submission_queue.get = AsyncMock(return_value=Submission(op=OpType.SHUTDOWN))

        await submission_loop(mock_session, mock_router)

        mock_session.emit.assert_any_call(AgentEvent(event_type="shutdown"))


# ── LLM Call Helpers ───────────────────────────────────────

class TestNonStreamLLMCall:
    async def test_returns_llm_result(self, mock_session):
        mock_session.is_cancelled.return_value = False
        messages = [{"role": "user", "content": "help"}]
        tools = []

        with patch("openmlr.agent.loop.LLMProvider.generate") as mock_gen:
            mock_gen.return_value = LLMResult(
                content="Response", tool_calls=[], finish_reason="stop",
            )
            result = await _non_stream_llm_call(mock_session, messages, tools)

        assert result is not None
        assert result.content == "Response"

    async def test_emits_chunk_and_end(self, mock_session):
        mock_session.is_cancelled.return_value = False

        with patch("openmlr.agent.loop.LLMProvider.generate") as mock_gen:
            mock_gen.return_value = LLMResult(
                content="Output", tool_calls=[], finish_reason="stop",
            )
            await _non_stream_llm_call(mock_session, [], [])

        assert mock_session.emit.called


class TestStreamLLMCall:
    async def test_returns_llm_result_from_chunks(self, mock_session):
        mock_session.is_cancelled.return_value = False
        mock_session.config = AgentConfig(model_name="test", stream=True)

        async def mock_stream(messages, config, tools):
            yield "Hello"
            yield " world"

        with patch("openmlr.agent.loop.LLMProvider.generate_stream") as mock_str:
            mock_str.return_value = mock_stream(None, None, None)
            result = await _stream_llm_call(mock_session, [], [])

        assert result is not None
        assert result.content == "Hello world"
        assert result.finish_reason == "stop"

    async def test_cancelled_returns_none(self, mock_session):
        mock_session.is_cancelled.return_value = True

        async def mock_stream(messages, config, tools):
            yield "Hello"
            if False:
                yield

        with patch("openmlr.agent.loop.LLMProvider.generate_stream") as mock_str:
            mock_str.return_value = mock_stream(None, None, None)
            result = await _stream_llm_call(mock_session, [], [])

        assert result is None

    async def test_handles_stream_with_tool_calls(self, mock_session):
        mock_session.is_cancelled.return_value = False
        mock_session.config = AgentConfig(model_name="test", stream=True)
        tc = ToolCall(id="call_1", name="search", arguments={"query": "test"})

        async def mock_stream(messages, config, tools):
            yield "Finding..."
            yield tc

        with patch("openmlr.agent.loop.LLMProvider.generate_stream") as mock_str:
            mock_str.return_value = mock_stream(None, None, None)
            result = await _stream_llm_call(mock_session, [], [])

        assert result is not None
        assert result.content == "Finding..."
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "search"
        assert result.finish_reason == "tool_calls"


# ── Compact LLM Call ───────────────────────────────────────

class TestCompactLLMCall:
    async def test_returns_content(self):
        messages = [{"role": "user", "content": "summarize"}]
        config = AgentConfig(model_name="test/title", stream=False)

        with patch("openmlr.agent.loop.LLMProvider.generate") as mock_gen:
            mock_gen.return_value = LLMResult(
                content="A summary.", tool_calls=[], finish_reason="stop",
            )
            result = await _compact_llm_call(messages, config)

        assert result == "A summary."
