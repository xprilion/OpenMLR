"""Agent core types — AgentEvent, Message, ToolSpec, ToolCall."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any


@dataclass
class ToolCall:
    """A tool call requested by the LLM."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ToolSpec:
    """Specification for an agent tool."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema
    handler: Callable[..., Awaitable[tuple[str, bool]]] | None = None
    needs_approval: Callable[..., bool] | None = None


@dataclass
class Message:
    """A message in the conversation context."""

    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None
    name: str | None = None


@dataclass(kw_only=True)
class AgentEvent:
    """Event emitted by the agent loop for SSE streaming."""

    event_type: str
    data: dict[str, Any] | None = None

    def to_sse(self) -> str:
        import json

        return f"data: {json.dumps({'event_type': self.event_type, 'data': self.data})}\n\n"


class OpType(str, Enum):
    """Operation types submitted to the agent loop."""

    USER_INPUT = "user_input"
    EXEC_APPROVAL = "exec_approval"
    COMPACT = "compact"
    UNDO = "undo"
    INTERRUPT = "interrupt"
    SHUTDOWN = "shutdown"


@dataclass
class Submission:
    """A submission to the agent loop."""

    op: OpType
    data: Any = None


@dataclass
class LLMResult:
    """Result of an LLM call."""

    content: str
    tool_calls: list[ToolCall]
    finish_reason: str
    usage: dict | None = None
