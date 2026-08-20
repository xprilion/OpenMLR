"""LLM Abstraction — multi-provider support (OpenAI, Anthropic, OpenRouter, litellm)."""

import asyncio
import json
from collections.abc import AsyncGenerator

from ..config import AgentConfig
from .llm_utils import (
    find_custom_provider,
    get_api_key,
    get_base_url,
    is_opencode_go_anthropic_format,
    normalize_model,
    supports_thinking,
)
from .types import LLMResult, ThinkingChunk, ToolCall


class LLMProvider:
    """Handles LLM calls across multiple providers with streaming and retry."""

    @staticmethod
    def _find_custom_provider(model_name: str, custom_providers: list | None) -> dict | None:
        return find_custom_provider(model_name, custom_providers)

    @staticmethod
    def _get_api_key(model_name: str, custom_providers: list | None = None) -> str | None:
        return get_api_key(model_name, custom_providers)

    @staticmethod
    def _normalize_model(model_name: str, custom_providers: list | None = None) -> str:
        return normalize_model(model_name, custom_providers)

    @staticmethod
    def _get_base_url(model_name: str, custom_providers: list | None = None) -> str | None:
        return get_base_url(model_name, custom_providers)

    @staticmethod
    def _is_opencode_go_anthropic_format(model_name: str) -> bool:
        return is_opencode_go_anthropic_format(model_name)

    @staticmethod
    def _is_anthropic_model(model_name: str) -> bool:
        return model_name.lower().startswith("anthropic/")

    @staticmethod
    def _supports_thinking(model_name: str) -> bool:
        return supports_thinking(model_name)

    @staticmethod
    def _uses_anthropic_format(model_name: str, custom_providers: list | None = None) -> bool:
        """Check if model uses Anthropic message format (native Anthropic, OpenCode Go Anthropic, or custom provider with anthropic-sdk)."""
        if LLMProvider._is_anthropic_model(model_name):
            return True
        if LLMProvider._is_opencode_go_anthropic_format(model_name):
            return True
        cp = LLMProvider._find_custom_provider(model_name, custom_providers)
        if cp and cp.get("sdk_type") == "anthropic-sdk":
            return True
        return False

    # ── Public API ────────────────────────────────────────

    @staticmethod
    async def generate(
        messages: list[dict],
        config: AgentConfig,
        tools: list[dict] | None = None,
    ) -> LLMResult:
        return await LLMProvider._call_with_retry(messages, config, tools)

    @staticmethod
    async def generate_stream(
        messages: list[dict],
        config: AgentConfig,
        tools: list[dict] | None = None,
    ) -> AsyncGenerator[str | ToolCall | ThinkingChunk | dict, None]:
        async for chunk in LLMProvider._stream_with_retry(messages, config, tools):
            yield chunk

    @staticmethod
    async def generate_title(
        messages: list[dict],
        config: AgentConfig,
    ) -> str | None:
        title_prompt = (
            "Based on the conversation, generate a short title "
            "(max 6 words). Return ONLY the title, nothing else."
        )
        title_messages = [
            {"role": m.get("role", "user"), "content": (m.get("content") or "")[:2000]}
            for m in messages[-4:]
        ]
        title_messages.append({"role": "user", "content": title_prompt})

        title_config = AgentConfig(
            model_name=config.title_model,
            stream=False,
            max_iterations=1,
        )
        try:
            result = await LLMProvider.generate(title_messages, title_config)
            content = result.content.strip().strip('"').strip("'")
            return content[:100] if content else None
        except Exception:
            return None

    # ── Retry wrappers ────────────────────────────────────

    @staticmethod
    def _is_retryable(e: Exception) -> bool:
        msg = str(e).lower()
        return any(
            x in msg
            for x in [
                "429",
                "rate",
                "timeout",
                "server_error",
                "503",
                "502",
                "overloaded",
                "connection",
                "capacity",
            ]
        )

    @staticmethod
    async def _call_with_retry(
        messages: list[dict],
        config: AgentConfig,
        tools: list[dict] | None = None,
        max_retries: int = 3,
    ) -> LLMResult:
        last_error = None
        for attempt in range(max_retries):
            try:
                if LLMProvider._uses_anthropic_format(config.model_name, config.custom_providers):
                    return await LLMProvider._call_anthropic(messages, config, tools)
                else:
                    return await LLMProvider._call_openai(messages, config, tools)
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1 and LLMProvider._is_retryable(e):
                    await asyncio.sleep(2 ** (attempt + 1))
                    continue
                raise
        raise last_error or Exception("LLM call failed")

    @staticmethod
    async def _stream_with_retry(
        messages: list[dict],
        config: AgentConfig,
        tools: list[dict] | None = None,
    ) -> AsyncGenerator[str | ToolCall | ThinkingChunk | dict, None]:
        last_error = None
        for attempt in range(3):
            try:
                if LLMProvider._uses_anthropic_format(config.model_name, config.custom_providers):
                    async for chunk in LLMProvider._stream_anthropic(messages, config, tools):
                        yield chunk
                else:
                    async for chunk in LLMProvider._stream_openai(messages, config, tools):
                        yield chunk
                return
            except Exception as e:
                last_error = e
                if attempt < 2 and LLMProvider._is_retryable(e):
                    await asyncio.sleep(2 ** (attempt + 1))
                    continue
                raise
        raise last_error or Exception("LLM streaming call failed")

    # ── OpenAI / OpenRouter ───────────────────────────────

    @staticmethod
    def _openai_client(config: AgentConfig):
        import logging

        from openai import AsyncOpenAI

        logger = logging.getLogger(__name__)

        api_key = LLMProvider._get_api_key(config.model_name, config.custom_providers)
        base_url = LLMProvider._get_base_url(config.model_name, config.custom_providers)

        logger.debug(
            f"[LLM] Model: {config.model_name}, Base URL: {base_url}, API key set: {bool(api_key)}"
        )

        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        return AsyncOpenAI(**kwargs)

    @staticmethod
    def _openai_tool_param(tools: list[dict] | None) -> list[dict] | None:
        """Convert tool specs to OpenAI tools param. Handles both raw and pre-wrapped."""
        if not tools:
            return None
        result = []
        for t in tools:
            if "type" in t and "function" in t:
                # Already in OpenAI format: {"type": "function", "function": {...}}
                result.append(t)
            else:
                # Raw: {"name": ..., "description": ..., "parameters": ...}
                result.append({"type": "function", "function": t})
        return result

    @staticmethod
    async def _call_openai(
        messages: list[dict],
        config: AgentConfig,
        tools: list[dict] | None,
    ) -> LLMResult:
        client = LLMProvider._openai_client(config)
        model = LLMProvider._normalize_model(config.model_name, config.custom_providers)

        params = {"model": model, "messages": messages, "max_tokens": 4096}
        openai_tools = LLMProvider._openai_tool_param(tools)
        if openai_tools:
            params["tools"] = openai_tools

        response = await client.chat.completions.create(**params)
        choice = response.choices[0]

        tool_calls = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, AttributeError):
                    args = {}
                tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args))

        usage = None
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        return LLMResult(
            content=choice.message.content or "",
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
            usage=usage,
        )

    @staticmethod
    async def _stream_openai(
        messages: list[dict],
        config: AgentConfig,
        tools: list[dict] | None,
    ) -> AsyncGenerator[str | ToolCall | ThinkingChunk | dict, None]:
        client = LLMProvider._openai_client(config)
        model = LLMProvider._normalize_model(config.model_name, config.custom_providers)

        params = {
            "model": model,
            "messages": messages,
            "max_tokens": 4096,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        openai_tools = LLMProvider._openai_tool_param(tools)
        if openai_tools:
            params["tools"] = openai_tools

        stream = await client.chat.completions.create(**params)

        tool_call_buffers: dict[int, dict] = {}

        async for chunk in stream:
            # Usage-only chunk (no choices)
            if not chunk.choices and chunk.usage:
                yield {
                    "event": "usage",
                    "usage": {
                        "prompt_tokens": chunk.usage.prompt_tokens,
                        "completion_tokens": chunk.usage.completion_tokens,
                        "total_tokens": chunk.usage.total_tokens,
                    },
                }
                continue

            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta
            if delta is None:
                continue

            # Reasoning content (OpenAI o1/o3 reasoning models)
            reasoning = getattr(delta, "reasoning_content", None)
            if reasoning:
                yield ThinkingChunk(text=reasoning)

            # Text content
            if delta.content:
                yield delta.content

            # Tool call deltas — accumulate in buffers
            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    if idx not in tool_call_buffers:
                        tool_call_buffers[idx] = {"id": "", "name": "", "arguments": ""}

                    buf = tool_call_buffers[idx]
                    if tc_delta.id:
                        buf["id"] = tc_delta.id
                    if tc_delta.function:
                        if tc_delta.function.name:
                            buf["name"] += tc_delta.function.name
                        if tc_delta.function.arguments:
                            buf["arguments"] += tc_delta.function.arguments

        # Stream ended — yield accumulated tool calls
        for _idx in sorted(tool_call_buffers.keys()):
            buf = tool_call_buffers[_idx]
            try:
                args = json.loads(buf["arguments"]) if buf["arguments"] else {}
            except json.JSONDecodeError:
                args = {}
            yield ToolCall(id=buf["id"], name=buf["name"], arguments=args)

    # ── Anthropic ─────────────────────────────────────────

    @staticmethod
    def _anthropic_tool_param(tools: list[dict] | None) -> list[dict] | None:
        """Convert tool specs to Anthropic format."""
        if not tools:
            return None
        result = []
        for t in tools:
            func = t.get("function", t)
            result.append(
                {
                    "name": func["name"],
                    "description": func.get("description", ""),
                    "input_schema": {
                        "type": "object",
                        "properties": func.get("parameters", {}).get("properties", {}),
                        "required": func.get("parameters", {}).get("required", []),
                    },
                }
            )
        return result

    @staticmethod
    def _merge_consecutive_user_messages(chat: list[dict]) -> list[dict]:
        from .llm_anthropic import merge_consecutive_user_messages
        return merge_consecutive_user_messages(chat)

    @staticmethod
    def _convert_assistant_msg(m: dict) -> dict:
        from .llm_anthropic import convert_assistant_msg
        return convert_assistant_msg(m)

    @staticmethod
    def _append_tool_result(chat: list[dict], m: dict) -> None:
        from .llm_anthropic import append_tool_result
        append_tool_result(chat, m)

    @staticmethod
    def _to_anthropic_messages(messages: list[dict]) -> tuple[str, list[dict]]:
        from .llm_anthropic import to_anthropic_messages
        return to_anthropic_messages(messages)

    @staticmethod
    def _anthropic_client(config: AgentConfig):
        from .llm_anthropic import anthropic_client
        cp = LLMProvider._find_custom_provider(config.model_name, config.custom_providers)
        return anthropic_client(config, cp)

    @staticmethod
    def _build_anthropic_params(
        model: str,
        chat_msgs: list[dict],
        system_prompt: str,
        tools: list[dict] | None,
        model_name: str,
    ) -> dict:
        from .llm_anthropic import build_anthropic_params
        return build_anthropic_params(
            model,
            chat_msgs,
            system_prompt,
            tools,
            model_name,
            LLMProvider._anthropic_tool_param,
        )

    @staticmethod
    async def _call_anthropic(
        messages: list[dict],
        config: AgentConfig,
        tools: list[dict] | None,
    ) -> LLMResult:
        from .llm_anthropic import call_anthropic
        cp = LLMProvider._find_custom_provider(config.model_name, config.custom_providers)
        return await call_anthropic(
            messages,
            config,
            tools,
            LLMProvider._normalize_model,
            LLMProvider._anthropic_tool_param,
            cp,
        )

    @staticmethod
    async def _stream_anthropic(
        messages: list[dict],
        config: AgentConfig,
        tools: list[dict] | None,
    ) -> AsyncGenerator[str | ToolCall | ThinkingChunk | dict, None]:
        from .llm_anthropic import stream_anthropic
        cp = LLMProvider._find_custom_provider(config.model_name, config.custom_providers)
        async for item in stream_anthropic(
            messages,
            config,
            tools,
            LLMProvider._normalize_model,
            LLMProvider._anthropic_tool_param,
            cp,
        ):
            yield item
