"""Configuration loading with layered priority: env vars > project config > defaults."""

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()


@dataclass
class AgentConfig:
    model_name: str = ""  # empty = auto-detect from available providers
    max_iterations: int = 300
    stream: bool = True
    yolo_mode: bool = False
    compact_threshold_ratio: float = 0.90
    untouched_messages: int = 5
    default_max_tokens: int = 200000
    confirm_sandbox_creation: bool = True
    confirm_destructive_ops: bool = True
    research_model: str = ""
    title_model: str = ""
    paper_search_budget: int = 25
    require_plan_approval: bool = True
    mcp_servers: dict = field(default_factory=dict)


DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "configs" / "agent_config.yaml"


def detect_default_model() -> str:
    """Pick the best available model based on which API keys are configured."""
    # Check for local models first
    if os.environ.get("LOCAL_API_BASE"):
        return os.environ.get("LOCAL_MODEL", "local/default")
    if os.environ.get("OLLAMA_API_BASE") or os.environ.get("OLLAMA_MODEL"):
        return f"ollama/{os.environ.get('OLLAMA_MODEL', 'llama3.1')}"
    if os.environ.get("LMSTUDIO_API_BASE"):
        return os.environ.get("LMSTUDIO_MODEL", "lmstudio/default")
    # Cloud providers
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic/claude-sonnet-4-20250514"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai/gpt-4o"
    if os.environ.get("OPENROUTER_API_KEY"):
        return "openrouter/anthropic/claude-sonnet-4"
    # Fallback — will error at call time with a clear message
    return "openrouter/anthropic/claude-sonnet-4"


def detect_cheap_model() -> str:
    """Pick a cheap/fast model for title generation and research sub-agent."""
    # For local models, use the same model (no separate cheap model)
    if os.environ.get("LOCAL_API_BASE"):
        return os.environ.get("LOCAL_MODEL", "local/default")
    if os.environ.get("OLLAMA_API_BASE") or os.environ.get("OLLAMA_MODEL"):
        return f"ollama/{os.environ.get('OLLAMA_MODEL', 'llama3.1')}"
    if os.environ.get("LMSTUDIO_API_BASE"):
        return os.environ.get("LMSTUDIO_MODEL", "lmstudio/default")
    # Cloud providers
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic/claude-haiku-4-20250514"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai/gpt-4o-mini"
    if os.environ.get("OPENROUTER_API_KEY"):
        return "openrouter/openai/gpt-4o-mini"
    return "openrouter/openai/gpt-4o-mini"


def load_config(config_path: Path | None = None) -> AgentConfig:
    """Load agent configuration with layered priority."""
    config = AgentConfig()

    # Layer 1: Default YAML config
    path = config_path or (DEFAULT_CONFIG_PATH if DEFAULT_CONFIG_PATH.exists() else None)
    if path and path.exists():
        with open(path) as f:
            yaml_config = yaml.safe_load(f) or {}
        for key, value in yaml_config.items():
            if hasattr(config, key):
                setattr(config, key, value)

    # Layer 2: Environment variable overrides
    env_overrides = {
        "OPEN_MLR_MODEL": "model_name",
        "OPEN_MLR_MAX_ITERATIONS": "max_iterations",
        "OPEN_MLR_YOLO": "yolo_mode",
    }
    for env_key, config_key in env_overrides.items():
        val = os.environ.get(env_key)
        if val is not None:
            field_type = type(getattr(config, config_key))
            if field_type is bool:
                setattr(config, config_key, val.lower() in ("1", "true", "yes"))
            elif field_type is int:
                setattr(config, config_key, int(val))
            elif field_type is float:
                setattr(config, config_key, float(val))
            else:
                setattr(config, config_key, val)

    # Layer 3: Auto-detect models if not explicitly set
    if not config.model_name:
        config.model_name = detect_default_model()
    if not config.research_model:
        config.research_model = detect_cheap_model()
    if not config.title_model:
        config.title_model = detect_cheap_model()

    return config


# Known model max token mappings
MODEL_MAX_TOKENS = {
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "gpt-4-turbo": 128000,
    "gpt-4": 8192,
    "gpt-3.5-turbo": 16385,
    "claude-sonnet-4": 200000,
    "claude-opus-4": 200000,
    "claude-haiku-4": 200000,
    "claude-sonnet-4-5": 200000,
    "claude-opus-4-1": 200000,
    "claude-3-opus": 200000,
    "claude-3-sonnet": 200000,
    "claude-3-haiku": 200000,
    "gemini-2.5-pro": 1048576,
    "gemini-2.5-flash": 1048576,
    "gemini-2.0-flash": 1048576,
    "gemini-pro": 32768,
}


def get_model_max_tokens(model_name: str) -> int:
    model_lower = model_name.lower()
    for key, tokens in MODEL_MAX_TOKENS.items():
        if key in model_lower:
            return tokens
    return 200000
