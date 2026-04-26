"""Tests for openmlr.agent.context — ContextManager and helpers."""

import pytest
from openmlr.agent.context import ContextManager, estimate_tokens
from openmlr.agent.types import Message, ToolCall
from openmlr.config import AgentConfig


# Override the autouse DB fixture from conftest — these tests are pure unit tests.
@pytest.fixture(autouse=True)
def _setup_db():
    yield


def _make_config(**overrides) -> AgentConfig:
    """Build an AgentConfig with sensible test defaults."""
    defaults = {
        "model_name": "gpt-4o",          # 128 000 max tokens
        "compact_threshold_ratio": 0.90,
        "untouched_messages": 5,
    }
    defaults.update(overrides)
    return AgentConfig(**defaults)


# ── estimate_tokens ────────────────────────────────────────────────────────

class TestEstimateTokens:
    def test_returns_roughly_len_over_4(self):
        text = "a" * 100
        assert estimate_tokens(text) == 25

    def test_short_string(self):
        assert estimate_tokens("hi") == 1  # max(1, 2//4) = max(1, 0) = 1

    def test_empty_string(self):
        assert estimate_tokens("") == 1  # max(1, 0) = 1

    def test_longer_text(self):
        text = "x" * 4000
        assert estimate_tokens(text) == 1000


# ── ContextManager.add_message ─────────────────────────────────────────────

class TestAddMessage:
    def test_adds_message_object(self):
        cm = ContextManager(config=_make_config())
        msg = Message(role="user", content="hello world")
        cm.add_message(msg)
        assert len(cm.messages) == 1
        assert cm.messages[0].role == "user"
        assert cm.messages[0].content == "hello world"

    def test_adds_dict_message(self):
        cm = ContextManager(config=_make_config())
        cm.add_message({"role": "assistant", "content": "sure thing"})
        assert len(cm.messages) == 1
        assert cm.messages[0].role == "assistant"

    def test_tracks_token_count(self):
        cm = ContextManager(config=_make_config())
        cm.add_message(Message(role="user", content="a" * 100))
        assert cm.running_token_count == 25  # 100 / 4
        cm.add_message(Message(role="assistant", content="b" * 200))
        assert cm.running_token_count == 75  # 25 + 50

    def test_dict_with_tool_calls(self):
        cm = ContextManager(config=_make_config())
        cm.add_message({
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"id": "tc1", "name": "bash", "arguments": {"cmd": "ls"}},
            ],
        })
        assert len(cm.messages) == 1
        assert cm.messages[0].tool_calls is not None
        assert cm.messages[0].tool_calls[0].name == "bash"


# ── ContextManager.get_messages ────────────────────────────────────────────

class TestGetMessages:
    def test_returns_messages_in_order(self):
        cm = ContextManager(config=_make_config())
        cm.add_message(Message(role="user", content="first"))
        cm.add_message(Message(role="assistant", content="second"))
        result = cm.get_messages(include_system=False)
        assert len(result) == 2
        assert result[0]["content"] == "first"
        assert result[1]["content"] == "second"

    def test_includes_system_prompt_when_set(self):
        cm = ContextManager(config=_make_config(), system_prompt="Be helpful.")
        cm.add_message(Message(role="user", content="hi"))
        result = cm.get_messages(include_system=True)
        assert result[0]["role"] == "system"
        assert result[0]["content"] == "Be helpful."
        assert len(result) == 2  # system + user

    def test_no_system_prompt_when_empty(self):
        cm = ContextManager(config=_make_config(), system_prompt="")
        cm.add_message(Message(role="user", content="hi"))
        result = cm.get_messages(include_system=True)
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_excludes_system_prompt_when_flag_false(self):
        cm = ContextManager(config=_make_config(), system_prompt="System msg")
        cm.add_message(Message(role="user", content="hi"))
        result = cm.get_messages(include_system=False)
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_serialises_tool_calls(self):
        cm = ContextManager(config=_make_config())
        tc = ToolCall(id="tc1", name="read", arguments={"path": "a.py"})
        cm.add_message(Message(role="assistant", content="", tool_calls=[tc]))
        result = cm.get_messages(include_system=False)
        entry = result[0]
        assert "tool_calls" in entry
        assert entry["tool_calls"][0]["function"]["name"] == "read"

    def test_serialises_tool_call_id(self):
        cm = ContextManager(config=_make_config())
        cm.add_message(Message(
            role="tool", content="file contents", tool_call_id="tc1", name="read"
        ))
        result = cm.get_messages(include_system=False)
        assert result[0]["tool_call_id"] == "tc1"
        assert result[0]["name"] == "read"


