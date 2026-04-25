# Configuration

## Environment variables (`.env`)

```bash
# ── Database (required) ──
DATABASE_URL="postgresql://user:pass@localhost:5432/openmlr"

# ── LLM providers (at least one required) ──
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OPENROUTER_API_KEY=sk-or-...

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

## Per-user settings

After login, click the gear icon in the sidebar to open Settings:

| Tab | What you can configure |
|-----|----------------------|
| **Providers** | API keys for all services (stored encrypted in DB, override .env) |
| **Agent** | Default model, research model, YOLO mode |
| **Sandbox** | Default execution environment (local/SSH/Modal), Modal credentials |
| **Writing** | Citation style (APA/IEEE/ACM/Chicago), export format |

## Model selection

Models are auto-detected based on which API keys are configured:

| Key set | Default model |
|---------|--------------|
| `ANTHROPIC_API_KEY` | `anthropic/claude-sonnet-4` |
| `OPENAI_API_KEY` | `openai/gpt-4o` |
| `OPENROUTER_API_KEY` | `openrouter/anthropic/claude-sonnet-4` |

Override via Settings > Agent > Default Model, or by clicking the model
button in the header.

## Agent config file

`backend/configs/agent_config.yaml` controls defaults:

```yaml
model_name: ""              # empty = auto-detect
max_iterations: 300
stream: true
paper_search_budget: 25     # API calls per session
require_plan_approval: true
```
