---
title: Setup & Installation - OpenMLR
description: Install OpenMLR with Docker Compose or set up local development. Prerequisites, quick start guide, and deployment options for the ML research agent.
---

# Setup & Installation

This guide covers all deployment options in detail. For a quick start, see the [Quick Start](/quickstart) guide.

## Deployment Options

| Method | Best for | Database | Redis |
|--------|----------|----------|-------|
| [Docker Production](#docker-production) | Self-hosting, trying it out | Included | Included |
| [Docker Development](#docker-development) | Contributing with Docker | Included | Included |
| [Local Development](#local-development) | Contributing without Docker | You provide | Optional |
| [Cloud (Render/Heroku)](#cloud-deployment) | Production hosting | Managed | Managed |

---

## Docker Production

Uses pre-built images from [Docker Hub](https://hub.docker.com/r/xprilion/openmlr). No build step required.

### Requirements
- Docker 20+
- Docker Compose v2

### Setup

```bash
git clone https://github.com/xprilion/OpenMLR.git
cd OpenMLR
cp .env.example .env
make up
# or: docker compose -f docker-compose.prod.yml up -d
```

Open `http://localhost:3000`. Create an account and configure API keys in **Settings > Providers**.

### Commands

| Command | Description |
|---------|-------------|
| `make up` | Start production stack |
| `make down` | Stop production stack |
| `make logs` | Tail production logs |
| `make restart` | Rebuild and restart web + worker |

### Services

| Service | Internal | External | Description |
|---------|----------|----------|-------------|
| web | :3000 | :3000 | FastAPI + React |
| worker | - | - | Celery background jobs |
| db | :5432 | :5433 | PostgreSQL 16 |
| redis | :6379 | :6380 | Redis 7 |

External ports are mapped to non-standard ports to avoid conflicts with local services.

---

## Docker Development

Development mode with live reload. Code changes are reflected immediately.

### Setup

```bash
git clone https://github.com/xprilion/OpenMLR.git
cd OpenMLR
cp .env.example .env
make dev-up
# or: docker compose up -d
```

Open `http://localhost:3000`.

### Commands

| Command | Description |
|---------|-------------|
| `make dev-up` | Start dev stack with live reload |
| `make dev-down` | Stop dev stack |
| `make dev-logs` | Tail dev logs |
| `make dev-clean` | Stop and remove volumes |
| `make dev-build` | Rebuild dev images |

### How it works

The default `docker-compose.yml` is configured for development:
- Mounts `backend/` into the container
- Runs uvicorn with `--reload`
- Uses `watchmedo` for worker auto-restart on code changes

---

## Local Development

Full native setup without Docker for the application (still uses Docker for Postgres/Redis).

### Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.12+ | [python.org](https://www.python.org) |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Node.js | 20+ | [nodejs.org](https://nodejs.org) |
| pnpm | 9+ | `npm i -g pnpm` |

### Setup

```bash
# Clone and install
git clone https://github.com/xprilion/OpenMLR.git
cd OpenMLR
make install

# Configure
cp .env.example .env

# Start infrastructure (Postgres + Redis in Docker)
make infra

# Create database tables
make db-fresh

# Run dev servers
make dev
```

Open `http://localhost:5173` (frontend) or `http://localhost:3000` (backend API).

::: warning Virtual environment location
Do **not** create a virtual environment at the project root. The backend manages its own venv at `backend/.venv` via uv. A root-level venv will cause import errors.
:::

### Dev server details

| Server | Port | Description |
|--------|------|-------------|
| Backend | 3000 | FastAPI with auto-reload |
| Frontend | 5173 | Vite with HMR |

The Vite dev server proxies `/api` requests to the backend.

### With background jobs

To test Celery-based background processing locally:

```bash
# Terminal 1: Infrastructure
make infra

# Terminal 2: Backend + Frontend
USE_BACKGROUND_JOBS=true USE_REDIS_PUBSUB=true make dev

# Terminal 3: Celery worker
make worker
```

Or use the combined command:

```bash
make infra
make dev-full    # Runs backend + frontend + worker
```

### Commands

| Command | Description |
|---------|-------------|
| `make install` | Install all dependencies |
| `make dev` | Run backend + frontend |
| `make dev-full` | Run backend + frontend + worker |
| `make worker` | Run Celery worker only |
| `make infra` | Start Postgres + Redis in Docker |
| `make db-fresh` | Drop and recreate all tables |
| `make db-upgrade` | Run Alembic migrations |

---

## Cloud Deployment

### Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/xprilion/OpenMLR)

Render deploys from the `render.yaml` blueprint which provisions:
- Web service (FastAPI + React)
- Background worker (Celery)
- PostgreSQL database
- Redis instance

After deployment, add your API keys in the Render dashboard under Environment Variables, or configure them in the OpenMLR Settings UI.

### Heroku

[![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://www.heroku.com/deploy?template=https://github.com/xprilion/OpenMLR)

Heroku deployment uses the `app.json` manifest. Add your API keys via Heroku's Config Vars or the OpenMLR Settings UI.

---

## First Launch

1. Open the app URL
2. **Create account** — First user is automatically registered
3. **Configure providers** — Go to **Settings > Providers** and add at least one LLM API key
4. **Start a conversation** — You'll be in Plan mode by default
5. **Switch modes** — Use `Cmd+B` (Plan) or `Cmd+E` (Execute) to toggle modes

---

## Makefile Reference

Run `make help` for the full list. Key targets:

### Development
| Target | Description |
|--------|-------------|
| `make install` | Install all dependencies |
| `make dev` | Run backend + frontend dev servers |
| `make dev-full` | Run backend + frontend + Celery worker |
| `make worker` | Start Celery worker only |
| `make infra` | Start Postgres + Redis in Docker |

### Docker (Production)
| Target | Description |
|--------|-------------|
| `make up` | Start production stack |
| `make down` | Stop production stack |
| `make logs` | Tail production logs |
| `make restart` | Rebuild and restart web + worker |

### Docker (Development)
| Target | Description |
|--------|-------------|
| `make dev-up` | Start dev stack with live reload |
| `make dev-down` | Stop dev stack |
| `make dev-logs` | Tail dev logs |
| `make dev-clean` | Stop and remove volumes |

### Database
| Target | Description |
|--------|-------------|
| `make db-fresh` | Drop + recreate tables |
| `make db-upgrade` | Run Alembic migrations |
| `make db-migrate MSG="..."` | Generate new migration |

### Testing
| Target | Description |
|--------|-------------|
| `make test` | Run all tests |
| `make test-backend` | Backend tests only |
| `make test-frontend` | Frontend tests only |
| `make lint` | Run all linters |
| `make lint-fix` | Auto-fix linting issues |

### Docker Hub
| Target | Description |
|--------|-------------|
| `make docker-build` | Build production image |
| `make docker-publish` | Build, tag, and push to Docker Hub |
