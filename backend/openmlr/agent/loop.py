"""Agentic loop — the core turn-processing engine with tool execution."""

import json
import asyncio
import traceback
from typing import Optional

from .types import AgentEvent, Message, ToolCall, ToolSpec, Submission, OpType, LLMResult
from .session import Session
from .context import ContextManager
from .llm import LLMProvider
from .doom_loop import detect_doom_loop
from ..config import AgentConfig


async def submission_loop(session: Session, tool_router) -> None:
    """Top-level loop: process submissions from the queue indefinitely."""
    await session.emit(AgentEvent(event_type="ready", data={"status": "ready"}))

    while True:
        submission: Submission = await session.submission_queue.get()

        if submission.op == OpType.USER_INPUT:
            await _run_agent(session, tool_router, submission.data)
        elif submission.op == OpType.EXEC_APPROVAL:
            await _handle_approval(session, tool_router, submission.data)
        elif submission.op == OpType.COMPACT:
            await _compact(session)
        elif submission.op == OpType.UNDO:
            await _undo(session)
        elif submission.op == OpType.INTERRUPT:
            session.cancel()
        elif submission.op == OpType.SHUTDOWN:
            await session.emit(AgentEvent(event_type="shutdown"))
            break


async def run_agent_turn(session: Session, tool_router, user_message: str, mode: str = None) -> None:
    """Direct entry point: run one agent turn."""
    await _run_agent(session, tool_router, user_message, mode)


async def _run_agent(session: Session, tool_router, user_message: str, mode: str = None) -> None:
    """Execute the agentic loop for a user message."""
    session.clear_cancel()

    if session.pending_approval:
        session.pending_approval = None

    # Set the mode on the tool router for strict enforcement
    effective_mode = mode if mode in ("plan", "execute") else "execute"
    tool_router.set_mode(effective_mode)

    # Inject per-message mode hint (short reinforcement of system prompt rules)
    mode_hint = (
        f"[Mode: {effective_mode.upper()}] "
        + ("Plan only — ask questions, gather context, create plan. No execution."
           if effective_mode == "plan" else
           "Execute the plan — do the work, no questions. All tools except ask_user.")
    )
    session.context_manager.add_message(Message(role="system", content=mode_hint))

    session.context_manager.add_message(Message(role="user", content=user_message))

    await session.emit(AgentEvent(event_type="processing", data={"status": "thinking..."}))

    try:
        for iteration in range(session.config.max_iterations):
            if session.is_cancelled():
                await session.emit(AgentEvent(event_type="interrupted"))
                break

            # Auto-compaction check
            if session.context_manager.needs_compaction():
                await session.emit(AgentEvent(
                    event_type="tool_log",
                    data={"message": "Context nearing limit, compacting..."},
                ))
                summary = await session.context_manager.compact(
                    lambda msgs, cfg: _compact_llm_call(msgs, cfg)
                )
                if summary:
                    await session.emit(AgentEvent(
                        event_type="compacted",
                        data={"summary": summary[:500]},
                    ))

            # Doom loop detection
            doom_msg = detect_doom_loop(session.context_manager.messages)
            if doom_msg:
                session.context_manager.add_message(
                    Message(role="system", content=doom_msg)
                )

            # Emit context usage for frontend gauge
            await session.emit(AgentEvent(
                event_type="context_usage",
                data=session.context_manager.get_token_usage(),
            ))

            # Get tool specs for LLM
            tool_specs = tool_router.get_tool_specs_for_llm()

            # Get messages for LLM
            messages = session.context_manager.get_messages()

            # LLM call
            if session.config.stream:
                result = await _stream_llm_call(session, messages, tool_specs)
            else:
                result = await _non_stream_llm_call(session, messages, tool_specs)

            if result is None:
                break

            # Update token count
            if result.usage:
                session.context_manager.running_token_count = result.usage.get(
                    "total_tokens", result.usage.get("input_tokens", 0) + result.usage.get("output_tokens", 0)
                )

            # Handle finish_reason == "length" with truncated tool calls
            if result.finish_reason == "length" and result.tool_calls:
                # Drop truncated tool calls and hint
                session.context_manager.add_message(
                    Message(role="system", content=(
                        "[System: Your response was truncated due to length. "
                        "Please be more concise and focus on essential tool calls only.]"
                    ))
                )
                continue

            # No tool calls = done
            if not result.tool_calls:
                if result.content:
                    session.context_manager.add_message(
                        Message(role="assistant", content=result.content)
                    )
                    await session.emit(AgentEvent(
                        event_type="assistant_message",
                        data={"content": result.content},
                    ))
                break

            # Add assistant message with tool calls to context
            session.context_manager.add_message(Message(
                role="assistant",
                content=result.content,
                tool_calls=result.tool_calls,
            ))

            # Check for approval-required tools
            needs_approval = []
            auto_approve = []
            for tc in result.tool_calls:
                tool = tool_router.get_tool(tc.name)
                if tool and tool.needs_approval and not session.config.yolo_mode:
                    if tool.needs_approval(tc.arguments):
                        needs_approval.append(tc)
                        continue
                auto_approve.append(tc)

            # Execute auto-approved tools in parallel
            if auto_approve:
                results = await asyncio.gather(
                    *[_execute_tool(session, tool_router, tc) for tc in auto_approve],
                    return_exceptions=True,
                )

                for tc, res in zip(auto_approve, results):
                    if isinstance(res, Exception):
                        output = f"Error: {str(res)}"
                        success = False
                    else:
                        output, success = res

                    # Add tool result to context
                    session.context_manager.add_message(Message(
                        role="tool",
                        content=output,
                        tool_call_id=tc.id,
                        name=tc.name,
                    ))

                    await session.emit(AgentEvent(
                        event_type="tool_output",
                        data={
                            "tool": tc.name,
                            "tool_call_id": tc.id,
                            "output": output[:10000],
                            "success": success,
                        },
                    ))

            # Handle approval-required tools
            if needs_approval:
                session.pending_approval = {
                    "tool_calls": needs_approval,
                    "tool_router": tool_router,
                }
                await session.emit(AgentEvent(
                    event_type="approval_required",
                    data={
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "name": tc.name,
                                "arguments": tc.arguments,
                            }
                            for tc in needs_approval
                        ],
                    },
                ))
                break  # Wait for approval submission

    except Exception as e:
        await session.emit(AgentEvent(
            event_type="error",
            data={"error": str(e), "traceback": traceback.format_exc()},
        ))
    finally:
        session.turn_count += 1
        # Emit final context usage
        await session.emit(AgentEvent(
            event_type="context_usage",
            data=session.context_manager.get_token_usage(),
        ))
        await session.emit(AgentEvent(event_type="turn_complete", data={"turns": session.turn_count}))
        await session.emit(AgentEvent(event_type="status", data={"status": "ready"}))


