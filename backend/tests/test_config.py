"""Tests for openmlr.config (AgentConfig, get_model_max_tokens) and estimate_tokens."""

import pytest

from openmlr.agent.context import estimate_tokens
from openmlr.config import AgentConfig, get_model_max_tokens

# ---------------------------------------------------------------------------
# AgentConfig defaults
# ---------------------------------------------------------------------------

class TestAgentConfigDefaults:
    def test_model_name_default_empty(self):
        cfg = AgentConfig()
        assert cfg.model_name == ""

    def test_max_iterations_default(self):
        assert AgentConfig().max_iterations == 300

    def test_stream_default(self):
        assert AgentConfig().stream is True

    def test_yolo_mode_default(self):
        assert AgentConfig().yolo_mode is False

    def test_compact_threshold_ratio_default(self):
        assert AgentConfig().compact_threshold_ratio == 0.90

    def test_untouched_messages_default(self):
        assert AgentConfig().untouched_messages == 5

    def test_default_max_tokens_default(self):
        assert AgentConfig().default_max_tokens == 200_000

    def test_confirm_sandbox_creation_default(self):
        assert AgentConfig().confirm_sandbox_creation is True

    def test_confirm_destructive_ops_default(self):
        assert AgentConfig().confirm_destructive_ops is True

    def test_research_model_default_empty(self):
        assert AgentConfig().research_model == ""

    def test_title_model_default_empty(self):
        assert AgentConfig().title_model == ""

    def test_paper_search_budget_default(self):
        assert AgentConfig().paper_search_budget == 25

    def test_require_plan_approval_default(self):
        assert AgentConfig().require_plan_approval is True

    def test_mcp_servers_default_empty_dict(self):
        cfg = AgentConfig()
        assert cfg.mcp_servers == {}
        assert isinstance(cfg.mcp_servers, dict)

    def test_mcp_servers_not_shared_across_instances(self):
        """Each instance should get its own dict (field default_factory)."""
        a = AgentConfig()
        b = AgentConfig()
        a.mcp_servers["x"] = 1
        assert "x" not in b.mcp_servers


# ---------------------------------------------------------------------------
# get_model_max_tokens — known models
# ---------------------------------------------------------------------------

class TestGetModelMaxTokensKnown:
    @pytest.mark.parametrize(
        "model_name, expected",
        [
            ("openai/gpt-4o", 128_000),
            ("openai/gpt-4o-mini", 128_000),
            ("gpt-4-turbo", 128_000),
            ("gpt-4", 8_192),
            ("gpt-3.5-turbo", 16_385),
            ("anthropic/claude-sonnet-4-20250514", 200_000),
            ("anthropic/claude-opus-4-20250514", 200_000),
            ("anthropic/claude-haiku-4-20250514", 200_000),
            ("claude-3-opus", 200_000),
            ("claude-3-sonnet", 200_000),
            ("claude-3-haiku", 200_000),
            ("google/gemini-2.5-pro", 1_048_576),
            ("google/gemini-2.5-flash", 1_048_576),
            ("gemini-2.0-flash", 1_048_576),
            ("gemini-pro", 32_768),
        ],
    )
    def test_known_model(self, model_name: str, expected: int):
        assert get_model_max_tokens(model_name) == expected

    def test_case_insensitive_matching(self):
        assert get_model_max_tokens("GPT-4O") == 128_000
        assert get_model_max_tokens("Claude-Sonnet-4") == 200_000

    def test_model_name_with_prefix(self):
        """Model names with provider prefixes should still match."""
        assert get_model_max_tokens("openrouter/openai/gpt-4o-mini") == 128_000


# ---------------------------------------------------------------------------
# get_model_max_tokens — unknown models
# ---------------------------------------------------------------------------

class TestGetModelMaxTokensUnknown:
    def test_unknown_model_returns_default(self):
        assert get_model_max_tokens("my-custom-model") == 200_000

    def test_empty_string_returns_default(self):
        assert get_model_max_tokens("") == 200_000

    def test_gibberish_returns_default(self):
        assert get_model_max_tokens("xyzzy-9000-turbo-ultra") == 200_000


# ---------------------------------------------------------------------------
# estimate_tokens (from context.py)
# ---------------------------------------------------------------------------

class TestEstimateTokens:
    def test_empty_string_returns_one(self):
        """Empty string yields at least 1 (max(1, 0//4))."""
        assert estimate_tokens("") == 1

    def test_short_string(self):
        # "hi" -> len=2, 2//4 = 0, max(1,0) = 1
        assert estimate_tokens("hi") == 1

    def test_four_char_string(self):
        # "abcd" -> len=4, 4//4 = 1
        assert estimate_tokens("abcd") == 1

    def test_longer_string(self):
        text = "a" * 100
        assert estimate_tokens(text) == 25  # 100 // 4

    def test_rough_proportionality(self):
        short = estimate_tokens("hello world")  # 11 chars -> 2
        long = estimate_tokens("hello world " * 100)  # 1200 chars -> 300
        assert long > short

    def test_never_returns_zero(self):
        # For any input the minimum should be 1
        for s in ("", "a", "ab", "abc"):
            assert estimate_tokens(s) >= 1
