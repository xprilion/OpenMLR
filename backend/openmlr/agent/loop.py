"""Agentic loop — the core turn-processing engine with tool execution and research state tracking."""

from __future__ import annotations

import asyncio
import traceback
from typing import Any

from .doom_loop import detect_doom_loop
from .llm import LLMProvider  # noqa: F401
from .loop_executor import (
    compact_llm_call,
    execute_tool,
    non_stream_llm_call,
    stream_llm_call,
)
from .session import Session
from .types import AgentEvent, Message, OpType, Submission

# Backward-compatible aliases for internal helpers
_compact_llm_call = compact_llm_call
_execute_tool = execute_tool
_non_stream_llm_call = non_stream_llm_call
_stream_llm_call = stream_llm_call


def _append_hint_to_last_user_msg(messages: list[Message], hint: str) -> None:
    """Append a system hint to the last user message to preserve user/assistant alternation."""
    for msg in reversed(messages):
        if msg.role == "user":
            msg.content = (msg.content or "") + f"\n\n{hint}"
            return


async def submission_loop(session: Session, tool_router: Any) -> None:
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


async def run_agent_turn(
    session: Session, tool_router: Any, user_message: str, mode: str | None = None
) -> None:
    """Direct entry point: run one agent turn."""
    await _run_agent(session, tool_router, user_message, mode)


