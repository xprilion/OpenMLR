"""LLM Abstraction — multi-provider support (OpenAI, Anthropic, OpenRouter, litellm)."""

import asyncio
import json
import os
from collections.abc import AsyncGenerator

from ..config import AgentConfig
from .types import LLMResult, ToolCall


class LLMProvider:
    """Handles LLM calls across multiple providers with streaming and retry."""

    @staticmethod
    def _find_custom_provider(model_name: str, custom_providers: list | None) -> dict | None:
        """Find matching custom provider for a model name."""
        if not custom_providers:
            return None
        mn = model_name.lower()
        for cp in custom_providers:
            pid = cp.get("id", "").lower()
            if pid and mn.startswith(f"{pid}/"):
                return cp
        return None

    @staticmethod
    def _get_api_key(model_name: str, custom_providers: list | None = None) -> str | None:
        mn = model_name.lower()
        # Check custom providers first
        cp = LLMProvider._find_custom_provider(model_name, custom_providers)
        if cp:
            return cp.get("api_key")
        if mn.startswith("openai/"):
            return os.environ.get("OPENAI_API_KEY")
        if mn.startswith("anthropic/"):
            return os.environ.get("ANTHROPIC_API_KEY")
        if mn.startswith("openrouter/"):
            return os.environ.get("OPENROUTER_API_KEY")
        if mn.startswith("opencode-go/"):
            return os.environ.get("OPENCODE_GO_API_KEY")
        if mn.startswith("local/") or mn.startswith("ollama/") or mn.startswith("lmstudio/"):
            # Local models often don't need API key, or use a placeholder
            return os.environ.get("LOCAL_API_KEY", "not-needed")
        return (
            os.environ.get("OPENAI_API_KEY")
            or os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("OPENROUTER_API_KEY")
        )

    @staticmethod
    def _normalize_model(model_name: str, custom_providers: list | None = None) -> str:
        # Check custom provider prefixes first
        cp = LLMProvider._find_custom_provider(model_name, custom_providers)
        if cp:
            pid = cp.get("id", "")
            if pid and model_name.lower().startswith(f"{pid.lower()}/"):
                return model_name[len(pid) + 1 :]
        for prefix in (
            "openai/",
            "openrouter/",
            "anthropic/",
            "litellm/",
            "local/",
            "ollama/",
            "lmstudio/",
            "opencode-go/",
        ):
            if model_name.startswith(prefix):
                return model_name[len(prefix) :]
        return model_name

    @staticmethod
    def _get_base_url(model_name: str, custom_providers: list | None = None) -> str | None:
        """Get the base URL for local/custom OpenAI-compatible APIs."""
        mn = model_name.lower()
        # Check custom providers first
        cp = LLMProvider._find_custom_provider(model_name, custom_providers)
        if cp:
            return cp.get("api_base", "").rstrip("/")
        if mn.startswith("local/"):
            # Custom base URL from env
            return os.environ.get("LOCAL_API_BASE", "http://localhost:8000/v1")
        if mn.startswith("ollama/"):
            return os.environ.get("OLLAMA_API_BASE", "http://localhost:11434/v1")
        if mn.startswith("lmstudio/"):
            return os.environ.get("LMSTUDIO_API_BASE", "http://localhost:1234/v1")
        if mn.startswith("openrouter/"):
            return "https://openrouter.ai/api/v1"
        if mn.startswith("opencode-go/"):
            # OpenCode Go uses OpenAI-compatible endpoint for most models
            # Some models (DeepSeek V4, MiniMax M2.7/M2.5) use Anthropic format
            model_id = mn.replace("opencode-go/", "")
            if model_id in ("deepseek-v4-pro", "deepseek-v4-flash", "minimax-m2.7", "minimax-m2.5"):
                return "https://opencode.ai/zen/go/v1"  # Anthropic format
            return "https://opencode.ai/zen/go/v1"  # OpenAI-compatible format
        return None

    @staticmethod
    def _is_opencode_go_anthropic_format(model_name: str) -> bool:
        """Check if OpenCode Go model uses Anthropic API format."""
        mn = model_name.lower()
        if not mn.startswith("opencode-go/"):
            return False
        model_id = mn.replace("opencode-go/", "")
        # These models use Anthropic messages format
        return model_id in ("deepseek-v4-pro", "deepseek-v4-flash", "minimax-m2.7", "minimax-m2.5")

    @staticmethod
    def _is_anthropic_model(model_name: str) -> bool:
        """True only for direct Anthropic API calls (anthropic/ prefix).
        OpenRouter-routed Claude models use the OpenAI-compatible path."""
        return model_name.lower().startswith("anthropic/")

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
    ) -> AsyncGenerator[str | ToolCall | dict, None]:
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
    ) -> AsyncGenerator[str | ToolCall | dict, None]:
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
    ) -> AsyncGenerator[str | ToolCall | dict, None]:
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
            # Unwrap if in OpenAI format
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
        """Merge consecutive user messages to satisfy Anthropic's strict alternation.

        Handles all combinations of string and list content blocks.
        """
        merged: list[dict] = []
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

    @staticmethod
    def _convert_assistant_msg(m: dict) -> dict:
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

    @staticmethod
    def _append_tool_result(chat: list[dict], m: dict) -> None:
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

    @staticmethod
    def _to_anthropic_messages(messages: list[dict]) -> tuple[str, list[dict]]:
        """Split system prompt and convert messages to Anthropic format."""
        system_parts = []
        chat = []
        for m in messages:
            role = m["role"]
            if role == "system":
                system_parts.append(m["content"])
            elif role == "user":
                chat.append({"role": "user", "content": m["content"]})
            elif role == "assistant":
                chat.append(LLMProvider._convert_assistant_msg(m))
            elif role == "tool":
                LLMProvider._append_tool_result(chat, m)

        return "\n\n".join(system_parts), LLMProvider._merge_consecutive_user_messages(chat)

    @staticmethod
    def _anthropic_client(config: AgentConfig):
        """Create Anthropic client with appropriate settings for native, OpenCode Go, or custom provider."""
        from anthropic import AsyncAnthropic

        mn = config.model_name.lower()
        # Check custom providers first
        cp = LLMProvider._find_custom_provider(config.model_name, config.custom_providers)
        if cp and cp.get("sdk_type") == "anthropic-sdk":
            return AsyncAnthropic(
                api_key=cp.get("api_key"),
                base_url=cp.get("api_base", "").rstrip("/"),
            )
        if mn.startswith("opencode-go/"):
            # OpenCode Go uses Anthropic format but different endpoint/key
            return AsyncAnthropic(
                api_key=os.environ.get("OPENCODE_GO_API_KEY"),
                base_url="https://opencode.ai/zen/go/v1",
            )
        # Native Anthropic
        return AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    @staticmethod
    async def _call_anthropic(
        messages: list[dict],
        config: AgentConfig,
        tools: list[dict] | None,
    ) -> LLMResult:
        model = LLMProvider._normalize_model(config.model_name, config.custom_providers)
        client = LLMProvider._anthropic_client(config)
        system_prompt, chat_msgs = LLMProvider._to_anthropic_messages(messages)

        params = {"model": model, "messages": chat_msgs, "max_tokens": 4096}
        if system_prompt:
            params["system"] = [
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        anthropic_tools = LLMProvider._anthropic_tool_param(tools)
        if anthropic_tools:
            params["tools"] = anthropic_tools

        params["extra_headers"] = {"anthropic-beta": "prompt-caching-2024-07-31"}
        response = await client.messages.create(**params)

        tool_calls = []
        text_content = ""
        for block in response.content:
            if block.type == "text":
                text_content += block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(id=block.id, name=block.name, arguments=block.input))

        usage = None
        if response.usage:
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            }

        return LLMResult(
            content=text_content,
            tool_calls=tool_calls,
            finish_reason=response.stop_reason or "end_turn",
            usage=usage,
        )

    @staticmethod
    async def _stream_anthropic(
        messages: list[dict],
        config: AgentConfig,
        tools: list[dict] | None,
    ) -> AsyncGenerator[str | ToolCall | dict, None]:
        model = LLMProvider._normalize_model(config.model_name, config.custom_providers)
        client = LLMProvider._anthropic_client(config)
        system_prompt, chat_msgs = LLMProvider._to_anthropic_messages(messages)

        params = {"model": model, "messages": chat_msgs, "max_tokens": 4096}
        if system_prompt:
            params["system"] = [
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        anthropic_tools = LLMProvider._anthropic_tool_param(tools)
        if anthropic_tools:
            params["tools"] = anthropic_tools

        params["extra_headers"] = {"anthropic-beta": "prompt-caching-2024-07-31"}
        async with client.messages.stream(**params) as stream:
            async for event in stream:
                if event.type == "content_block_delta":
                    if event.delta.type == "text_delta":
                        yield event.delta.text

                if event.type == "message_delta" and event.usage:
                    yield {
                        "event": "usage",
                        "usage": {"output_tokens": event.usage.output_tokens},
                    }

            final = await stream.get_final_message()
            for block in final.content:
                if block.type == "tool_use":
                    yield ToolCall(id=block.id, name=block.name, arguments=block.input)
