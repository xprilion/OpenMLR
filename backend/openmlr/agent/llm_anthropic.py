"""Anthropic provider implementation and message format converter."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator
from typing import Any

from ..config import AgentConfig
from .types import LLMResult, ThinkingChunk, ToolCall

logger = logging.getLogger(__name__)


def merge_consecutive_user_messages(chat: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge consecutive user messages to satisfy Anthropic's strict alternation."""
    merged: list[dict[str, Any]] = []
    for msg in chat:
        if not (merged and merged[-1]["role"] == "user" and msg["role"] == "user"):
            merged.append(msg)
            continue

        prev_content = merged[-1]["content"]
        curr_content = msg["content"]

        if isinstance(prev_content, list) and isinstance(curr_content, list):
            merged[-1]["content"] = prev_content + curr_content
        elif isinstance(prev_content, str) and isinstance(curr_content, str):
            merged[-1]["content"] = prev_content + "\n\n" + curr_content
        elif isinstance(prev_content, str) and isinstance(curr_content, list):
            merged[-1]["content"] = [{"type": "text", "text": prev_content}] + curr_content
        elif isinstance(prev_content, list) and isinstance(curr_content, str):
            merged[-1]["content"] = prev_content + [{"type": "text", "text": curr_content}]
        else:
            merged.append(msg)

    return merged


def convert_assistant_msg(m: dict[str, Any]) -> dict[str, Any]:
    """Convert an assistant message to Anthropic format with tool_use blocks."""
    content_blocks = []
    if m.get("content"):
        content_blocks.append({"type": "text", "text": m["content"]})
    for tc in m.get("tool_calls", []):
        func = tc.get("function", tc)
        content_blocks.append(
            {
                "type": "tool_use",
                "id": tc.get("id", ""),
                "name": func.get("name", tc.get("name", "")),
                "input": func.get("arguments", tc.get("arguments", {})),
            }
        )
    return {"role": "assistant", "content": content_blocks or m.get("content", "")}


def append_tool_result(chat: list[dict[str, Any]], m: dict[str, Any]) -> None:
    """Append a tool result to the chat list, merging with previous user message if possible."""
    tool_block = {
        "type": "tool_result",
        "tool_use_id": m.get("tool_call_id", ""),
        "content": m["content"],
    }
    if chat and chat[-1]["role"] == "user" and isinstance(chat[-1]["content"], list):
        chat[-1]["content"].append(tool_block)
    else:
        chat.append({"role": "user", "content": [tool_block]})


def to_anthropic_messages(messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    """Split system prompt and convert messages to Anthropic format."""
    system_parts = []
    chat: list[dict[str, Any]] = []
    for m in messages:
        role = m["role"]
        if role == "system":
            system_parts.append(m["content"])
        elif role == "user":
            chat.append({"role": "user", "content": m["content"]})
        elif role == "assistant":
            chat.append(convert_assistant_msg(m))
        elif role == "tool":
            append_tool_result(chat, m)

    return "\n\n".join(system_parts), merge_consecutive_user_messages(chat)


def anthropic_client(config: AgentConfig, custom_provider: dict[str, Any] | None = None):
    """Create Anthropic client with appropriate settings."""
    from anthropic import AsyncAnthropic

    mn = config.model_name.lower()
    if custom_provider and custom_provider.get("sdk_type") == "anthropic-sdk":
        return AsyncAnthropic(
            api_key=custom_provider.get("api_key"),
            base_url=custom_provider.get("api_base", "").rstrip("/"),
        )
    if mn.startswith("opencode-go/"):
        return AsyncAnthropic(
            api_key=os.environ.get("OPENCODE_GO_API_KEY"),
            base_url="https://opencode.ai/zen/go/v1",
        )
    return AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def build_anthropic_params(
    model: str,
    chat_msgs: list[dict[str, Any]],
    system_prompt: str,
    tools: list[dict[str, Any]] | None,
    model_name: str,
    anthropic_tool_fn: Any,
) -> dict[str, Any]:
    """Build the params dict shared by call_anthropic and stream_anthropic."""
    params: dict[str, Any] = {"model": model, "messages": chat_msgs, "max_tokens": 4096}
    if system_prompt:
        params["system"] = [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]
    anthropic_tools = anthropic_tool_fn(tools)
    if anthropic_tools:
        params["tools"] = anthropic_tools

    # Thinking budget for extended thinking models (claude-3-7-sonnet)
    mn = model_name.lower()
    if "claude-3-7" in mn or "claude-3.7" in mn:
        params["thinking"] = {"type": "enabled", "budget_tokens": 2048}
        params["max_tokens"] = 8192

    return params


async def call_anthropic(
    messages: list[dict[str, Any]],
    config: AgentConfig,
    tools: list[dict[str, Any]] | None,
    normalize_fn: Any,
    tool_fn: Any,
    custom_provider: dict[str, Any] | None = None,
) -> LLMResult:
    """Non-streaming call to Anthropic API."""
    client = anthropic_client(config, custom_provider)
    model = normalize_fn(config.model_name, config.custom_providers)
    system_prompt, chat_msgs = to_anthropic_messages(messages)
    params = build_anthropic_params(
        model, chat_msgs, system_prompt, tools, config.model_name, tool_fn
    )

    response = await client.messages.create(**params)

    content_parts = []
    tool_calls = []
    for block in response.content:
        if block.type == "text":
            content_parts.append(block.text)
        elif block.type == "tool_use":
            tool_calls.append(
                ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=block.input if isinstance(block.input, dict) else {},
                )
            )

    usage = None
    if response.usage:
        usage = {
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
        }

    return LLMResult(
        content="".join(content_parts),
        tool_calls=tool_calls,
        finish_reason=response.stop_reason or "end_turn",
        usage=usage,
    )


async def stream_anthropic(
    messages: list[dict[str, Any]],
    config: AgentConfig,
    tools: list[dict[str, Any]] | None,
    normalize_fn: Any,
    tool_fn: Any,
    custom_provider: dict[str, Any] | None = None,
) -> AsyncGenerator[str | ToolCall | ThinkingChunk | dict[str, Any], None]:
    """Streaming call to Anthropic API with thinking chunk support."""
    client = anthropic_client(config, custom_provider)
    model = normalize_fn(config.model_name, config.custom_providers)
    system_prompt, chat_msgs = to_anthropic_messages(messages)
    params = build_anthropic_params(
        model, chat_msgs, system_prompt, tools, config.model_name, tool_fn
    )

    async with client.messages.stream(**params) as stream:
        async for event in stream:
            if event.type == "text":
                yield event.text
            elif event.type == "thinking":
                yield ThinkingChunk(text=event.thinking)

        final_msg = await stream.get_final_message()
        for block in final_msg.content:
            if block.type == "tool_use":
                yield ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=block.input if isinstance(block.input, dict) else {},
                )

        if final_msg.usage:
            yield {
                "event": "usage",
                "usage": {
                    "prompt_tokens": final_msg.usage.input_tokens,
                    "completion_tokens": final_msg.usage.output_tokens,
                    "total_tokens": final_msg.usage.input_tokens + final_msg.usage.output_tokens,
                },
            }