async def _run_agent(
    session: Session, tool_router: Any, user_message: str, mode: str | None = None
) -> None:
    """Execute the agentic loop for a user message."""
    session.clear_cancel()

    if session.pending_approval:
        session.pending_approval = None

    if mode in ("plan", "execute"):
        effective_mode = mode
        session.current_mode = mode
    else:
        effective_mode = session.current_mode
    tool_router.set_mode(effective_mode)

    mode_hint = f"[Mode: {effective_mode.upper()}] " + (
        "Plan only — ask questions, create plan. "
        "Use search/papers only for quick feasibility checks. "
        "Do NOT do comprehensive research here — add research as Execute mode tasks."
        if effective_mode == "plan"
        else "Execute the plan — do the work, no questions. All tools except ask_user."
    )

    # Append research orchestrator context if active
    if session.research_orchestrator and hasattr(
        session.research_orchestrator, "format_research_context"
    ):
        r_ctx = session.research_orchestrator.format_research_context()
        if r_ctx:
            mode_hint = f"{mode_hint}\n\n{r_ctx}"

    if user_message:
        user_content = f"{mode_hint}\n\n{user_message}"
        session.context_manager.add_message(Message(role="user", content=user_content))

    await session.emit(AgentEvent(event_type="processing", data={"status": "thinking..."}))

    try:
        for _iteration in range(session.config.max_iterations):
            if session.is_cancelled():
                await session.emit(AgentEvent(event_type="interrupted"))
                break

            # Auto-compaction check
            if session.context_manager.needs_compaction():
                _append_hint_to_last_user_msg(
                    session.context_manager.messages,
                    "[URGENT: Context compaction imminent] Save any unsaved findings, "
                    "paper references, or research decisions NOW using `memory`, "
                    "`workspace knowledge_add`, or `workspace note` before context is compressed.",
                )
                await session.emit(
                    AgentEvent(
                        event_type="tool_log",
                        data={"message": "Context nearing limit, compacting..."},
                    )
                )
                summary = await session.context_manager.compact(
                    lambda msgs, cfg: compact_llm_call(msgs, cfg)
                )
                if summary:
                    await session.emit(
                        AgentEvent(
                            event_type="compacted",
                            data={"summary": summary[:500]},
                        )
                    )

            hint_injected = False
            doom_msg = detect_doom_loop(session.context_manager.messages)
            if doom_msg:
                _append_hint_to_last_user_msg(session.context_manager.messages, doom_msg)
                hint_injected = True

            if not hint_injected and session.turns_since_nudge >= session.nudge_interval:
                session.turns_since_nudge = 0
                _append_hint_to_last_user_msg(
                    session.context_manager.messages,
                    "[Knowledge nudge] Consider saving recent findings via `memory`, "
                    "`workspace knowledge_add`, or `workspace note`.",
                )

            await session.emit(
                AgentEvent(
                    event_type="context_usage",
                    data=session.context_manager.get_token_usage(),
                )
            )

            tool_specs = tool_router.get_tool_specs_for_llm()
            messages = session.context_manager.get_messages()

            if session.config.stream:
                result = await stream_llm_call(session, messages, tool_specs)
            else:
                result = await non_stream_llm_call(session, messages, tool_specs)

            if result is None:
                break

            if result.usage:
                session.context_manager.running_token_count = result.usage.get(
                    "total_tokens",
                    result.usage.get("input_tokens", 0) + result.usage.get("output_tokens", 0),
                )

            if result.finish_reason == "length" and result.tool_calls:
                _append_hint_to_last_user_msg(
                    session.context_manager.messages,
                    "[System: Your response was truncated. Be more concise and focus on essential tool calls only.]",
                )
                continue

            if not result.tool_calls:
                if result.content:
                    session.context_manager.add_message(
                        Message(role="assistant", content=result.content)
                    )
                    await session.emit(
                        AgentEvent(
                            event_type="assistant_message",
                            data={"content": result.content},
                        )
                    )
                break

            session.context_manager.add_message(
                Message(
                    role="assistant",
                    content=result.content,
                    tool_calls=result.tool_calls,
                )
            )

            if result.content:
                await session.emit(
                    AgentEvent(
                        event_type="assistant_message",
                        data={"content": result.content},
                    )
                )

            needs_approval = []
            auto_approve = []
            for tc in result.tool_calls:
                tool = tool_router.get_tool(tc.name)
                if tool and tool.needs_approval and not session.config.yolo_mode:
                    if tool.needs_approval(tc.arguments):
                        needs_approval.append(tc)
                        continue
                auto_approve.append(tc)

            if auto_approve:
                results = await asyncio.gather(
                    *[execute_tool(session, tool_router, tc) for tc in auto_approve],
                    return_exceptions=True,
                )

                for tc, res in zip(auto_approve, results, strict=False):
                    if isinstance(res, Exception):
                        output = f"Error: {str(res)}"
                        success = False
                    else:
                        output, success = res

                    session.context_manager.add_message(
                        Message(
                            role="tool",
                            content=output,
                            tool_call_id=tc.id,
                            name=tc.name,
                        )
                    )

                    await session.emit(
                        AgentEvent(
                            event_type="tool_output",
                            data={
                                "tool": tc.name,
                                "tool_call_id": tc.id,
                                "output": output[:10000],
                                "success": success,
                            },
                        )
                    )

            if needs_approval:
                session.pending_approval = {
                    "tool_calls": needs_approval,
                    "tool_router": tool_router,
                }
                await session.emit(
                    AgentEvent(
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
                    )
                )
                break

    except Exception as e:
        await session.emit(
            AgentEvent(
                event_type="error",
                data={"error": str(e), "traceback": traceback.format_exc()},
            )
        )
    finally:
        session.turn_count += 1
        session.turns_since_nudge += 1
        await session.emit(
            AgentEvent(
                event_type="context_usage",
                data=session.context_manager.get_token_usage(),
            )
        )
        await session.emit(
            AgentEvent(event_type="turn_complete", data={"turns": session.turn_count})
        )
        await session.emit(AgentEvent(event_type="status", data={"status": "ready"}))


async def _handle_approval(
    session: Session,
    tool_router: Any,
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
            output, success = await execute_tool(session, tool_router, tc)
        else:
            output = "Tool execution rejected by user."
            success = False

        session.context_manager.add_message(
            Message(
                role="tool",
                content=output,
                tool_call_id=tc.id,
                name=tc.name,
            )
        )
        await session.emit(
            AgentEvent(
                event_type="tool_output",
                data={
                    "tool": tc.name,
                    "tool_call_id": tc.id,
                    "output": output[:10000],
                    "success": success,
                },
            )
        )

    await _run_agent(session, tool_router, "")


async def _compact(session: Session) -> None:
    """Compact the context."""
    summary = await session.context_manager.compact(lambda msgs, cfg: compact_llm_call(msgs, cfg))
    status_msg = summary[:500] if summary else "Nothing to compact."
    await session.emit(
        AgentEvent(
            event_type="compacted",
            data={"summary": status_msg},
        )
    )


async def _undo(session: Session) -> None:
    """Undo the last turn."""
    removed = session.context_manager.undo_last_turn()
    await session.emit(
        AgentEvent(
            event_type="undo_complete",
            data={"removed_messages": removed},
        )
    )
