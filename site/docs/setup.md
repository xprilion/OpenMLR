# Setup & Installation

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.12+ | [python.org](https://www.python.org) |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Node.js | 20+ | [nodejs.org](https://nodejs.org) |
| pnpm | 9+ | `npm i -g pnpm` |
| PostgreSQL | 14+ | [postgresql.org](https://www.postgresql.org) |
| Docker | 20+ | [docker.com](https://www.docker.com) (recommended for code execution) |

## Quick Start with Docker Compose

The easiest way to run everything:

```bash
git clone https://github.com/xprilion/OpenMLR.git
cd OpenMLR
cp .env.example .env   # add your API keys
make up                # starts db, redis, web, worker
```

Open `http://localhost:3000`. Create an account on first visit.

## Local Development

### Install

```bash
git clone https://github.com/xprilion/OpenMLR.git
cd OpenMLR
make install
```

This runs `uv sync` for the Python backend and `pnpm install` for the frontend.

> **Do not** create a virtual environment at the project root (`uv venv` or `python -m venv`).
> The backend is a standalone uv project — `uv sync` and `uv run` automatically manage
> `backend/.venv`. Activating a root-level venv will conflict with the backend's environment
> and cause import errors at runtime.

### Configure

```bash
cp .env.example .env
```

Edit `.env` with at least a database URL and one LLM provider:

```bash
DATABASE_URL="postgresql://user:pass@localhost:5432/openmlr"
OPENROUTER_API_KEY=sk-or-...    # or OPENAI_API_KEY or ANTHROPIC_API_KEY
```

For local models, see [Local Models](#local-models) below.

See [Configuration](/configuration) for all options.

### Create database

```bash
make db-fresh   # first time: creates all tables
```

### Run

**Development** (auto-reload):
```bash
make dev
```
Opens backend on `:3000` and Vite dev server on `:5173`. Use `:5173` for development.

**With background jobs** (requires Redis):
```bash
make infra      # start postgres + redis in Docker
make dev-full   # backend + frontend + celery worker
```

**Production**:
```bash
make start
```
Builds the frontend and serves everything from `:3000`.

## Docker Compose

### Production

```bash
make up         # start all services
make logs       # tail logs
make restart    # quick rebuild + restart
make down       # stop all services
```

### Development with Live Reload

```bash
make dev-docker-build   # first time
make dev-docker         # subsequent runs
```

Code changes are automatically detected and services restart.

### Useful Commands

| Command | Description |
|---------|-------------|
| `make up` | Start all services |
| `make down` | Stop all services |
| `make restart` | Quick rebuild web + worker |
| `make rebuild` | Full rebuild from scratch |
| `make logs` | Tail all logs |
| `make logs-web` | Tail web service only |
| `make logs-worker` | Tail worker only |
| `make shell-db` | psql into database |
| `make shell-web` | bash into web container |
| `make infra` | Start only db + redis |

## Local Models

OpenMLR supports any OpenAI-compatible API for local inference.

### Ollama

```bash
# Start Ollama
ollama serve

# Pull a model
ollama pull llama3.1

# Configure in .env
OLLAMA_MODEL=llama3.1
```

Use as `ollama/llama3.1` in the model selector.

### LM Studio

1. Start the LM Studio server from the UI
2. Configure in `.env`:
```bash
LMSTUDIO_API_BASE=http://localhost:1234/v1
LMSTUDIO_MODEL=default
```

Use as `lmstudio/default` in the model selector.

### vLLM / text-generation-inference / Other

For any OpenAI-compatible server:

```bash
LOCAL_API_BASE=http://localhost:8000/v1
LOCAL_MODEL=local/my-model
LOCAL_API_KEY=not-needed   # if no auth required
```

Use as `local/my-model` in the model selector.

## First Launch

1. Open `http://localhost:5173` (dev) or `http://localhost:3000` (prod/Docker)
2. Create an account (first user is auto-created)
3. The model is auto-detected from your configured API keys
4. Start a conversation in **Plan** mode

## Background Jobs

To enable persistent task tracking that survives browser refreshes:

```bash
# In .env
REDIS_URL=redis://localhost:6379/0
USE_BACKGROUND_JOBS=true
USE_REDIS_PUBSUB=true
```

When enabled:
- Tasks and resources persist to the database
- Agent continues processing even if you close the browser
- You can return later and see all progress

## All Makefile Targets

Run `make help` for the full list:

| Target | Description |
|--------|-------------|
| **Setup** | |
| `make install` | Install all dependencies |
| **Development** | |
| `make dev` | Run backend + frontend |
| `make dev-full` | Run with background jobs |
| `make worker` | Start Celery worker only |
| **Docker Compose** | |
| `make up` | Start all services |
| `make down` | Stop all services |
| `make restart` | Quick rebuild + restart |
| `make rebuild` | Full rebuild |
| `make logs` | Tail all logs |
| `make infra` | Start only db + redis |
| `make dev-docker` | Live reload with Docker |
| **Database** | |
| `make db-fresh` | Drop + recreate tables |
| `make db-upgrade` | Run migrations |
| **Other** | |
| `make check` | Type-check backend + frontend |
| `make test` | Run backend tests |
| `make docs-dev` | Preview docs locally |
| `make clean` | Remove build artifacts |
