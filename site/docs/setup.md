---
title: Setup & Installation - OpenMLR
description: Install OpenMLR with Docker Compose or set up local development. Prerequisites, quick start guide, and deployment options for the ML research agent.
---

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

## Quick Start with Docker Compose (Recommended)

OpenMLR is available as a pre-built image on [Docker Hub](https://hub.docker.com/r/xprilion/openmlr).

```bash
git clone https://github.com/xprilion/OpenMLR.git
cd OpenMLR
cp .env.example .env   # add your API keys
docker compose up -d
```

This will pull the `xprilion/openmlr:latest` image and start it along with PostgreSQL and Redis. Open `http://localhost:3000` to begin.

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

### Production Stack
```bash
make up         # start all services (pulls from Docker Hub)
make logs       # tail logs
make down       # stop all services
```

### Development Stack (Live Reload)
```bash
make dev-up     # start with live reload (mounts source code)
make dev-logs   # tail dev logs
make dev-down   # stop dev services
```
Code changes in `backend/` are automatically detected and the server restarts inside the container.


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
| **Docker Compose (Prod)** | |
| `make up` | Start production stack |
| `make down` | Stop production stack |
| `make logs` | Tail production logs |
| **Docker Compose (Dev)** | |
| `make dev-up` | Start dev stack with live reload |
| `make dev-down` | Stop dev stack |
| `make dev-logs` | Tail dev logs |
| `make dev-clean` | Stop dev stack and remove volumes |
| **Docker Hub** | |
| `make docker-publish` | Build and push to Docker Hub |
| **Database** | |
| `make db-fresh` | Drop + recreate tables |
| `make db-upgrade` | Run migrations |
| **Testing** | |
| `make test` | Run all tests (backend + frontend + docs build) |
| `make test-backend` | Backend tests only (591 tests) |
| `make test-frontend` | Frontend tests only (182 tests) |
| `make test-docs` | Docs build check |
| **Linting** | |
| `make lint` | Run all linters (ruff + ESLint) |
| `make lint-backend` | Lint backend with ruff |
| `make lint-frontend` | Lint frontend with ESLint |
| `make lint-fix` | Auto-fix linting issues |
| **Other** | |
| `make check` | Type-check backend + frontend |
| `make docs-dev` | Preview docs locally |
| `make clean` | Remove build artifacts |
