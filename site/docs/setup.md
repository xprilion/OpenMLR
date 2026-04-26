# Setup & Installation

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.12+ | [python.org](https://www.python.org) |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Node.js | 20+ | [nodejs.org](https://nodejs.org) |
| pnpm | 9+ | `npm i -g pnpm` |
| PostgreSQL | 14+ | [postgresql.org](https://www.postgresql.org) |
| Docker | 20+ | [docker.com](https://www.docker.com) (recommended) |

## Quick Start with Docker Compose

```bash
git clone https://github.com/xprilion/OpenMLR.git
cd OpenMLR
cp .env.example .env   # add your API keys
docker compose up -d
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

> **Do not** create a virtual environment at the project root.
> The backend is a standalone uv project — `uv sync` and `uv run` manage
> `backend/.venv` automatically. A root-level venv will cause import errors.

### Configure

```bash
cp .env.example .env
```

Edit `.env` with at least a database URL and one LLM provider:

```bash
DATABASE_URL="postgresql://user:pass@localhost:5432/openmlr"
OPENROUTER_API_KEY=sk-or-...    # or OPENAI_API_KEY or ANTHROPIC_API_KEY
```

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
make dev        # backend + frontend dev servers
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
make dev-docker     # docker compose with live reload (includes docs)
```

Code changes are automatically detected and services restart.

## Background Jobs

Enable persistent processing that survives browser refreshes:

```bash
# In .env
REDIS_URL=redis://localhost:6379/0
USE_BACKGROUND_JOBS=true
USE_REDIS_PUBSUB=true
```

When enabled:
- Agent continues processing even if you close the browser
- Per-conversation processing state — multiple conversations run in parallel
- Redis-based interrupt relay actually kills running worker tasks
- Reconnecting via SSE catches up on missed events

Requires a running Redis server. Use `make infra` to start one with Docker.

## First Launch

1. Open `http://localhost:5173` (dev) or `http://localhost:3000` (prod/Docker)
2. Create an account (first user is auto-created)
3. If no LLM provider is configured, the **onboarding flow** guides you through adding API keys at `/settings/providers`
4. Start a conversation — you'll be in **Plan mode** by default
5. Switch to **Execute mode** (P/E button or `Cmd+E`) when ready to work

## All Makefile Targets

Run `make help` for the full list:

| Target | Description |
|--------|-------------|
| **Setup** | |
| `make install` | Install all dependencies |
| **Development** | |
| `make dev` | Run backend + frontend dev servers |
| `make worker` | Start Celery worker only |
| **Docker Compose** | |
| `make up` | Start all services |
| `make down` | Stop all services |
| `make restart` | Quick rebuild web + worker |
| `make rebuild` | Full rebuild from scratch |
| `make logs` | Tail all logs |
| `make infra` | Start only db + redis |
| `make dev-docker` | Live reload with Docker (includes docs) |
| **Database** | |
| `make db-fresh` | Drop + recreate tables |
| `make db-upgrade` | Run migrations |
| **Testing** | |
| `make test` | Run all tests (backend + frontend + docs build) |
| `make test-backend` | Backend tests only (149 tests) |
| `make test-frontend` | Frontend tests only (29 tests) |
| `make test-docs` | Docs build check |
| **Other** | |
| `make check` | Type-check backend + frontend |
| `make docs-dev` | Preview docs locally |
| `make clean` | Remove build artifacts |
