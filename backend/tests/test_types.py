"""Tests for agent core types — AgentEvent, OpType, Message, ToolCall, ToolSpec, LLMResult, Submission."""

import json

from openmlr.agent.types import (
    AgentEvent,
    LLMResult,
    Message,
    OpType,
    Submission,
    ToolCall,
    ToolSpec,
)


class TestToolCall:
    def test_creation(self):
        tc = ToolCall(id="call_1", name="read_file", arguments={"path": "/tmp/test"})
        assert tc.id == "call_1"
        assert tc.name == "read_file"
        assert tc.arguments == {"path": "/tmp/test"}

    def test_empty_arguments(self):
        tc = ToolCall(id="c2", name="noop", arguments={})
        assert tc.arguments == {}


class TestToolSpec:
    def test_creation_without_optional(self):
        ts = ToolSpec(name="test_tool", description="A test tool", parameters={"type": "object"})
        assert ts.name == "test_tool"
        assert ts.description == "A test tool"
        assert ts.parameters == {"type": "object"}
        assert ts.handler is None
        assert ts.needs_approval is None

    def test_creation_with_handler(self):
        async def handler(arg1: str, arg2: int = 0) -> tuple[str, bool]:
            return f"done: {arg1}", True

        ts = ToolSpec(
            name="with_handler",
            description="Tool with handler",
            parameters={"type": "object", "properties": {"arg1": {"type": "string"}}},
            handler=handler,
        )
        assert ts.handler is not None
        assert ts.name == "with_handler"

    def test_needs_approval(self):
        ts = ToolSpec(
            name="dangerous",
            description="Needs approval",
            parameters={"type": "object"},
            needs_approval=lambda **kwargs: True,
        )
        assert ts.needs_approval is not None


class TestMessage:
    def test_user_message(self):
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.tool_calls is None
        assert msg.tool_call_id is None
        assert msg.name is None

    def test_assistant_with_tool_calls(self):
        tc = ToolCall(id="tc1", name="bash", arguments={"cmd": "ls"})
        msg = Message(role="assistant", content="", tool_calls=[tc])
        assert msg.role == "assistant"
        assert msg.content == ""
        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0].name == "bash"

    def test_tool_result_message(self):
        msg = Message(role="tool", content="output here", tool_call_id="tc1", name="bash")
        assert msg.role == "tool"
        assert msg.tool_call_id == "tc1"
        assert msg.name == "bash"

    def test_system_message(self):
        msg = Message(role="system", content="You are an AI assistant.")
        assert msg.role == "system"


class TestAgentEvent:
    def test_creation_without_data(self):
        evt = AgentEvent(event_type="status")
        assert evt.event_type == "status"
        assert evt.data is None

    def test_creation_with_data(self):
        evt = AgentEvent(event_type="status", data={"status": "thinking..."})
        assert evt.data == {"status": "thinking..."}

    def test_creation_kwargs(self):
        evt = AgentEvent(event_type="text_delta", data={"text": "hello"})
        assert evt.event_type == "text_delta"
        assert evt.data["text"] == "hello"

    def test_to_sse_simple(self):
        evt = AgentEvent(event_type="ping")
        sse = evt.to_sse()
        assert sse.startswith("data: ")
        assert sse.endswith("\n\n")
        parsed = json.loads(sse[6:-2])
        assert parsed["event_type"] == "ping"
        assert parsed["data"] is None

    def test_to_sse_with_data(self):
        evt = AgentEvent(event_type="status", data={"status": "ready"})
        sse = evt.to_sse()
        parsed = json.loads(sse[6:-2])
        assert parsed["event_type"] == "status"
        assert parsed["data"] == {"status": "ready"}

    def test_to_sse_complex_data(self):
        evt = AgentEvent(event_type="text_delta", data={"text": "hello\nworld", "index": 0})
        sse = evt.to_sse()
        parsed = json.loads(sse[6:-2])
        assert parsed["data"]["text"] == "hello\nworld"
        assert parsed["data"]["index"] == 0


class TestOpType:
    def test_enum_values(self):
        assert OpType.USER_INPUT == "user_input"
        assert OpType.EXEC_APPROVAL == "exec_approval"
        assert OpType.COMPACT == "compact"
        assert OpType.UNDO == "undo"
        assert OpType.INTERRUPT == "interrupt"
        assert OpType.SHUTDOWN == "shutdown"

    def test_string_equality(self):
        assert OpType.USER_INPUT == "user_input"
        assert OpType.INTERRUPT != "user_input"


class TestSubmission:
    def test_creation(self):
        sub = Submission(op=OpType.USER_INPUT, data="Send this message")
        assert sub.op == OpType.USER_INPUT
        assert sub.data == "Send this message"

    def test_no_data_default(self):
        sub = Submission(op=OpType.SHUTDOWN)
        assert sub.op == OpType.SHUTDOWN
        assert sub.data is None


class TestLLMResult:
    def test_basic_result(self):
        result = LLMResult(content="Hello, world!", tool_calls=[], finish_reason="stop")
        assert result.content == "Hello, world!"
        assert result.tool_calls == []
        assert result.finish_reason == "stop"
        assert result.usage is None

    def test_with_tool_calls(self):
        tc = ToolCall(id="c1", name="search", arguments={"query": "test"})
        result = LLMResult(content="", tool_calls=[tc], finish_reason="tool_calls")
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "search"
        assert result.finish_reason == "tool_calls"

    def test_with_usage(self):
        usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
        result = LLMResult(content="ok", tool_calls=[], finish_reason="stop", usage=usage)
        assert result.usage == usage
        assert result.usage["total_tokens"] == 150

    def test_finish_reason_length(self):
        """finish_reason can be 'length' for truncated responses."""
        result = LLMResult(content="truncated", tool_calls=[], finish_reason="length")
        assert result.finish_reason == "length"
