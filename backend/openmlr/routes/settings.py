"""Settings routes — user settings, provider config, model management."""

import os
from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import operations as ops
from ..db.engine import get_db
from ..db.models import User
from ..dependencies import get_current_user

router = APIRouter(prefix="/api", tags=["settings"])


# ---- User Settings ----


@router.get("/settings")
async def get_all_settings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    settings = await ops.get_all_settings(db, user.id)
    return {"settings": settings}


@router.get("/settings/{category}")
async def get_settings_category(
    category: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    settings = await ops.get_all_settings(db, user.id, category=category)
    return {"settings": settings.get(category, {})}


@router.put("/settings/{category}/{key}")
async def update_setting(
    category: str,
    key: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    body = await request.json()
    value = body.get("value")
    if value is None:
        raise HTTPException(status_code=400, detail="Missing 'value'")

    await ops.set_user_setting(db, user.id, category, key, value)

    # For provider keys, also update env vars in-process
    if category == "providers":
        env_key_map = {
            "openai_api_key": "OPENAI_API_KEY",
            "anthropic_api_key": "ANTHROPIC_API_KEY",
            "openrouter_api_key": "OPENROUTER_API_KEY",
            "brave_api_key": "BRAVE_API_KEY",
            "github_token": "GITHUB_TOKEN",
            "semantic_scholar_api_key": "SEMANTIC_SCHOLAR_API_KEY",
            "openalex_api_key": "OPENALEX_API_KEY",
            "modal_token_id": "MODAL_TOKEN_ID",
            "modal_token_secret": "MODAL_TOKEN_SECRET",
        }
        env_key = env_key_map.get(key)
        if env_key and isinstance(value, str):
            os.environ[env_key] = value

    return {"ok": True}


@router.delete("/settings/{category}/{key}")
async def delete_setting(
    category: str,
    key: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ops.delete_user_setting(db, user.id, category, key)

    # If a provider key was deleted, check if the current model still has a valid provider
    if category == "providers":
        provider_map = {
            "openai_api_key": "openai",
            "anthropic_api_key": "anthropic",
            "openrouter_api_key": "openrouter",
            "opencode_go_api_key": "opencode-go",
        }
        deleted_provider = provider_map.get(key)
        if deleted_provider:
            agent_settings = await ops.get_user_agent_settings(db, user.id)
            current_model = agent_settings.get("default_model", "")
            # If the user's selected model uses the deleted provider, clear it
            if current_model and deleted_provider in current_model:
                await ops.set_user_setting(db, user.id, "agent", "default_model", "")
                # Also clear from env
                env_key_map = {
                    "openai_api_key": "OPENAI_API_KEY",
                    "anthropic_api_key": "ANTHROPIC_API_KEY",
                    "openrouter_api_key": "OPENROUTER_API_KEY",
                    "opencode_go_api_key": "OPENCODE_GO_API_KEY",
                }
                env_key = env_key_map.get(key)
                if env_key and env_key in os.environ:
                    del os.environ[env_key]

    return {"ok": True}


# ---- Helpers for configured status ----


def _is_provider_configured(provider_id: str, provider_settings: dict) -> bool:
    """Check if a standard provider is configured via env or user setting."""
    env_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "opencode-go": "OPENCODE_GO_API_KEY",
        "ollama": "OLLAMA_API_BASE",
        "lmstudio": "LMSTUDIO_API_BASE",
        "brave": "BRAVE_API_KEY",
        "github": "GITHUB_TOKEN",
        "semantic_scholar": "SEMANTIC_SCHOLAR_API_KEY",
        "openalex": "OPENALEX_API_KEY",
        "modal": "MODAL_TOKEN_ID",
    }
    env_key = env_map.get(provider_id)
    if env_key and os.environ.get(env_key):
        return True
    setting_key = {
        "openai": "openai_api_key",
        "anthropic": "anthropic_api_key",
        "openrouter": "openrouter_api_key",
        "opencode-go": "opencode_go_api_key",
        "ollama": "ollama_api_base",
        "lmstudio": "lmstudio_api_base",
        "brave": "brave_api_key",
        "github": "github_token",
        "semantic_scholar": "semantic_scholar_api_key",
        "openalex": "openalex_api_key",
        "modal": "modal_token_id",
    }.get(provider_id)
    if setting_key and provider_settings.get(setting_key):
        return True
    return False


def _get_custom_providers(provider_settings: dict) -> list[dict]:
    """Extract custom providers from user settings."""
    raw = provider_settings.get("custom_providers")
    if isinstance(raw, list):
        return raw
    return []


# ---- Providers ----


@router.get("/providers")
async def list_providers(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Merge env vars with user settings
    user_settings = await ops.get_all_settings(db, user.id, category="providers")
    provider_settings = user_settings.get("providers", {})

    providers = [
        {
            "id": "openai",
            "name": "OpenAI",
            "key_env": "OPENAI_API_KEY",
            "configured": _is_provider_configured("openai", provider_settings),
            "categories": ["models"],
            "docs_url": "https://platform.openai.com/docs/api-reference",
        },
        {
            "id": "anthropic",
            "name": "Anthropic",
            "key_env": "ANTHROPIC_API_KEY",
            "configured": _is_provider_configured("anthropic", provider_settings),
            "categories": ["models"],
            "docs_url": "https://docs.anthropic.com/en/api/getting-started",
        },
        {
            "id": "openrouter",
            "name": "OpenRouter",
            "key_env": "OPENROUTER_API_KEY",
            "configured": _is_provider_configured("openrouter", provider_settings),
            "categories": ["models"],
            "docs_url": "https://openrouter.ai/docs",
        },
        {
            "id": "opencode-go",
            "name": "OpenCode Go",
            "key_env": "OPENCODE_GO_API_KEY",
            "configured": _is_provider_configured("opencode-go", provider_settings),
            "categories": ["models"],
            "docs_url": "https://go.opencode.ai/docs",
        },
        {
            "id": "ollama",
            "name": "Ollama (Local)",
            "key_env": "OLLAMA_API_BASE",
            "configured": _is_provider_configured("ollama", provider_settings),
            "categories": ["models"],
            "docs_url": "https://ollama.com/docs",
        },
        {
            "id": "lmstudio",
            "name": "LM Studio (Local)",
            "key_env": "LMSTUDIO_API_BASE",
            "configured": _is_provider_configured("lmstudio", provider_settings),
            "categories": ["models"],
            "docs_url": "https://lmstudio.ai/docs",
        },
        {
            "id": "brave",
            "name": "Brave Search",
            "key_env": "BRAVE_API_KEY",
            "configured": _is_provider_configured("brave", provider_settings),
            "categories": ["search"],
            "docs_url": "https://brave.com/search/api/",
        },
        {
            "id": "github",
            "name": "GitHub",
            "key_env": "GITHUB_TOKEN",
            "configured": _is_provider_configured("github", provider_settings),
            "categories": ["papers", "others"],
            "docs_url": "https://docs.github.com/en/rest",
        },
        {
            "id": "semantic_scholar",
            "name": "Semantic Scholar",
            "key_env": "SEMANTIC_SCHOLAR_API_KEY",
            "configured": _is_provider_configured("semantic_scholar", provider_settings),
            "categories": ["papers"],
            "docs_url": "https://api.semanticscholar.org/api-docs/",
        },
        {
            "id": "openalex",
            "name": "OpenAlex",
            "key_env": "OPENALEX_API_KEY",
            "configured": _is_provider_configured("openalex", provider_settings),
            "categories": ["papers"],
            "docs_url": "https://docs.openalex.org/",
        },
        {
            "id": "modal",
            "name": "Modal",
            "key_env": "MODAL_TOKEN_ID",
            "configured": _is_provider_configured("modal", provider_settings),
            "categories": ["compute"],
            "docs_url": "https://modal.com/docs",
        },
    ]

    # Add custom providers
    for cp in _get_custom_providers(provider_settings):
        providers.append(
            {
                "id": cp.get("id", ""),
                "name": cp.get("name", cp.get("id", "")),
                "key_env": f"{cp.get('id', '').upper()}_API_KEY",
                "configured": bool(cp.get("api_key") and cp.get("api_base")),
                "categories": ["models"],
                "docs_url": cp.get("api_base", ""),
                "is_custom": True,
                "sdk_type": cp.get("sdk_type", "openai-sdk"),
                "api_base": cp.get("api_base", ""),
            }
        )

    return {"providers": providers}


# ---- App Status (model, config) ----


@router.get("/status")
async def get_status(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return current model and app state for frontend init."""
    config = request.app.state.config
    user_settings = await ops.get_all_settings(db, user.id, category="agent")
    agent_settings = user_settings.get("agent", {})

    # User's explicitly selected model, or fall back to auto-detected
    user_model = agent_settings.get("default_model") or None
    effective_model = user_model or config.model_name

    # Only need onboarding if no providers are configured at all
    # (i.e., auto-detection also failed to find anything useful)
    has_any_provider = any(
        [
            os.environ.get("ANTHROPIC_API_KEY"),
            os.environ.get("OPENAI_API_KEY"),
            os.environ.get("OPENROUTER_API_KEY"),
            os.environ.get("OPENCODE_GO_API_KEY"),
            os.environ.get("OLLAMA_API_BASE"),
            os.environ.get("LMSTUDIO_API_BASE"),
        ]
    )
    # Check user-configured providers too
    if not has_any_provider:
        user_providers = await ops.get_all_settings(db, user.id, category="providers")
        prov = user_providers.get("providers", {})
        has_any_provider = any(v for v in prov.values() if v)
        # Also check custom providers
        if not has_any_provider:
            custom = _get_custom_providers(prov)
            has_any_provider = any(bool(cp.get("api_key") and cp.get("api_base")) for cp in custom)

    return {
        "model": effective_model,
        "research_model": agent_settings.get("research_model") or config.research_model,
        "yolo_mode": agent_settings.get("yolo_mode", config.yolo_mode),
        "needs_onboarding": not has_any_provider,
    }


# ---- Models ----


# Standard fallback models (used when models.dev is unreachable)
_FALLBACK_MODELS = [
    {"id": "openai/gpt-4o", "name": "GPT-4o", "provider": "openai", "release_date": "2024-05-13"},
    {
        "id": "openai/gpt-4o-mini",
        "name": "GPT-4o Mini",
        "provider": "openai",
        "release_date": "2024-07-18",
    },
    {"id": "openai/o3-mini", "name": "o3-mini", "provider": "openai", "release_date": "2025-01-31"},
    {
        "id": "anthropic/claude-sonnet-4-20250514",
        "name": "Claude Sonnet 4",
        "provider": "anthropic",
        "release_date": "2025-05-14",
    },
    {
        "id": "anthropic/claude-opus-4-20250514",
        "name": "Claude Opus 4",
        "provider": "anthropic",
        "release_date": "2025-05-14",
    },
    {
        "id": "anthropic/claude-haiku-4-20250514",
        "name": "Claude Haiku 4",
        "provider": "anthropic",
        "release_date": "2025-05-14",
    },
    {
        "id": "openrouter/openai/gpt-4o",
        "name": "OpenRouter GPT-4o",
        "provider": "openrouter",
        "release_date": "2024-05-13",
    },
    {
        "id": "openrouter/anthropic/claude-sonnet-4",
        "name": "OR Claude Sonnet",
        "provider": "openrouter",
        "release_date": "2025-05-14",
    },
    {
        "id": "openrouter/google/gemini-2.5-pro",
        "name": "OR Gemini 2.5 Pro",
        "provider": "openrouter",
        "release_date": "2025-03-25",
    },
    {
        "id": "openrouter/google/gemini-2.5-flash",
        "name": "OR Gemini 2.5 Flash",
        "provider": "openrouter",
        "release_date": "2025-04-15",
    },
]

# OpenCode Go models
_OPENCODE_GO_MODELS = [
    {
        "id": "opencode-go/glm-5.1",
        "name": "GLM-5.1",
        "provider": "opencode-go",
        "release_date": "2025-04-01",
    },
    {
        "id": "opencode-go/glm-5",
        "name": "GLM-5",
        "provider": "opencode-go",
        "release_date": "2025-03-01",
    },
    {
        "id": "opencode-go/kimi-k2.6",
        "name": "Kimi K2.6",
        "provider": "opencode-go",
        "release_date": "2025-04-20",
    },
    {
        "id": "opencode-go/kimi-k2.5",
        "name": "Kimi K2.5",
        "provider": "opencode-go",
        "release_date": "2025-03-15",
    },
    {
        "id": "opencode-go/deepseek-v4-pro",
        "name": "DeepSeek V4 Pro",
        "provider": "opencode-go",
        "release_date": "2025-04-10",
    },
    {
        "id": "opencode-go/deepseek-v4-flash",
        "name": "DeepSeek V4 Flash",
        "provider": "opencode-go",
        "release_date": "2025-04-10",
    },
    {
        "id": "opencode-go/mimo-v2.5-pro",
        "name": "MiMo-V2.5-Pro",
        "provider": "opencode-go",
        "release_date": "2025-03-20",
    },
    {
        "id": "opencode-go/mimo-v2.5",
        "name": "MiMo-V2.5",
        "provider": "opencode-go",
        "release_date": "2025-03-20",
    },
    {
        "id": "opencode-go/minimax-m2.7",
        "name": "MiniMax M2.7",
        "provider": "opencode-go",
        "release_date": "2025-04-05",
    },
    {
        "id": "opencode-go/minimax-m2.5",
        "name": "MiniMax M2.5",
        "provider": "opencode-go",
        "release_date": "2025-03-10",
    },
    {
        "id": "opencode-go/qwen3.6-plus",
        "name": "Qwen3.6 Plus",
        "provider": "opencode-go",
        "release_date": "2025-04-15",
    },
    {
        "id": "opencode-go/qwen3.5-plus",
        "name": "Qwen3.5 Plus",
        "provider": "opencode-go",
        "release_date": "2025-03-01",
    },
]


async def _fetch_models_dev() -> list[dict]:
    """Fetch models from models.dev and return flat list with provider info."""
    models = []
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://models.dev/api.json", timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                for provider_id, provider_data in data.items():
                    if not isinstance(provider_data, dict):
                        continue
                    provider_models = provider_data.get("models", {})
                    if isinstance(provider_models, dict):
                        for model_id, model_info in provider_models.items():
                            if not isinstance(model_info, dict):
                                continue
                            release_date = model_info.get("release_date", "")
                            # Skip entries without a release date (not real models)
                            if not release_date:
                                continue
                            models.append(
                                {
                                    "id": f"{provider_id}/{model_id}",
                                    "name": model_info.get("name", model_id),
                                    "provider": provider_id,
                                    "release_date": release_date,
                                }
                            )
    except Exception:
        pass
    return models


@router.get("/models")
async def list_models(
    request: Request,
    provider: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List available LLM models from configured providers.

    If `provider` is specified, only return models for that provider.
    Otherwise return models from all configured providers.
    """
    # Get user's provider settings to check what's configured
    user_settings = await ops.get_all_settings(db, user.id, category="providers")
    provider_settings = user_settings.get("providers", {})

    # Determine which providers are configured
    configured_providers = set()
    for pid in ["openai", "anthropic", "openrouter", "opencode-go", "ollama", "lmstudio"]:
        if _is_provider_configured(pid, provider_settings):
            configured_providers.add(pid)

    # Add custom providers
    custom_providers = _get_custom_providers(provider_settings)
    for cp in custom_providers:
        if cp.get("api_key") and cp.get("api_base"):
            configured_providers.add(cp.get("id", ""))

    # If a specific provider is requested, only use that one
    target_providers = {provider} if provider else configured_providers

    # Fetch from models.dev
    all_models = await _fetch_models_dev()

    # Filter to target providers
    models = [m for m in all_models if m.get("provider") in target_providers]

    # If models.dev failed or returned nothing, use fallbacks
    if not models:
        fallback = []
        for m in _FALLBACK_MODELS:
            if not provider or m["provider"] == provider:
                if m["provider"] in configured_providers:
                    fallback.append(m)
        for m in _OPENCODE_GO_MODELS:
            if not provider or m["provider"] == provider:
                if m["provider"] in configured_providers:
                    fallback.append(m)
        models = fallback
    else:
        # Add fallback models for providers not in models.dev response
        # or for when models.dev is missing some providers
        existing_ids = {m["id"] for m in models}
        for m in _FALLBACK_MODELS:
            if m["id"] not in existing_ids:
                if (not provider or m["provider"] == provider) and m[
                    "provider"
                ] in configured_providers:
                    models.append(m)
        for m in _OPENCODE_GO_MODELS:
            if m["id"] not in existing_ids:
                if (not provider or m["provider"] == provider) and m[
                    "provider"
                ] in configured_providers:
                    models.append(m)

    # Add local model placeholders if configured
    if "ollama" in configured_providers and (not provider or provider == "ollama"):
        ollama_model = os.environ.get("OLLAMA_MODEL", "llama3.1")
        if not any(m["id"] == f"ollama/{ollama_model}" for m in models):
            models.append(
                {
                    "id": f"ollama/{ollama_model}",
                    "name": f"Ollama: {ollama_model}",
                    "provider": "ollama",
                    "release_date": "",
                }
            )
        for m in [
            "llama3.1",
            "llama3.2",
            "qwen2.5-coder",
            "codellama",
            "deepseek-coder-v2",
            "mistral",
        ]:
            if not any(x["id"] == f"ollama/{m}" for x in models):
                models.append(
                    {
                        "id": f"ollama/{m}",
                        "name": f"Ollama: {m}",
                        "provider": "ollama",
                        "release_date": "",
                    }
                )

    if "lmstudio" in configured_providers and (not provider or provider == "lmstudio"):
        if not any(m["id"] == "lmstudio/default" for m in models):
            models.append(
                {
                    "id": "lmstudio/default",
                    "name": "LM Studio (default)",
                    "provider": "lmstudio",
                    "release_date": "",
                }
            )

    # Add custom provider cached models
    for cp in custom_providers:
        cp_id = cp.get("id", "")
        if cp_id not in configured_providers:
            continue
        if provider and cp_id != provider:
            continue
        for cm in cp.get("models", []):
            model_entry = {
                "id": f"{cp_id}/{cm.get('id', cm.get('modelId', ''))}",
                "name": cm.get("name", cm.get("id", "")),
                "provider": cp_id,
                "release_date": cm.get("release_date", ""),
            }
            if not any(m["id"] == model_entry["id"] for m in models):
                models.append(model_entry)

    # Get recent models
    agent_settings = await ops.get_user_agent_settings(db, user.id)
    recent_model_ids = agent_settings.get("recent_models", [])
    if not isinstance(recent_model_ids, list):
        recent_model_ids = []

    # Build recent model entries (preserve order, most recent first)
    recent_models = []
    seen_recent = set()
    for mid in recent_model_ids[:10]:
        if mid in seen_recent:
            continue
        seen_recent.add(mid)
        # Find model info from the full list
        model_info = None
        for m in models:
            if m["id"] == mid:
                model_info = m
                break
        if model_info:
            recent_models.append(model_info)

    # Sort models by release_date descending within each provider
    def _sort_key(m):
        rd = m.get("release_date", "")
        # Use a very old date for models without release_date so they sort to bottom
        return (m.get("provider", ""), rd if rd else "1900-01-01")

    models.sort(key=_sort_key, reverse=True)
    # Actually reverse sort needs to be per-provider. Let's do a stable sort.
    # Sort by provider first, then by release_date descending
    models.sort(
        key=lambda m: (m.get("provider", ""), m.get("release_date", "1900-01-01")), reverse=False
    )
    # Hmm, this won't work for reverse per-field. Let's use two sorts.
    models.sort(key=lambda m: m.get("release_date", "1900-01-01"), reverse=True)
    models.sort(key=lambda m: m.get("provider", ""))

    return {
        "models": models,
        "recent_models": recent_models[:5],
    }


# ---- Custom Provider Model Fetching ----


@router.post("/providers/{provider_id}/fetch-models")
async def fetch_custom_provider_models(
    provider_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch models from a custom provider's API and cache them."""
    user_settings = await ops.get_all_settings(db, user.id, category="providers")
    provider_settings = user_settings.get("providers", {})

    custom_providers = _get_custom_providers(provider_settings)
    cp = None
    for c in custom_providers:
        if c.get("id") == provider_id:
            cp = c
            break

    if not cp:
        raise HTTPException(status_code=404, detail="Custom provider not found")

    sdk_type = cp.get("sdk_type", "openai-sdk")
    api_base = cp.get("api_base", "").rstrip("/")
    api_key = cp.get("api_key", "")

    if not api_base or not api_key:
        raise HTTPException(status_code=400, detail="Provider missing api_base or api_key")

    fetched_models = []

    if sdk_type in ("openai-sdk", "openrouter", "litellm"):
        # OpenAI-compatible /models endpoint
        try:
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {api_key}"}
                resp = await client.get(f"{api_base}/models", headers=headers, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    for m in data.get("data", []):
                        if isinstance(m, dict):
                            fetched_models.append(
                                {
                                    "id": m.get("id", ""),
                                    "name": m.get("id", ""),  # OpenAI /models usually only has id
                                    "release_date": "",
                                }
                            )
                else:
                    raise HTTPException(
                        status_code=502, detail=f"Provider returned {resp.status_code}"
                    )
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Failed to reach provider: {str(e)}")
    elif sdk_type == "anthropic-sdk":
        # Anthropic doesn't expose a models list API
        # Return empty list — user will need to add models manually
        pass
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported sdk_type: {sdk_type}")

    # Update the custom provider with fetched models
    for i, c in enumerate(custom_providers):
        if c.get("id") == provider_id:
            custom_providers[i]["models"] = fetched_models
            custom_providers[i]["last_fetched_at"] = datetime.now(UTC).isoformat()
            break

    await ops.set_user_setting(db, user.id, "providers", "custom_providers", custom_providers)

    return {"models": fetched_models}


# ---- Config (legacy .env writing — for backward compat) ----


@router.post("/config")
async def save_config(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save API keys — both to user settings and to process env."""
    # Whitelist of allowed environment variables to set
    ALLOWED_ENV_KEYS = {
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "OPENROUTER_API_KEY",
        "OPENCODE_GO_API_KEY",
        "BRAVE_API_KEY",
        "GITHUB_TOKEN",
        "SEMANTIC_SCHOLAR_API_KEY",
        "OPENALEX_API_KEY",
        "MODAL_TOKEN_ID",
        "MODAL_TOKEN_SECRET",
    }

    body = await request.json()

    for key, value in body.items():
        if isinstance(value, str) and value:
            # Only allow setting whitelisted environment variables
            if key in ALLOWED_ENV_KEYS:
                os.environ[key] = value
            # Save as user setting regardless (stored in DB, not env)
            setting_key = key.lower()
            await ops.set_user_setting(db, user.id, "providers", setting_key, value)

    return {"ok": True}
