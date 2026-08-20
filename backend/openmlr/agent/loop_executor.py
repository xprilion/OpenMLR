"""Tool execution and streaming LLM helper functions for the agent loop."""

from __future__ import annotations

import json
import time
from typing import Any

from ..config import AgentConfig
from .llm import LLMProvider
from .ml_debugger import diagnose_ml_error
from .session import Session
from .types import AgentEvent, LLMResult, ThinkingChunk, ToolCall


async def stream_llm_call(
    session: Session,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
) -> LLMResult | None:
    """Execute a streaming LLM call, emitting chunks to SSE."""
    content_buffer = ""
    tool_calls: list[ToolCall] = []
    usage_data = None
    thinking_started: float | None = None
    was_thinking = False

    async for chunk in LLMProvider.generate_stream(messages, session.config, tools):
        if session.is_cancelled():
            return None

        if isinstance(chunk, ThinkingChunk):
            if thinking_started is None:
                thinking_started = time.time()
            was_thinking = True
            await session.emit(
                AgentEvent(
                    event_type="thinking_chunk",
                    data={"chunk": chunk.text},
                )
            )
        elif isinstance(chunk, str):
            if was_thinking:
                duration = time.time() - thinking_started if thinking_started else 0
                await session.emit(
                    AgentEvent(
                        event_type="thinking_end",
                        data={"duration_seconds": round(duration, 1)},
                    )
                )
                was_thinking = False
            content_buffer += chunk
            await session.emit(
                AgentEvent(
                    event_type="assistant_chunk",
                    data={"chunk": chunk},
                )
            )
        elif isinstance(chunk, ToolCall):
            if was_thinking:
                duration = time.time() - thinking_started if thinking_started else 0
                await session.emit(
                    AgentEvent(
                        event_type="thinking_end",
                        data={"duration_seconds": round(duration, 1)},
                    )
                )
                was_thinking = False
            tool_calls.append(chunk)
            await session.emit(
                AgentEvent(
                    event_type="tool_call",
                    data={
                        "id": chunk.id,
                        "tool": chunk.name,
                        "arguments": json.dumps(chunk.arguments)
                        if isinstance(chunk.arguments, dict)
                        else str(chunk.arguments),
                    },
                )
            )
        elif isinstance(chunk, dict) and chunk.get("event") == "usage":
            usage_data = chunk.get("usage")

    if was_thinking and thinking_started:
        duration = time.time() - thinking_started
        await session.emit(
            AgentEvent(
                event_type="thinking_end",
                data={"duration_seconds": round(duration, 1)},
            )
        )

    if content_buffer or tool_calls:
        await session.emit(AgentEvent(event_type="assistant_stream_end"))

    return LLMResult(
        content=content_buffer,
        tool_calls=tool_calls,
        finish_reason="tool_calls" if tool_calls else "stop",
        usage=usage_data,
    )


async def non_stream_llm_call(
    session: Session,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
) -> LLMResult | None:
    """Execute a non-streaming LLM call."""
    result = await LLMProvider.generate(messages, session.config, tools)

    if result.content:
        await session.emit(
            AgentEvent(
                event_type="assistant_chunk",
                data={"chunk": result.content},
            )
        )
        await session.emit(AgentEvent(event_type="assistant_stream_end"))

    for tc in result.tool_calls:
        await session.emit(
            AgentEvent(
                event_type="tool_call",
                data={
                    "id": tc.id,
                    "tool": tc.name,
                    "arguments": json.dumps(tc.arguments),
                },
            )
        )

    return result


async def execute_tool(
    session: Session,
    tool_router: Any,
    tool_call: ToolCall,
) -> tuple[str, bool]:
    """Execute a single tool call and emit lifecycle events, enriching ML errors with self-healing guidance."""
    await session.emit(
        AgentEvent(
            event_type="tool_state_change",
            data={"tool_call_id": tool_call.id, "state": "running"},
        )
    )

    try:
        output, success = await tool_router.call_tool(
            tool_call.name, tool_call.arguments, session=session
        )
        if output:
            diag = diagnose_ml_error(output)
            if diag and diag.remedy_prompt:
                output = f"{output}\n\n{diag.remedy_prompt}"
        return output, success
    except Exception as e:
        err_msg = f"Tool execution error: {str(e)}"
        diag = diagnose_ml_error(err_msg)
        if diag and diag.remedy_prompt:
            err_msg = f"{err_msg}\n\n{diag.remedy_prompt}"
        return err_msg, False
    finally:
        await session.emit(
            AgentEvent(
                event_type="tool_state_change",
                data={"tool_call_id": tool_call.id, "state": "done"},
            )
        )


async def compact_llm_call(messages: list[dict[str, Any]], config: AgentConfig) -> str:
    """Helper: make an LLM call for context compaction."""
    result = await LLMProvider.generate(messages, config)
    return result.content or ""
