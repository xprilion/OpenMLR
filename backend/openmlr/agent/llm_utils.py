"""Helper utilities for LLM provider discovery, model normalization, and authentication."""

from __future__ import annotations

import os
from typing import Any


def find_custom_provider(
    model_name: str, custom_providers: list[dict[str, Any]] | None
) -> dict[str, Any] | None:
    """Find matching custom provider for a model name."""
    if not custom_providers:
        return None
    mn = model_name.lower()
    for cp in custom_providers:
        pid = cp.get("id", "").lower()
        if pid and mn.startswith(f"{pid}/"):
            return cp
    return None


def get_api_key(
    model_name: str, custom_providers: list[dict[str, Any]] | None = None
) -> str | None:
    """Resolve API key based on provider prefix or environment variables."""
    mn = model_name.lower()
    cp = find_custom_provider(model_name, custom_providers)
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
        return os.environ.get("LOCAL_API_KEY", "not-needed")
    return (
        os.environ.get("OPENAI_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("OPENROUTER_API_KEY")
    )


def normalize_model(
    model_name: str, custom_providers: list[dict[str, Any]] | None = None
) -> str:
    """Strip provider prefix for upstream API calls."""
    cp = find_custom_provider(model_name, custom_providers)
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


def get_base_url(
    model_name: str, custom_providers: list[dict[str, Any]] | None = None
) -> str | None:
    """Get the base URL for local/custom OpenAI-compatible APIs."""
    mn = model_name.lower()
    cp = find_custom_provider(model_name, custom_providers)
    if cp:
        return cp.get("api_base", "").rstrip("/")
    if mn.startswith("local/"):
        return os.environ.get("LOCAL_API_BASE", "http://localhost:8000/v1")
    if mn.startswith("ollama/"):
        return os.environ.get("OLLAMA_API_BASE", "http://localhost:11434/v1")
    if mn.startswith("lmstudio/"):
        return os.environ.get("LMSTUDIO_API_BASE", "http://localhost:1234/v1")
    if mn.startswith("openrouter/"):
        return "https://openrouter.ai/api/v1"
    if mn.startswith("opencode-go/"):
        return "https://opencode.ai/zen/go/v1"
    return None


def is_opencode_go_anthropic_format(model_name: str) -> bool:
    """Determine if an OpenCode Go model uses Anthropic format instead of OpenAI format."""
    mn = model_name.lower().replace("opencode-go/", "")
    return mn in ("deepseek-v4-pro", "deepseek-v4-flash", "minimax-m2.7", "minimax-m2.5")


def supports_thinking(model_name: str) -> bool:
    """Check if model supports extended thinking (Claude 3.7+, Claude 4+)."""
    mn = model_name.lower()
    return "claude-3-7" in mn or "claude-3.7" in mn or "claude-4" in mn