async def _stream_llm_call(
    session: Session,
    messages: list[dict],
    tools: list[dict],
) -> Optional[LLMResult]:
    """Execute a streaming LLM call, emitting chunks to SSE."""
    content_buffer = ""
    tool_calls: list[ToolCall] = []
    usage_data = None

    async for chunk in LLMProvider.generate_stream(messages, session.config, tools):
        if session.is_cancelled():
            return None

        if isinstance(chunk, str):
            content_buffer += chunk
            await session.emit(AgentEvent(
                event_type="assistant_chunk",
                data={"chunk": chunk},
            ))
        elif isinstance(chunk, ToolCall):
            tool_calls.append(chunk)
            await session.emit(AgentEvent(
                event_type="tool_call",
                data={
                    "id": chunk.id,
                    "tool": chunk.name,
                    "arguments": json.dumps(chunk.arguments) if isinstance(chunk.arguments, dict) else str(chunk.arguments),
                },
            ))
        elif isinstance(chunk, dict):
            if chunk.get("event") == "usage":
                usage_data = chunk.get("usage")

    if content_buffer or tool_calls:
        await session.emit(AgentEvent(event_type="assistant_stream_end"))

    return LLMResult(
        content=content_buffer,
        tool_calls=tool_calls,
        finish_reason="tool_calls" if tool_calls else "stop",
        usage=usage_data,
    )


async def _non_stream_llm_call(
    session: Session,
    messages: list[dict],
    tools: list[dict],
) -> Optional[LLMResult]:
    """Execute a non-streaming LLM call."""
    result = await LLMProvider.generate(messages, session.config, tools)

    if result.content:
        await session.emit(AgentEvent(
            event_type="assistant_chunk",
            data={"chunk": result.content},
        ))
        await session.emit(AgentEvent(event_type="assistant_stream_end"))

    for tc in result.tool_calls:
        await session.emit(AgentEvent(
            event_type="tool_call",
            data={
                "id": tc.id,
                "tool": tc.name,
                "arguments": json.dumps(tc.arguments),
            },
        ))

    return result


async def _execute_tool(
    session: Session,
    tool_router,
    tool_call: ToolCall,
) -> tuple[str, bool]:
    """Execute a single tool call."""
    await session.emit(AgentEvent(
        event_type="tool_state_change",
        data={"tool_call_id": tool_call.id, "state": "running"},
    ))

    try:
        output, success = await tool_router.call_tool(
            tool_call.name, tool_call.arguments, session=session
        )
        return output, success
    except Exception as e:
        return f"Tool execution error: {str(e)}", False
    finally:
        await session.emit(AgentEvent(
            event_type="tool_state_change",
            data={"tool_call_id": tool_call.id, "state": "done"},
        ))


async def _handle_approval(
    session: Session,
    tool_router,
    approvals: dict[str, bool],
) -> None:
    """Handle user approval/rejection of tool calls."""
    if not session.pending_approval:
        return

    pending_tcs = session.pending_approval.get("tool_calls", [])
    session.pending_approval = None

    for tc in pending_tcs:
        approved = approvals.get(tc.id, False)
        if approved:
            output, success = await _execute_tool(session, tool_router, tc)
        else:
            output = "Tool execution rejected by user."
            success = False

        session.context_manager.add_message(Message(
            role="tool",
            content=output,
            tool_call_id=tc.id,
            name=tc.name,
        ))
        await session.emit(AgentEvent(
            event_type="tool_output",
            data={
                "tool": tc.name,
                "tool_call_id": tc.id,
                "output": output[:10000],
                "success": success,
            },
        ))

    # Continue the agent loop after approval
    await _run_agent(session, tool_router, "")


async def _compact(session: Session) -> None:
    """Compact the context."""
    summary = await session.context_manager.compact(
        lambda msgs, cfg: _compact_llm_call(msgs, cfg)
    )
    if summary:
        await session.emit(AgentEvent(
            event_type="compacted",
            data={"summary": summary[:500]},
        ))
    else:
        await session.emit(AgentEvent(
            event_type="compacted",
            data={"summary": "Nothing to compact."},
        ))


async def _undo(session: Session) -> None:
    """Undo the last turn."""
    removed = session.context_manager.undo_last_turn()
    await session.emit(AgentEvent(
        event_type="undo_complete",
        data={"removed_messages": removed},
    ))


async def _compact_llm_call(messages: list[dict], config: AgentConfig) -> str:
    """Helper: make an LLM call for context compaction."""
    result = await LLMProvider.generate(messages, config)
    return result.content
