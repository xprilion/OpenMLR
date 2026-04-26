# Quick Start

Get OpenMLR running in under 2 minutes.

## Choose Your Path

| I want to... | Method | Time |
|--------------|--------|------|
| Try it out quickly | [Docker (Production)](#docker-production) | 2 min |
| Deploy to cloud | [Render / Heroku](#cloud-deployment) | 5 min |
| Develop locally | [Local Development](#local-development) | 5 min |

---

## Docker (Production)

The fastest way to run OpenMLR. Uses pre-built images from Docker Hub.

```bash
git clone https://github.com/xprilion/OpenMLR.git
cd OpenMLR
cp .env.example .env
docker compose up -d
```

Open `http://localhost:3000` and create your account.

::: tip No API keys needed to start
OpenMLR has an onboarding flow that guides you through adding API keys after you log in. You can configure everything from **Settings > Providers** in the UI.
:::

### What's running

| Service | Port | Description |
|---------|------|-------------|
| Web app | 3000 | FastAPI backend + React frontend |
| Worker | - | Celery background job processor |
| PostgreSQL | 5433 | Database |
| Redis | 6380 | Job queue + pub/sub |

### Commands

```bash
docker compose up -d      # Start all services
docker compose logs -f    # Watch logs
docker compose down       # Stop all services
docker compose down -v    # Stop and remove data
```

---

## Cloud Deployment

One-click deploy to Render or Heroku:

<div style="display: flex; gap: 10px; margin: 16px 0;">
  <a href="https://render.com/deploy?repo=https://github.com/xprilion/OpenMLR" target="_blank" rel="noopener">
    <img src="https://render.com/images/deploy-to-render-button.svg" alt="Deploy to Render" width="146" height="32">
  </a>
  <a href="https://www.heroku.com/deploy?template=https://github.com/xprilion/OpenMLR" target="_blank" rel="noopener">
    <img src="https://www.herokucdn.com/deploy/button.svg" alt="Deploy to Heroku" width="196" height="32">
  </a>
</div>

After deployment, add your LLM API keys via the platform's dashboard or through the OpenMLR Settings UI.

---

## Local Development

For contributing or customizing OpenMLR.

### Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.12+ | [python.org](https://www.python.org) |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Node.js | 20+ | [nodejs.org](https://nodejs.org) |
| pnpm | 9+ | `npm i -g pnpm` |

### Setup

```bash
git clone https://github.com/xprilion/OpenMLR.git
cd OpenMLR
make install              # Install Python + Node dependencies
cp .env.example .env      # Create config file
make infra                # Start PostgreSQL + Redis in Docker
make db-fresh             # Create database tables
make dev                  # Start dev servers
```

Open `http://localhost:5173` (Vite dev server with hot reload).

See [Setup & Installation](/setup) for detailed options.

---

## First Steps

1. **Create account** — First user is automatically registered
2. **Add API keys** — Go to **Settings > Providers** and add at least one LLM key (OpenAI, Anthropic, or OpenRouter)
3. **Start chatting** — You're in **Plan mode** by default. Use `Cmd+B` / `Cmd+E` to switch between Plan and Execute modes.

---

## Next

- [Configuration](/configuration) — Environment variables and settings
- [Agent Harness](/agent-harness) — How the agent works
- [Modes](/modes) — Plan vs Execute mode explained
