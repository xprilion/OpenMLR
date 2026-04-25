# OpenMLR

A self-hosted ML research intern that plans tasks, reads papers, writes drafts,
and runs experiments — end to end.

**Docs**: [openmlr.dev](https://openmlr.dev)

## Features

- **Structured planning** — asks clarifying questions (2-4 options + free text)
  before starting work, builds a task list, generates completion reports
- **Paper research** — OpenAlex, ArXiv, CrossRef, Papers With Code; reads full
  papers section-by-section; crawls citation graphs; per-session search budgets
- **Paper writing** — section-by-section drafting with research corpus,
  bibliography management, Markdown/LaTeX export
- **Code execution** — Docker-isolated by default, SSH remotes, Modal cloud
  sandboxes; probes environment before running anything
- **Context tracking** — token usage gauge, auto-compaction approaching model
  limits, completion reports preserved across compactions
- **Multi-provider LLMs** — OpenAI, Anthropic, OpenRouter, plus local models
  (Ollama, LM Studio, vLLM, any OpenAI-compatible API)
- **Background jobs** — tasks persist to database and continue running even if
  you close the browser (requires Redis + Celery)
- **Per-message modes** — Plan, Research, Write selector on every message;
  code execution available in all modes
- **Task management** — right-side panel with tasks, resources, search budget;
  draggable separator; slide-out report viewer
- **MCP support** — connect any Model Context Protocol server as additional tools
- **User accounts** — JWT auth, per-user settings and API keys

## Quick Start

```bash
git clone https://github.com/xprilion/OpenMLR.git
cd OpenMLR
make install
cp .env.example .env   # edit with DATABASE_URL + at least one LLM key
make db-fresh
make dev
```

Open `http://localhost:5173`. Create an account on first visit.

See [Setup & Installation](https://openmlr.dev/setup) for details.

## Docker Compose

The easiest way to run everything (db, redis, web, background worker):

```bash
cp .env.example .env   # add your API keys
make up                # start all services
make logs              # tail logs
```

Open `http://localhost:3000`.

### Development with Live Reload

```bash
make dev-docker-build  # first time
make dev-docker        # subsequent runs (auto-reloads on code changes)
```

### Useful Commands

```bash
make restart           # quick rebuild + restart web/worker only
make rebuild           # full rebuild from scratch
make down              # stop all services
make shell-db          # psql into database
```

## Local Development (without Docker)

```bash
# Start just the infrastructure
make infra             # starts postgres + redis in Docker

# Run the app locally
make dev               # backend + frontend (no background jobs)
make dev-full          # backend + frontend + celery worker
```

## Using Local Models

OpenMLR supports any OpenAI-compatible API. Configure in `.env`:

### Ollama

```bash
# Start Ollama
ollama serve

# Pull a model
ollama pull llama3.1

# Configure OpenMLR
OLLAMA_MODEL=llama3.1
# OLLAMA_API_BASE=http://localhost:11434/v1  # default
```

### LM Studio

```bash
# Start LM Studio server (in LM Studio UI)
# Configure OpenMLR
LMSTUDIO_API_BASE=http://localhost:1234/v1
LMSTUDIO_MODEL=default
```

### vLLM / text-generation-inference / Any OpenAI-compatible API

```bash
LOCAL_API_BASE=http://localhost:8000/v1
LOCAL_MODEL=local/my-model
LOCAL_API_KEY=not-needed  # if your server doesn't require auth
```

Then use the model with prefix in the UI:
- `ollama/llama3.1`
- `lmstudio/default`
- `local/my-model`

## Makefile

Run `make help` for all targets:

| Target | Description |
|--------|-------------|
| **Setup** | |
| `make install` | Install all deps (backend + frontend) |
| **Development** | |
| `make dev` | Run backend + frontend dev servers |
| `make dev-full` | Run with background jobs (needs Redis) |
| `make worker` | Start Celery worker only |
| **Docker Compose** | |
| `make up` | Start all services |
| `make down` | Stop all services |
| `make restart` | Quick rebuild + restart web/worker |
| `make rebuild` | Full rebuild from scratch |
| `make logs` | Tail all logs |
| `make infra` | Start only db + redis |
| **Docker Dev** | |
| `make dev-docker` | Live reload with Docker |
| `make dev-docker-build` | Build + start dev mode |
| **Database** | |
| `make db-fresh` | Drop + recreate tables |
| `make db-upgrade` | Run migrations |
| **Other** | |
| `make check` | Type-check backend + frontend |
| `make test` | Run pytest |
| `make docker-build` | Build Docker image |
| `make clean` | Remove build artifacts |

## Architecture

```
frontend/   React 19 + Vite + react-router-dom
backend/    Python 3.12 + FastAPI + SQLAlchemy + asyncpg + Celery
site/       VitePress documentation
```

See [Architecture](https://openmlr.dev/architecture) for the full breakdown.

## License

MIT
