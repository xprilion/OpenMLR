"""LLM Abstraction — multi-provider support (OpenAI, Anthropic, OpenRouter, litellm)."""

import os
import json
import asyncio
from typing import AsyncGenerator, Optional
from .types import LLMResult, ToolCall, ToolSpec
from ..config import AgentConfig


class LLMProvider:
    """Handles LLM calls across multiple providers with streaming and retry."""

    @staticmethod
    def _get_api_key(model_name: str) -> Optional[str]:
        mn = model_name.lower()
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
    def _normalize_model(model_name: str) -> str:
        for prefix in ("openai/", "openrouter/", "anthropic/", "litellm/", "local/", "ollama/", "lmstudio/", "opencode-go/"):
            if model_name.startswith(prefix):
                return model_name[len(prefix):]
        return model_name
    
    @staticmethod
    def _get_base_url(model_name: str) -> Optional[str]:
        """Get the base URL for local/custom OpenAI-compatible APIs."""
        mn = model_name.lower()
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
    def _uses_anthropic_format(model_name: str) -> bool:
        """Check if model uses Anthropic message format (native Anthropic or OpenCode Go Anthropic models)."""
        if LLMProvider._is_anthropic_model(model_name):
            return True
        return LLMProvider._is_opencode_go_anthropic_format(model_name)

    # ── Public API ────────────────────────────────────────

    @staticmethod
    async def generate(
        messages: list[dict],
        config: AgentConfig,
        tools: Optional[list[dict]] = None,
    ) -> LLMResult:
        return await LLMProvider._call_with_retry(messages, config, tools)

    @staticmethod
    async def generate_stream(
        messages: list[dict],
        config: AgentConfig,
        tools: Optional[list[dict]] = None,
    ) -> AsyncGenerator[str | ToolCall | dict, None]:
        async for chunk in LLMProvider._stream_with_retry(messages, config, tools):
            yield chunk

    @staticmethod
    async def generate_title(
        messages: list[dict],
        config: AgentConfig,
    ) -> Optional[str]:
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
        return any(x in msg for x in [
            "429", "rate", "timeout", "server_error", "503", "502",
            "overloaded", "connection", "capacity",
        ])

    @staticmethod
    async def _call_with_retry(
        messages: list[dict],
        config: AgentConfig,
        tools: Optional[list[dict]] = None,
        max_retries: int = 3,
    ) -> LLMResult:
        last_error = None
        for attempt in range(max_retries):
            try:
                if LLMProvider._uses_anthropic_format(config.model_name):
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
        tools: Optional[list[dict]] = None,
    ) -> AsyncGenerator[str | ToolCall | dict, None]:
        last_error = None
        for attempt in range(3):
            try:
                if LLMProvider._uses_anthropic_format(config.model_name):
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
        from openai import AsyncOpenAI
        import logging
        logger = logging.getLogger(__name__)
        
        api_key = LLMProvider._get_api_key(config.model_name)
        base_url = LLMProvider._get_base_url(config.model_name)
        
        logger.debug(f"[LLM] Model: {config.model_name}, Base URL: {base_url}, API key set: {bool(api_key)}")
        
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        return AsyncOpenAI(**kwargs)

    @staticmethod
    def _openai_tool_param(tools: Optional[list[dict]]) -> Optional[list[dict]]:
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
        tools: Optional[list[dict]],
    ) -> LLMResult:
        client = LLMProvider._openai_client(config)
        model = LLMProvider._normalize_model(config.model_name)

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
        tools: Optional[list[dict]],
    ) -> AsyncGenerator[str | ToolCall | dict, None]:
        client = LLMProvider._openai_client(config)
        model = LLMProvider._normalize_model(config.model_name)

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
    def _anthropic_tool_param(tools: Optional[list[dict]]) -> Optional[list[dict]]:
        """Convert tool specs to Anthropic format."""
        if not tools:
            return None
        result = []
        for t in tools:
            # Unwrap if in OpenAI format
            func = t.get("function", t)
            result.append({
                "name": func["name"],
                "description": func.get("description", ""),
                "input_schema": {
                    "type": "object",
                    "properties": func.get("parameters", {}).get("properties", {}),
                    "required": func.get("parameters", {}).get("required", []),
                },
            })
        return result

    @staticmethod
    def _to_anthropic_messages(messages: list[dict]) -> tuple[str, list[dict]]:
        """Split system prompt and convert messages to Anthropic format."""
        system_parts = []
        chat = []
        for m in messages:
            if m["role"] == "system":
                system_parts.append(m["content"])
            elif m["role"] == "user":
                chat.append({"role": "user", "content": m["content"]})
            elif m["role"] == "assistant":
                content_blocks = []
                if m.get("content"):
                    content_blocks.append({"type": "text", "text": m["content"]})
                for tc in m.get("tool_calls", []):
                    func = tc.get("function", tc)
                    content_blocks.append({
                        "type": "tool_use",
                        "id": tc.get("id", ""),
                        "name": func.get("name", tc.get("name", "")),
                        "input": func.get("arguments", tc.get("arguments", {})),
                    })
                chat.append({"role": "assistant", "content": content_blocks or m.get("content", "")})
            elif m["role"] == "tool":
                chat.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": m.get("tool_call_id", ""),
                        "content": m["content"],
                    }],
                })
        return "\n\n".join(system_parts), chat

    @staticmethod
    def _anthropic_client(config: AgentConfig):
        """Create Anthropic client with appropriate settings for native or OpenCode Go."""
        from anthropic import AsyncAnthropic
        
        mn = config.model_name.lower()
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
        tools: Optional[list[dict]],
    ) -> LLMResult:
        model = LLMProvider._normalize_model(config.model_name)
        client = LLMProvider._anthropic_client(config)
        system_prompt, chat_msgs = LLMProvider._to_anthropic_messages(messages)

        params = {"model": model, "messages": chat_msgs, "max_tokens": 4096}
        if system_prompt:
            params["system"] = system_prompt
        anthropic_tools = LLMProvider._anthropic_tool_param(tools)
        if anthropic_tools:
            params["tools"] = anthropic_tools

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
        tools: Optional[list[dict]],
    ) -> AsyncGenerator[str | ToolCall | dict, None]:
        model = LLMProvider._normalize_model(config.model_name)
        client = LLMProvider._anthropic_client(config)
        system_prompt, chat_msgs = LLMProvider._to_anthropic_messages(messages)

        params = {"model": model, "messages": chat_msgs, "max_tokens": 4096}
        if system_prompt:
            params["system"] = system_prompt
        anthropic_tools = LLMProvider._anthropic_tool_param(tools)
        if anthropic_tools:
            params["tools"] = anthropic_tools

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
