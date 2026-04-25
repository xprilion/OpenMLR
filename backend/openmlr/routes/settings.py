"""Settings routes — user settings, provider config, model management."""

import os
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.engine import get_db
from ..db.models import User
from ..db import operations as ops
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
    return {"ok": True}


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
            "configured": bool(os.environ.get("OPENAI_API_KEY") or provider_settings.get("openai_api_key")),
        },
        {
            "id": "anthropic",
            "name": "Anthropic",
            "key_env": "ANTHROPIC_API_KEY",
            "configured": bool(os.environ.get("ANTHROPIC_API_KEY") or provider_settings.get("anthropic_api_key")),
        },
        {
            "id": "openrouter",
            "name": "OpenRouter",
            "key_env": "OPENROUTER_API_KEY",
            "configured": bool(os.environ.get("OPENROUTER_API_KEY") or provider_settings.get("openrouter_api_key")),
        },
        {
            "id": "opencode-go",
            "name": "OpenCode Go",
            "key_env": "OPENCODE_GO_API_KEY",
            "configured": bool(os.environ.get("OPENCODE_GO_API_KEY") or provider_settings.get("opencode_go_api_key")),
        },
        {
            "id": "ollama",
            "name": "Ollama (Local)",
            "key_env": "OLLAMA_API_BASE",
            "configured": bool(os.environ.get("OLLAMA_API_BASE") or provider_settings.get("ollama_api_base")),
        },
        {
            "id": "lmstudio",
            "name": "LM Studio (Local)",
            "key_env": "LMSTUDIO_API_BASE",
            "configured": bool(os.environ.get("LMSTUDIO_API_BASE") or provider_settings.get("lmstudio_api_base")),
        },
        {
            "id": "brave",
            "name": "Brave Search",
            "key_env": "BRAVE_API_KEY",
            "configured": bool(os.environ.get("BRAVE_API_KEY") or provider_settings.get("brave_api_key")),
        },
        {
            "id": "github",
            "name": "GitHub",
            "key_env": "GITHUB_TOKEN",
            "configured": bool(os.environ.get("GITHUB_TOKEN") or provider_settings.get("github_token")),
        },
        {
            "id": "semantic_scholar",
            "name": "Semantic Scholar",
            "key_env": "SEMANTIC_SCHOLAR_API_KEY",
            "configured": bool(os.environ.get("SEMANTIC_SCHOLAR_API_KEY") or provider_settings.get("semantic_scholar_api_key")),
        },
        {
            "id": "modal",
            "name": "Modal",
            "key_env": "MODAL_TOKEN_ID",
            "configured": bool(os.environ.get("MODAL_TOKEN_ID") or provider_settings.get("modal_token_id")),
        },
    ]
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

    # User's preferred model > config auto-detected model
    current_model = agent_settings.get("default_model") or config.model_name
    return {
        "model": current_model,
        "research_model": agent_settings.get("research_model") or config.research_model,
        "yolo_mode": agent_settings.get("yolo_mode", config.yolo_mode),
    }


# ---- Models ----

@router.get("/models")
async def list_models():
    """List available LLM models."""
    models = []
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://models.dev/api/v1/models", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data.get("models"), list):
                    models = [
                        {
                            "id": m.get("id", m.get("modelId", "")),
                            "name": m.get("name", m.get("id", "")),
                            "provider": m.get("provider", "unknown"),
                        }
                        for m in data["models"]
                    ]
    except Exception:
        pass

    if not models:
        models = [
            {"id": "openai/gpt-4o", "name": "GPT-4o", "provider": "openai"},
            {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini", "provider": "openai"},
            {"id": "openai/o3-mini", "name": "o3-mini", "provider": "openai"},
            {"id": "anthropic/claude-sonnet-4", "name": "Claude Sonnet 4", "provider": "anthropic"},
            {"id": "anthropic/claude-opus-4", "name": "Claude Opus 4", "provider": "anthropic"},
            {"id": "anthropic/claude-haiku-4", "name": "Claude Haiku 4", "provider": "anthropic"},
            {"id": "openrouter/openai/gpt-4o", "name": "OpenRouter GPT-4o", "provider": "openrouter"},
            {"id": "openrouter/anthropic/claude-sonnet-4", "name": "OR Claude Sonnet", "provider": "openrouter"},
            {"id": "openrouter/google/gemini-2.5-pro", "name": "OR Gemini 2.5 Pro", "provider": "openrouter"},
            {"id": "openrouter/google/gemini-2.5-flash", "name": "OR Gemini 2.5 Flash", "provider": "openrouter"},
        ]
    
    # Add OpenCode Go models
    opencode_go_models = [
        {"id": "opencode-go/glm-5.1", "name": "GLM-5.1", "provider": "opencode-go"},
        {"id": "opencode-go/glm-5", "name": "GLM-5", "provider": "opencode-go"},
        {"id": "opencode-go/kimi-k2.6", "name": "Kimi K2.6", "provider": "opencode-go"},
        {"id": "opencode-go/kimi-k2.5", "name": "Kimi K2.5", "provider": "opencode-go"},
        {"id": "opencode-go/deepseek-v4-pro", "name": "DeepSeek V4 Pro", "provider": "opencode-go"},
        {"id": "opencode-go/deepseek-v4-flash", "name": "DeepSeek V4 Flash", "provider": "opencode-go"},
        {"id": "opencode-go/mimo-v2.5-pro", "name": "MiMo-V2.5-Pro", "provider": "opencode-go"},
        {"id": "opencode-go/mimo-v2.5", "name": "MiMo-V2.5", "provider": "opencode-go"},
        {"id": "opencode-go/minimax-m2.7", "name": "MiniMax M2.7", "provider": "opencode-go"},
        {"id": "opencode-go/minimax-m2.5", "name": "MiniMax M2.5", "provider": "opencode-go"},
        {"id": "opencode-go/qwen3.6-plus", "name": "Qwen3.6 Plus", "provider": "opencode-go"},
        {"id": "opencode-go/qwen3.5-plus", "name": "Qwen3.5 Plus", "provider": "opencode-go"},
    ]
    models.extend(opencode_go_models)
    
    # Add local model placeholders if configured
    if os.environ.get("OLLAMA_API_BASE"):
        ollama_model = os.environ.get("OLLAMA_MODEL", "llama3.1")
        models.append({"id": f"ollama/{ollama_model}", "name": f"Ollama: {ollama_model}", "provider": "ollama"})
        # Common Ollama models
        for m in ["llama3.1", "llama3.2", "qwen2.5-coder", "codellama", "deepseek-coder-v2", "mistral"]:
            if m != ollama_model:
                models.append({"id": f"ollama/{m}", "name": f"Ollama: {m}", "provider": "ollama"})
    
    if os.environ.get("LMSTUDIO_API_BASE"):
        models.append({"id": "lmstudio/default", "name": "LM Studio (default)", "provider": "lmstudio"})
    
    return {"models": models}


# ---- Config (legacy .env writing — for backward compat) ----

@router.post("/config")
async def save_config(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save API keys — both to user settings and to process env."""
    body = await request.json()

    for key, value in body.items():
        if isinstance(value, str) and value:
            os.environ[key] = value
            # Also save as user setting
            setting_key = key.lower()
            await ops.set_user_setting(db, user.id, "providers", setting_key, value)

    return {"ok": True}
