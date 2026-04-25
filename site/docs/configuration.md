# Configuration

## Environment Variables (`.env`)

```bash
# ── Database (required) ──
DATABASE_URL="postgresql://user:pass@localhost:5432/openmlr"

# ── LLM providers (at least one required) ──
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OPENROUTER_API_KEY=sk-or-...

# ── Local models (OpenAI-compatible APIs) ──
# Ollama
OLLAMA_API_BASE=http://localhost:11434/v1
OLLAMA_MODEL=llama3.1

# LM Studio
LMSTUDIO_API_BASE=http://localhost:1234/v1
LMSTUDIO_MODEL=default

# Any OpenAI-compatible API (vLLM, TGI, etc.)
LOCAL_API_BASE=http://localhost:8000/v1
LOCAL_MODEL=local/my-model
LOCAL_API_KEY=not-needed

# ── Background jobs (optional) ──
REDIS_URL=redis://localhost:6379/0
USE_BACKGROUND_JOBS=true
USE_REDIS_PUBSUB=true

# ── Search & research (optional) ──
BRAVE_API_KEY=...                    # web search
OPENALEX_EMAIL=you@example.com       # polite pool (no key needed)

# ── GitHub (optional) ──
GITHUB_TOKEN=ghp_...                 # improves code search rate limits

# ── Auth ──
JWT_SECRET_KEY=change-me-in-production

# ── Docker execution ──
OPEN_MLR_DOCKER_IMAGE=python:3.12-slim  # default container image

# ── Modal sandbox (optional) ──
MODAL_TOKEN_ID=...
MODAL_TOKEN_SECRET=...
```

## Per-User Settings

After login, click the gear icon in the sidebar to open Settings:

| Tab | What you can configure |
|-----|----------------------|
| **Providers** | API keys for all services (stored encrypted in DB, override .env) |
| **Agent** | Default model, research model, YOLO mode |
| **Sandbox** | Default execution environment (local/SSH/Modal), Modal credentials |
| **Writing** | Citation style (APA/IEEE/ACM/Chicago), export format |

## Model Selection

Models are auto-detected based on which API keys/URLs are configured:

### Cloud Providers

| Key set | Default model |
|---------|--------------|
| `ANTHROPIC_API_KEY` | `anthropic/claude-sonnet-4` |
| `OPENAI_API_KEY` | `openai/gpt-4o` |
| `OPENROUTER_API_KEY` | `openrouter/anthropic/claude-sonnet-4` |

### Local Models

| Config | Model prefix |
|--------|-------------|
| `OLLAMA_MODEL` | `ollama/llama3.1` |
| `LMSTUDIO_API_BASE` | `lmstudio/default` |
| `LOCAL_API_BASE` | `local/my-model` |

Override via Settings > Agent > Default Model, or by clicking the model
button in the header.

## Local Model Setup

### Ollama

```bash
# Install and start Ollama
ollama serve

# Pull a model
ollama pull llama3.1

# Configure
OLLAMA_MODEL=llama3.1
# OLLAMA_API_BASE defaults to http://localhost:11434/v1
```

Use as `ollama/llama3.1` in the model selector.

### LM Studio

1. Download and install [LM Studio](https://lmstudio.ai)
2. Load a model and start the server
3. Configure:
```bash
LMSTUDIO_API_BASE=http://localhost:1234/v1
LMSTUDIO_MODEL=default
```

Use as `lmstudio/default` in the model selector.

### vLLM / text-generation-inference / Other

Any server that exposes an OpenAI-compatible `/v1/chat/completions` endpoint:

```bash
LOCAL_API_BASE=http://localhost:8000/v1
LOCAL_MODEL=local/my-model-name
LOCAL_API_KEY=not-needed   # or your auth token
```

Use as `local/my-model-name` in the model selector.

## Background Jobs

Enable persistent task tracking that survives browser refreshes:

```bash
REDIS_URL=redis://localhost:6379/0
USE_BACKGROUND_JOBS=true
USE_REDIS_PUBSUB=true
```

When enabled:
- Tasks and resources persist to the database
- Agent processing continues even if you close the browser
- Reconnecting shows full progress history
- Multiple browser tabs receive live updates via Redis pub/sub

Requires a running Redis server. Use `make infra` to start one with Docker.

## Agent Config File

`backend/configs/agent_config.yaml` controls defaults:

```yaml
model_name: ""              # empty = auto-detect
max_iterations: 300
stream: true
paper_search_budget: 25     # API calls per session
require_plan_approval: true
```
