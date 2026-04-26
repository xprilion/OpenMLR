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
OLLAMA_API_BASE=http://localhost:11434/v1
OLLAMA_MODEL=llama3.1

LMSTUDIO_API_BASE=http://localhost:1234/v1
LMSTUDIO_MODEL=default

LOCAL_API_BASE=http://localhost:8000/v1
LOCAL_MODEL=local/my-model
LOCAL_API_KEY=not-needed

# ── Background jobs (optional, recommended) ──
REDIS_URL=redis://localhost:6379/0
USE_BACKGROUND_JOBS=true
USE_REDIS_PUBSUB=true

# ── Search & research (optional) ──
BRAVE_API_KEY=...
OPENALEX_EMAIL=you@example.com

# ── GitHub (optional) ──
GITHUB_TOKEN=ghp_...

# ── Auth ──
JWT_SECRET_KEY=change-me-in-production

# ── Docker execution ──
OPEN_MLR_DOCKER_IMAGE=python:3.12-slim

# ── Modal sandbox (optional) ──
MODAL_TOKEN_ID=...
MODAL_TOKEN_SECRET=...
```

## Settings Pages

Settings are routed pages (not a modal), accessible from the sidebar:

| Route | What you configure |
|-------|-------------------|
| `/settings/providers` | API keys for LLM providers and services. Stored encrypted in DB, override `.env` values. |
| `/settings/agent` | Default model, research model, YOLO mode, max iterations. |
| `/settings/sandbox` | Default execution environment (Docker/SSH/Modal), Modal credentials. |
| `/settings/writing` | Citation style (APA/IEEE/ACM/Chicago), export format preferences. |

## Sticky Model Selection

The selected model is persisted per-user in the database. When you switch models via the header dropdown, the choice sticks across sessions, devices, and browser refreshes. No need to re-select every time.

## Model Selection

Models are auto-detected based on which API keys/URLs are configured:

| Key set | Example model |
|---------|--------------|
| `ANTHROPIC_API_KEY` | `anthropic/claude-sonnet-4` |
| `OPENAI_API_KEY` | `openai/gpt-4o` |
| `OPENROUTER_API_KEY` | `openrouter/anthropic/claude-sonnet-4` |
| `OLLAMA_MODEL` | `ollama/llama3.1` |
| `LMSTUDIO_API_BASE` | `lmstudio/default` |
| `LOCAL_API_BASE` | `local/my-model` |

Override via `/settings/agent` or the model dropdown in the header.

## Background Jobs

Enable with Redis for persistent processing:

```bash
REDIS_URL=redis://localhost:6379/0
USE_BACKGROUND_JOBS=true
USE_REDIS_PUBSUB=true
```

When enabled:
- Agent processing continues even if you close the browser
- Multiple conversations process in parallel via Celery workers
- Redis pub/sub relays events from workers to SSE clients
- Redis-based interrupt relay actually kills running worker tasks
- Reconnecting via SSE catches up on missed events

Requires a running Redis server. Use `make infra` to start one with Docker.

## Agent Config

`backend/configs/agent_config.yaml` controls defaults:

```yaml
model_name: ""              # empty = auto-detect
max_iterations: 300
stream: true
paper_search_budget: 25
require_plan_approval: true
```

These can be overridden per-user via `/settings/agent`.
