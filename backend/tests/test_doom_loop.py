"""Tests for openmlr.agent.doom_loop — repetitive tool-call detection."""

import pytest

from openmlr.agent.doom_loop import detect_doom_loop
from openmlr.agent.types import Message, ToolCall


# Override the autouse DB fixture from conftest — these tests are pure unit tests.
@pytest.fixture(autouse=True)
def _setup_db():
    yield


def _assistant_with_tool(name: str, args: dict | None = None) -> Message:
    """Helper: create an assistant message carrying one tool call."""
    return Message(
        role="assistant",
        content="",
        tool_calls=[ToolCall(id=f"call_{name}", name=name, arguments=args or {})],
    )


# ── Edge cases / no detection ──────────────────────────────────────────────


class TestNoDetection:
    def test_returns_none_for_empty_list(self):
        assert detect_doom_loop([]) is None

    def test_returns_none_for_fewer_than_3_tool_calls(self):
        msgs = [
            _assistant_with_tool("read_file", {"path": "a.py"}),
            _assistant_with_tool("read_file", {"path": "a.py"}),
        ]
        assert detect_doom_loop(msgs) is None

    def test_returns_none_for_non_repetitive_calls(self):
        msgs = [
            _assistant_with_tool("read_file", {"path": "a.py"}),
            _assistant_with_tool("write_file", {"path": "b.py"}),
            _assistant_with_tool("exec_cmd", {"cmd": "ls"}),
            _assistant_with_tool("read_file", {"path": "c.py"}),
            _assistant_with_tool("search", {"q": "hello"}),
        ]
        assert detect_doom_loop(msgs) is None

    def test_ignores_non_assistant_messages(self):
        msgs = [
            Message(role="user", content="fix it"),
            Message(role="user", content="fix it again"),
            Message(role="user", content="please"),
        ]
        assert detect_doom_loop(msgs) is None


# ── Pattern 1: identical consecutive calls ─────────────────────────────────


class TestIdenticalConsecutive:
    def test_detects_3_identical_calls(self):
        msgs = [
            _assistant_with_tool("read_file", {"path": "a.py"}),
            _assistant_with_tool("read_file", {"path": "a.py"}),
            _assistant_with_tool("read_file", {"path": "a.py"}),
        ]
        result = detect_doom_loop(msgs)
        assert result is not None
        assert "read_file" in result

    def test_detects_5_identical_calls(self):
        msgs = [_assistant_with_tool("bash", {"cmd": "ls"})] * 5
        result = detect_doom_loop(msgs)
        assert result is not None
        assert "bash" in result

    def test_does_not_trigger_for_2_identical(self):
        msgs = [
            _assistant_with_tool("bash", {"cmd": "ls"}),
            _assistant_with_tool("bash", {"cmd": "ls"}),
            _assistant_with_tool("read_file", {"path": "x.py"}),
        ]
        assert detect_doom_loop(msgs) is None

    def test_different_args_are_not_identical(self):
        msgs = [
            _assistant_with_tool("read_file", {"path": "a.py"}),
            _assistant_with_tool("read_file", {"path": "b.py"}),
            _assistant_with_tool("read_file", {"path": "c.py"}),
        ]
        assert detect_doom_loop(msgs) is None


# ── Pattern 2: repeating sequences ─────────────────────────────────────────


class TestRepeatingSequences:
    def test_detects_AB_AB_pattern(self):
        msgs = [
            _assistant_with_tool("read_file", {"path": "a.py"}),
            _assistant_with_tool("write_file", {"path": "a.py"}),
            _assistant_with_tool("read_file", {"path": "a.py"}),
            _assistant_with_tool("write_file", {"path": "a.py"}),
        ]
        result = detect_doom_loop(msgs)
        assert result is not None
        assert "read_file" in result
        assert "write_file" in result

    def test_detects_ABC_ABC_pattern(self):
        msgs = [
            _assistant_with_tool("read", {"p": "1"}),
            _assistant_with_tool("edit", {"p": "1"}),
            _assistant_with_tool("run", {"p": "1"}),
            _assistant_with_tool("read", {"p": "1"}),
            _assistant_with_tool("edit", {"p": "1"}),
            _assistant_with_tool("run", {"p": "1"}),
        ]
        result = detect_doom_loop(msgs)
        assert result is not None
        assert "read" in result
        assert "edit" in result
        assert "run" in result

    def test_returned_string_mentions_tool_name(self):
        msgs = [
            _assistant_with_tool("grep_search", {"q": "TODO"}),
            _assistant_with_tool("grep_search", {"q": "TODO"}),
            _assistant_with_tool("grep_search", {"q": "TODO"}),
        ]
        result = detect_doom_loop(msgs)
        assert result is not None
        assert "grep_search" in result

    def test_sequence_detection_with_noise_before(self):
        """Non-repeating prefix should not prevent detection of a later loop."""
        prefix = [
            _assistant_with_tool("search", {"q": "unique_query"}),
        ]
        loop = [
            _assistant_with_tool("read_file", {"path": "x.py"}),
            _assistant_with_tool("write_file", {"path": "x.py"}),
        ] * 2  # A,B,A,B
        result = detect_doom_loop(prefix + loop)
        assert result is not None

    def test_window_limits_lookback(self):
        """Only the last `window` messages are considered."""
        old_noise = [
            _assistant_with_tool("bash", {"cmd": "ls"}),
        ] * 5
        recent_clean = [
            _assistant_with_tool("read", {"p": "a"}),
            _assistant_with_tool("write", {"p": "b"}),
            _assistant_with_tool("search", {"q": "c"}),
        ]
        # With a tight window only the 3 clean calls are visible
        assert detect_doom_loop(old_noise + recent_clean, window=3) is None
