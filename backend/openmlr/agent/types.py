"""Agent core types — AgentEvent, Message, ToolSpec, ToolCall."""

from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable, Optional
from enum import Enum


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
    handler: Optional[Callable[..., Awaitable[tuple[str, bool]]]] = None
    needs_approval: Optional[Callable[..., bool]] = None


@dataclass
class Message:
    """A message in the conversation context."""
    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_calls: Optional[list[ToolCall]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


@dataclass(kw_only=True)
class AgentEvent:
    """Event emitted by the agent loop for SSE streaming."""
    event_type: str
    data: Optional[dict[str, Any]] = None

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
    usage: Optional[dict] = None
