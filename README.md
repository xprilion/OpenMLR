# OpenMLR

Built for ML researchers who are tired of context-switching.

Search papers, take notes, write drafts, run experiments — all in one conversation.
Your context stays with you from the first question to the final export.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/xprilion/OpenMLR)
[![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://www.heroku.com/deploy?template=https://github.com/xprilion/OpenMLR)

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Docs**: [openmlr.dev](https://openmlr.dev)

---

## What it does

- **Plan** — Asks clarifying questions before diving in. Breaks down tasks, tracks progress.
- **Research** — OpenAlex, ArXiv, Papers With Code, citation graphs. Reads full papers, not just abstracts.
- **Write** — Section-by-section drafting with auto-citations. Export to Markdown or LaTeX.
- **Execute** — Docker-isolated code execution. SSH remotes. Modal cloud. Runs experiments, not just snippets.

## Features

- **Structured planning** — asks 2-4 clarifying options before starting, builds task lists, generates completion reports
- **Paper research** — OpenAlex, ArXiv, CrossRef, Papers With Code; reads full papers section-by-section; crawls citation graphs
- **Context tracking** — token usage gauge, auto-compaction approaching limits, preserves key decisions
- **Multi-provider LLMs** — OpenAI, Anthropic, OpenRouter, OpenCode Go, plus local models (Ollama, LM Studio, vLLM)
- **Background jobs** — tasks persist and continue even if you close the browser (requires Redis)
- **Mode enforcement** — Plan, Research, Write modes restrict which tools are available
- **MCP support** — connect any Model Context Protocol server as additional tools

## Quick Start

### Docker Compose (recommended)

```bash
git clone https://github.com/xprilion/OpenMLR.git
cd OpenMLR
cp .env.example .env   # Add your API keys
docker compose up -d
```

Open `http://localhost:3000`. Create an account on first visit.

### Render

Click the button to deploy to Render (includes Postgres + Redis):

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/xprilion/OpenMLR)

After deploy, add your LLM API key(s) in the Environment settings.

### Heroku

[![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://www.heroku.com/deploy?template=https://github.com/xprilion/OpenMLR)

### Coolify

In Coolify, create a new Docker Compose service pointing to this repo. It will use `docker-compose.yml` automatically. Add your LLM API keys as environment variables in the Coolify UI.

### Local Development

```bash
make install           # Install deps (backend + frontend)
cp .env.example .env   # Add DATABASE_URL + at least one LLM key
make db-fresh          # Create tables
make dev               # Start dev servers
```

Open `http://localhost:5173`.

## Configuration

At minimum, you need:

```bash
# Database
DATABASE_URL="postgresql://user:pass@localhost:5432/openmlr"

# At least one LLM provider
OPENAI_API_KEY=sk-...
# or
ANTHROPIC_API_KEY=sk-ant-...
# or
OPENROUTER_API_KEY=sk-or-...
# or
OPENCODE_GO_API_KEY=sk-...   # $5-10/mo for open models
```

See `.env.example` for all options including:
- Local models (Ollama, LM Studio, vLLM)
- Background jobs (Redis + Celery)
- Web search (Brave API)
- GitHub integration

## Using Local Models

```bash
# Ollama
OLLAMA_MODEL=llama3.1
# Use as: ollama/llama3.1

# LM Studio
LMSTUDIO_API_BASE=http://localhost:1234/v1
# Use as: lmstudio/default

# Any OpenAI-compatible API
LOCAL_API_BASE=http://localhost:8000/v1
LOCAL_MODEL=my-model
# Use as: local/my-model
```

## Architecture

```
frontend/   React 19 + Vite + react-router-dom
backend/    Python 3.12 + FastAPI + SQLAlchemy + Celery
site/       VitePress documentation
```

Key components:
- **Agent Harness** — 300-iteration loop with doom detection, auto-compaction, mode enforcement
- **Tool Router** — Mode-based tool filtering, MCP integration
- **Session Manager** — Per-conversation state isolation
- **LLM Provider** — Multi-provider routing with retry logic

See [Architecture](https://openmlr.dev/architecture) and [Agent Harness](https://openmlr.dev/agent-harness) for details.

## Makefile

| Target | Description |
|--------|-------------|
| `make install` | Install all dependencies |
| `make dev` | Run backend + frontend dev servers |
| `make up` | Start Docker Compose (app on :3000) |
| `make down` | Stop Docker Compose |
| `make restart` | Rebuild + restart web/worker |
| `make logs` | Tail all logs |
| `make docs-docker` | Run docs site (:4000) |
| `make docs-dev` | Run docs locally (:4000) |
| `make db-fresh` | Drop + recreate tables |
| `make check` | Type-check backend + frontend |
| `make test` | Run pytest |

Run `make help` for all targets.

## Contributing

Contributions welcome! Please:

1. Fork the repo
2. Create a feature branch
3. Make your changes
4. Run `make check` and `make test`
5. Submit a PR

## License

MIT