# ── ContextManager.needs_compaction ────────────────────────────────────────

class TestNeedsCompaction:
    def test_returns_false_when_under_threshold(self):
        cm = ContextManager(config=_make_config())
        cm.add_message(Message(role="user", content="short"))
        assert cm.needs_compaction() is False

    def test_returns_true_when_over_threshold(self):
        cfg = _make_config(
            model_name="gpt-4o",          # 128 000 max tokens
            compact_threshold_ratio=0.90,  # threshold = 115 200
        )
        cm = ContextManager(config=cfg)
        # Inject a large token count to exceed threshold
        cm.running_token_count = 120_000
        assert cm.needs_compaction() is True

    def test_boundary_just_under(self):
        # gpt-4o = 128000, threshold at 0.90 = 115200
        cfg = _make_config(model_name="gpt-4o", compact_threshold_ratio=0.90)
        cm = ContextManager(config=cfg)
        cm.running_token_count = 115_200
        assert cm.needs_compaction() is False

    def test_boundary_just_over(self):
        cfg = _make_config(model_name="gpt-4o", compact_threshold_ratio=0.90)
        cm = ContextManager(config=cfg)
        cm.running_token_count = 115_201
        assert cm.needs_compaction() is True


# ── ContextManager.undo_last_turn ──────────────────────────────────────────

class TestUndoLastTurn:
    def test_removes_assistant_and_user_messages(self):
        cm = ContextManager(config=_make_config())
        cm.add_message(Message(role="user", content="first question"))
        cm.add_message(Message(role="assistant", content="first answer"))
        cm.add_message(Message(role="user", content="second question"))
        cm.add_message(Message(role="assistant", content="second answer"))

        removed = cm.undo_last_turn()
        # Should remove "second answer" (assistant) then "second question" (user)
        assert removed == 2
        assert len(cm.messages) == 2
        assert cm.messages[-1].content == "first answer"

    def test_removes_tool_messages_in_turn(self):
        cm = ContextManager(config=_make_config())
        cm.add_message(Message(role="user", content="do something"))
        cm.add_message(Message(role="assistant", content="calling tool"))
        cm.add_message(Message(role="tool", content="tool result", tool_call_id="tc1"))
        cm.add_message(Message(role="assistant", content="done"))

        removed = cm.undo_last_turn()
        # removes: "done" (assistant), "tool result" (tool), "calling tool" (assistant), "do something" (user)
        assert removed == 4
        assert len(cm.messages) == 0

    def test_token_count_decreases(self):
        cm = ContextManager(config=_make_config())
        cm.add_message(Message(role="user", content="a" * 100))
        cm.add_message(Message(role="assistant", content="b" * 200))
        initial_tokens = cm.running_token_count
        cm.undo_last_turn()
        assert cm.running_token_count < initial_tokens

    def test_token_count_never_negative(self):
        cm = ContextManager(config=_make_config())
        cm.add_message(Message(role="user", content="hi"))
        cm.undo_last_turn()
        assert cm.running_token_count >= 0

    def test_noop_on_empty(self):
        cm = ContextManager(config=_make_config())
        removed = cm.undo_last_turn()
        assert removed == 0
        assert cm.running_token_count == 0


# ── ContextManager.clear ───────────────────────────────────────────────────

class TestClear:
    def test_empties_messages(self):
        cm = ContextManager(config=_make_config())
        cm.add_message(Message(role="user", content="hello"))
        cm.add_message(Message(role="assistant", content="world"))
        cm.clear()
        assert len(cm.messages) == 0

    def test_resets_token_count(self):
        cm = ContextManager(config=_make_config())
        cm.add_message(Message(role="user", content="a" * 1000))
        assert cm.running_token_count > 0
        cm.clear()
        assert cm.running_token_count == 0

    def test_system_prompt_preserved(self):
        cm = ContextManager(config=_make_config(), system_prompt="Remember me")
        cm.add_message(Message(role="user", content="hi"))
        cm.clear()
        assert cm.system_prompt == "Remember me"
        assert len(cm.messages) == 0
