"""Unit tests for LLMProvider — API key resolution, model normalization, tool param conversion, retry logic."""

import pytest

from openmlr.agent.llm import LLMProvider


class TestGetApiKey:
    @pytest.mark.parametrize("model_name,env_var", [
        ("openai/gpt-4o", "OPENAI_API_KEY"),
        ("anthropic/claude-sonnet-4", "ANTHROPIC_API_KEY"),
        ("openrouter/openai/gpt-4o", "OPENROUTER_API_KEY"),
        ("opencode-go/glm-5.1", "OPENCODE_GO_API_KEY"),
    ])
    def test_model_prefix_maps_to_env_var(self, monkeypatch, model_name, env_var):
        monkeypatch.setenv(env_var, f"test-key-{env_var}")
        key = LLMProvider._get_api_key(model_name)
        assert key == f"test-key-{env_var}"

    def test_local_model_uses_local_api_key(self, monkeypatch):
        monkeypatch.setenv("LOCAL_API_KEY", "local")
        key = LLMProvider._get_api_key("local/default")
        assert key == "local"

    def test_ollama_defaults_to_not_needed(self, monkeypatch):
        monkeypatch.delenv("LOCAL_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        key = LLMProvider._get_api_key("ollama/llama3.1")
        assert key == "not-needed"

    def test_lmstudio_defaults_to_not_needed(self, monkeypatch):
        monkeypatch.delenv("LOCAL_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        key = LLMProvider._get_api_key("lmstudio/default")
        assert key == "not-needed"

    def test_fallback_to_any_available_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-anthro")
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        key = LLMProvider._get_api_key("unknown/model")
        assert key == "sk-anthro"


class TestNormalizeModel:
    @pytest.mark.parametrize("full_name,normalized", [
        ("openai/gpt-4o", "gpt-4o"),
        ("anthropic/claude-sonnet-4", "claude-sonnet-4"),
        ("openrouter/anthropic/claude-3-sonnet", "anthropic/claude-3-sonnet"),
        ("ollama/llama3.1", "llama3.1"),
        ("lmstudio/default", "default"),
        ("local/custom-model", "custom-model"),
        ("opencode-go/glm-5.1", "glm-5.1"),
    ])
    def test_normalize_strips_prefix(self, full_name, normalized):
        result = LLMProvider._normalize_model(full_name)
        assert result == normalized

    def test_no_prefix_passes_through(self):
        result = LLMProvider._normalize_model("gpt-4o")
        assert result == "gpt-4o"


class TestGetBaseUrl:
    def test_local_base_url(self):
        assert LLMProvider._get_base_url("local/default") == "http://localhost:8000/v1"

    def test_ollama_base_url(self):
        assert LLMProvider._get_base_url("ollama/llama3") == "http://localhost:11434/v1"

    def test_lmstudio_base_url(self):
        assert LLMProvider._get_base_url("lmstudio/default") == "http://localhost:1234/v1"

    def test_openrouter_base_url(self):
        assert LLMProvider._get_base_url("openrouter/gpt-4o") == "https://openrouter.ai/api/v1"

    def test_opencode_go_base_url(self):
        assert LLMProvider._get_base_url("opencode-go/glm-5.1") == "https://opencode.ai/zen/go/v1"

    def test_standard_provider_no_base_url(self):
        assert LLMProvider._get_base_url("openai/gpt-4o") is None
        assert LLMProvider._get_base_url("anthropic/claude-4") is None

    def test_local_custom_base_url(self, monkeypatch):
        monkeypatch.setenv("LOCAL_API_BASE", "http://custom:9999/v1")
        assert LLMProvider._get_base_url("local/model") == "http://custom:9999/v1"

    def test_ollama_custom_base_url(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_API_BASE", "http://remote:11435/v1")
        assert LLMProvider._get_base_url("ollama/model") == "http://remote:11435/v1"

    def test_lmstudio_custom_base_url(self, monkeypatch):
        monkeypatch.setenv("LMSTUDIO_API_BASE", "http://other:1235/v1")
        assert LLMProvider._get_base_url("lmstudio/model") == "http://other:1235/v1"


class TestAnthropicFormatDetection:
    def test_native_anthropic(self):
        assert LLMProvider._is_anthropic_model("anthropic/claude-sonnet-4") is True

    def test_openrouter_is_not_anthropic(self):
        assert LLMProvider._is_anthropic_model("openrouter/anthropic/claude-4") is False

    def test_opencode_go_deepseek_is_anthropic_format(self):
        assert LLMProvider._is_opencode_go_anthropic_format("opencode-go/deepseek-v4-pro") is True

    def test_opencode_go_deepseek_flash_is_anthropic_format(self):
        assert LLMProvider._is_opencode_go_anthropic_format("opencode-go/deepseek-v4-flash") is True

    def test_opencode_go_minimax_is_anthropic_format(self):
        assert LLMProvider._is_opencode_go_anthropic_format("opencode-go/minimax-m2.7") is True

    def test_opencode_go_glm_is_not_anthropic_format(self):
        assert LLMProvider._is_opencode_go_anthropic_format("opencode-go/glm-5.1") is False

    def test_uses_anthropic_format_native(self):
        assert LLMProvider._uses_anthropic_format("anthropic/claude-4") is True

    def test_uses_anthropic_format_opencode_go_deepseek(self):
        assert LLMProvider._uses_anthropic_format("opencode-go/deepseek-v4-pro") is True

    def test_uses_anthropic_format_openai(self):
        assert LLMProvider._uses_anthropic_format("openai/gpt-4o") is False


class TestToolParamConversion:
    def test_openai_tool_param_none(self):
        assert LLMProvider._openai_tool_param(None) is None

    def test_openai_tool_param_empty(self):
        assert LLMProvider._openai_tool_param([]) is None

    def test_openai_tool_param_raw_format(self):
        tools = [
            {"name": "search", "description": "Search web", "parameters": {"type": "object", "properties": {}}},
        ]
        result = LLMProvider._openai_tool_param(tools)
        assert len(result) == 1
        assert result[0]["type"] == "function"
        assert result[0]["function"]["name"] == "search"

    def test_openai_tool_param_already_formatted(self):
        tools = [
            {"type": "function", "function": {"name": "bash", "description": "Run cmd", "parameters": {}}},
        ]
        result = LLMProvider._openai_tool_param(tools)
        assert len(result) == 1
        assert result[0]["type"] == "function"

    def test_anthropic_tool_param_none(self):
        assert LLMProvider._anthropic_tool_param(None) is None

    def test_anthropic_tool_param_conversion(self):
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "read",
                    "description": "Read file",
                    "parameters": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"],
                    },
                },
            },
        ]
        result = LLMProvider._anthropic_tool_param(tools)
        assert len(result) == 1
        assert result[0]["name"] == "read"
        assert result[0]["input_schema"]["type"] == "object"
        assert "path" in result[0]["input_schema"]["properties"]
        assert result[0]["input_schema"]["required"] == ["path"]

    def test_anthropic_tool_param_unwrapped(self):
        tools = [
            {"name": "bash", "description": "Run cmd", "parameters": {"type": "object", "properties": {}}},
        ]
        result = LLMProvider._anthropic_tool_param(tools)
        assert len(result) == 1
        assert result[0]["name"] == "bash"


