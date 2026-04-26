# OpenMLR

A self-hosted ML research agent that plans, researches, writes papers, and executes code — all in one conversation.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/xprilion/OpenMLR)
[![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://www.heroku.com/deploy?template=https://github.com/xprilion/OpenMLR)

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Docs**: [openmlr.dev](https://openmlr.dev)

---

## Features

- **Plan + Execute modes** — Plan mode gathers context and creates plans; Execute mode does the work. Toggle with `Cmd+B` / `Cmd+E`.
- **Paper research** — OpenAlex, ArXiv, CrossRef, Papers With Code. Reads full papers, crawls citation graphs.
- **Paper writing** — Section-by-section drafting with auto-save to database. Preview and export (Markdown/LaTeX) in the Paper tab.
- **Sub-agent streaming** — Research tool spawns independent sub-agents with their own context, with nested tool call visibility.
- **Background jobs** — Celery + Redis processing. Close the browser, come back later.
- **Per-conversation parallelism** — Multiple conversations process simultaneously with isolated state.
- **Multi-provider LLMs** — OpenAI, Anthropic, OpenRouter, plus local models (Ollama, LM Studio, vLLM).
- **Onboarding flow** — Guided setup when no LLM provider is configured.

## Quick Start (Docker)

The fastest way to get started is using the pre-built image from Docker Hub:

```bash
git clone https://github.com/xprilion/OpenMLR.git
cd OpenMLR
cp .env.example .env   # Add your API keys (OpenAI/Anthropic/OpenRouter)
docker compose up -d
```

Open `http://localhost:3000`. The first user to visit will be prompted to create an account.

## Local Development

### Option 1: Native (Recommended for fastest iteration)
```bash
make install           # Install deps (backend + frontend)
cp .env.example .env   # Add DATABASE_URL + at least one LLM key
make db-fresh          # Create tables
make dev               # Start dev servers (backend :3000, frontend :5173)
```

### Option 2: Docker (Live reload)
```bash
make dev-up            # Start all services with live reload
make dev-logs          # Watch logs
```
This mounts your local `backend/` directory into the container and uses `uvicorn --reload`.

## Configuration

At minimum, set in `.env`:

```bash
DATABASE_URL="postgresql://user:pass@localhost:5432/openmlr"

# At least one LLM provider
OPENAI_API_KEY=sk-...
# or ANTHROPIC_API_KEY=sk-ant-...
# or OPENROUTER_API_KEY=sk-or-...
```

For background jobs, add:

```bash
REDIS_URL=redis://localhost:6379/0
USE_BACKGROUND_JOBS=true
USE_REDIS_PUBSUB=true
```

See `.env.example` for all options.

## Testing

```bash
make test              # Run all tests (591 backend + 182 frontend + docs build)
make test-backend      # Backend tests only
make test-frontend     # Frontend tests only
make test-docs         # Docs build check
```

## Architecture

```
frontend/   React 19 + TypeScript + Vite
backend/    Python 3.12 + FastAPI + SQLAlchemy + Celery
site/       VitePress documentation
```

See [Architecture](https://openmlr.dev/architecture) for details.

## Contributing

1. Fork the repo
2. Create a feature branch
3. Make your changes
4. Run `make test`
5. Submit a PR

## License

MIT
