---
title: Configuration - OpenMLR
description: Configure OpenMLR environment variables, LLM providers (OpenAI, Anthropic, OpenRouter, Ollama), API keys, and runtime settings.
---

# Configuration

OpenMLR can be configured via environment variables (`.env` file) or through the Settings UI after login.

## Environment Variables

### Required vs Optional

::: info Key point
**No environment variables are strictly required to start OpenMLR.** The app will start and guide you through configuration via the onboarding flow.

However, for the app to be **functional**, you need:
1. A database connection (auto-configured in Docker)
2. At least one LLM provider API key (configurable via UI)
:::

### Variable Categories

| Category | Required to Start? | Can Configure via UI? |
|----------|-------------------|----------------------|
| [Database](#database) | Yes (auto in Docker) | No |
| [Security](#security) | Auto-generated in dev | No |
| [LLM Providers](#llm-providers) | No | **Yes** |
| [Development](#development) | No | No |
| [Background Jobs](#background-jobs) | No | No |
| [Tools & Integrations](#tools-integrations) | No | **Yes** |
| [Sandbox](#sandbox) | No | Partial |

---

## Database

Required for the app to function, but **auto-configured when using Docker Compose**.

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | See below | PostgreSQL connection string |

**Docker Compose default:**
```
postgresql+asyncpg://openmlr:openmlr@db:5432/openmlr
```

**Local development:**
```bash
DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/openmlr"
```

---

## Security

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET_KEY` | Auto-generated in dev | Secret for signing auth tokens |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Allowed CORS origins |
| `ENVIRONMENT` | `development` | `development` or `production` |

::: warning Production
In production, always set a strong `JWT_SECRET_KEY`:
```bash
JWT_SECRET_KEY=$(openssl rand -hex 32)
```
:::

---

## LLM Providers

**All LLM keys are optional at startup.** Configure via **Settings > Providers** in the UI, or set in `.env`.

::: tip UI Configuration
API keys set via the Settings UI are stored encrypted in the database and take precedence over `.env` values. This is the recommended approach.
:::

### Cloud Providers

| Variable | Provider | Get Key |
|----------|----------|---------|
| `OPENAI_API_KEY` | OpenAI | [platform.openai.com](https://platform.openai.com) |
| `ANTHROPIC_API_KEY` | Anthropic | [console.anthropic.com](https://console.anthropic.com) |
| `OPENROUTER_API_KEY` | OpenRouter | [openrouter.ai](https://openrouter.ai) |
| `OPENCODE_GO_API_KEY` | OpenCode Go | [opencode.ai](https://opencode.ai/auth) |

### Local Models

For self-hosted models with OpenAI-compatible APIs:

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_API_BASE` | `http://localhost:11434/v1` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.1` | Default Ollama model |
| `LMSTUDIO_API_BASE` | `http://localhost:1234/v1` | LM Studio server URL |
| `LMSTUDIO_MODEL` | `default` | Default LM Studio model |
| `LOCAL_API_BASE` | `http://localhost:8000/v1` | Custom OpenAI-compatible API |
| `LOCAL_MODEL` | `local/default` | Custom model name |
| `LOCAL_API_KEY` | `not-needed` | API key if required |

### Custom Providers

You can add custom OpenAI-compatible or Anthropic-compatible providers via **Settings > Providers > Add Custom Provider**. Each custom provider requires:

| Field | Description |
|-------|-------------|
| Display Name | Human-readable name shown in the model picker |
| Provider ID | Prefix for model IDs (e.g., `my-org` makes models like `my-org/model-name`) |
| SDK Type | `OpenAI SDK`, `Anthropic SDK`, `OpenRouter`, or `LiteLLM` |
| API Base URL | The provider's API endpoint |
| API Key | Authentication key |

After saving, use the **Fetch Models** button to retrieve the provider's model list via its `/models` endpoint. Fetched models appear in the model picker alongside standard providers.

### Model Selection

Models are auto-detected based on configured keys. The model picker shows:
- **Recently used models** (top 5) for quick access
- **Models grouped by provider** with logos, sorted by release date (newest first)
- Live model lists from [models.dev](https://models.dev) for standard providers

Override in **Settings > Agent** or the model dropdown.

| Key Present | Example Model |
|-------------|---------------|
| `ANTHROPIC_API_KEY` | `anthropic/claude-sonnet-4` |
| `OPENAI_API_KEY` | `openai/gpt-4o` |
| `OPENROUTER_API_KEY` | `openrouter/anthropic/claude-sonnet-4` |
| `OLLAMA_MODEL` | `ollama/llama3.1` |

---

## Development

| Variable | Default | Description |
|----------|---------|-------------|
| `DEV_MODE` | `false` | Enables Swagger UI at `/docs`, disables static frontend serving |

When `DEV_MODE=true`:
- Swagger UI is available at `http://localhost:3000/docs`
- ReDoc is available at `http://localhost:3000/redoc`
- The root URL (`/`) redirects to `/docs`
- The static frontend bundle is **not** served (use Vite dev server on port 5173 instead)

This is auto-set in Docker development mode (`docker-compose.yml`).

---

## Background Jobs

Enable persistent processing that survives browser refreshes. **Auto-configured in Docker Compose.**

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `USE_BACKGROUND_JOBS` | `false` | Enable Celery workers |
| `USE_REDIS_PUBSUB` | `false` | Enable Redis pub/sub for SSE |

When enabled:
- Agent continues processing if you close the browser
- Multiple conversations process in parallel
- Interrupt commands actually kill running worker tasks
- SSE reconnection catches up on missed events

---

## Tools & Integrations

**All optional.** Configure via **Settings > Providers** in the UI.

| Variable | Service | Description |
|----------|---------|-------------|
| `BRAVE_API_KEY` | Brave Search | Web search capability |
| `GITHUB_TOKEN` | GitHub | Repository access, code search |
| `OPENALEX_API_KEY` | OpenAlex | Optional API key for higher rate limits |
| `SEMANTIC_SCHOLAR_API_KEY` | Semantic Scholar | API key for paper search with abstracts |

::: tip Research tools work without keys
Paper search (OpenAlex, arXiv, CrossRef) works without any API keys. API keys just provide higher rate limits.
:::

---

## Sandbox

Controls how the agent executes code.

| Variable | Default | Description |
|----------|---------|-------------|
| `OPEN_MLR_DOCKER_IMAGE` | `python:3.12-slim` | Docker image for sandboxed execution |
| `OPENMLR_ALLOW_DIRECT_EXEC` | `false` | Allow host execution (security risk) |
| `OPENMLR_WORKSPACE_ROOT` | Current directory | Base path for file operations |
| `MODAL_TOKEN_ID` | - | Modal.com token ID |
| `MODAL_TOKEN_SECRET` | - | Modal.com token secret |

---

## MCP Servers

OpenMLR supports the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) for connecting external tools. Configure MCP servers in **Settings > MCP Servers**.

### Adding an MCP Server

1. Go to **Settings > MCP Servers**
2. Click **Add Server**
3. Enter a unique server name
4. Configure the transport:
   - **HTTP**: Enter the server URL (e.g., `http://localhost:8080/mcp`)
   - **stdio**: Enter the command and arguments (e.g., `npx -y @anthropic/mcp-server-filesystem /path/to/dir`)

### Example Configuration

**HTTP server:**
```
Name: my-tools
Transport: HTTP
URL: http://localhost:3001/mcp
```

**stdio server (filesystem access):**
```
Name: filesystem
Transport: stdio
Command: npx
Arguments: -y, @anthropic/mcp-server-filesystem, /Users/me/projects
```

MCP servers are connected when you start a new session. Tools from connected servers appear alongside built-in tools.

---

## Settings Pages

Settings are accessible from the sidebar after login:

| Route | What You Configure |
|-------|-------------------|
| `/settings/providers` | API keys for LLM providers and tools |
| `/settings/agent` | Default model, research model, max iterations |
| `/settings/sandbox` | Execution environment (Docker/SSH/Modal) |
| `/settings/writing` | Citation style, export format |
| `/settings/mcp` | MCP server connections |

---

## Full `.env` Example

```bash
# ═══════════════════════════════════════════════════════════
# REQUIRED FOR LOCAL DEVELOPMENT (auto-configured in Docker)
# ═══════════════════════════════════════════════════════════

DATABASE_URL="postgresql+asyncpg://openmlr:openmlr@localhost:5432/openmlr"
JWT_SECRET_KEY=change-me-in-production

# ═══════════════════════════════════════════════════════════
# LLM PROVIDERS (configure at least one - via .env or UI)
# ═══════════════════════════════════════════════════════════

# Cloud providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OPENROUTER_API_KEY=sk-or-...

# Local models
# OLLAMA_API_BASE=http://localhost:11434/v1
# OLLAMA_MODEL=llama3.1

# ═══════════════════════════════════════════════════════════
# BACKGROUND JOBS (optional, auto-configured in Docker)
# ═══════════════════════════════════════════════════════════

REDIS_URL=redis://localhost:6379/0
USE_BACKGROUND_JOBS=true
USE_REDIS_PUBSUB=true

# ═══════════════════════════════════════════════════════════
# TOOLS (optional - configure via UI or here)
# ═══════════════════════════════════════════════════════════

BRAVE_API_KEY=...
GITHUB_TOKEN=ghp_...
```

---

## Agent Configuration

`backend/configs/agent_config.yaml` controls agent defaults:

```yaml
model_name: ""              # empty = auto-detect from available providers
max_iterations: 300         # max tool calls per conversation turn
stream: true                # stream responses
paper_search_budget: 25     # max papers per search
require_plan_approval: true # require approval before executing plans
```

Override per-user via **Settings > Agent**.