class TestToAnthropicMessages:
    def test_separates_system_prompt(self):
        messages = [
            {"role": "system", "content": "You are an assistant."},
            {"role": "user", "content": "Hello"},
        ]
        system, chat = LLMProvider._to_anthropic_messages(messages)
        assert "You are an assistant" in system
        assert len(chat) == 1
        assert chat[0]["role"] == "user"
        assert chat[0]["content"] == "Hello"

    def test_converts_assistant_with_tool_calls(self):
        messages = [
            {"role": "user", "content": "Read file"},
            {
                "role": "assistant",
                "content": "Let me read that.",
                "tool_calls": [
                    {"id": "tc1", "name": "read_file", "arguments": {"path": "/tmp/test"}},
                ],
            },
        ]
        _system, chat = LLMProvider._to_anthropic_messages(messages)
        assert len(chat) == 2

    def test_converts_tool_result(self):
        messages = [
            {"role": "tool", "content": "file contents here", "tool_call_id": "tc1"},
        ]
        _system, chat = LLMProvider._to_anthropic_messages(messages)
        assert len(chat) == 1
        assert chat[0]["role"] == "user"


class TestRetryLogic:
    def test_is_retryable_rate_limit(self):
        assert LLMProvider._is_retryable(Exception("429 Rate limit exceeded")) is True

    def test_is_retryable_timeout(self):
        assert LLMProvider._is_retryable(Exception("Connection timeout")) is True

    def test_is_retryable_server_error(self):
        assert LLMProvider._is_retryable(Exception("server_error 503")) is True

    def test_is_not_retryable_auth_error(self):
        assert LLMProvider._is_retryable(Exception("Invalid API key")) is False

    def test_is_not_retryable_validation_error(self):
        assert LLMProvider._is_retryable(Exception("Model not found")) is False

    def test_is_retryable_overloaded(self):
        assert LLMProvider._is_retryable(Exception("Server is overloaded")) is True

    def test_is_retryable_capacity(self):
        assert LLMProvider._is_retryable(Exception("Exceeded capacity")) is True

    def test_is_retryable_502(self):
        assert LLMProvider._is_retryable(Exception("502 Bad Gateway")) is True
