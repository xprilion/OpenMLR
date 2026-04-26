<p align="center">
  <img src="assets/logo-200.png" alt="OpenMLR Logo" width="120" />
</p>

<h1 align="center">OpenMLR</h1>

<p align="center">
  A self-hosted ML research agent that plans, researches, writes papers, and executes code — all in one conversation.
</p>

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/xprilion/OpenMLR)
[![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://www.heroku.com/deploy?template=https://github.com/xprilion/OpenMLR)

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Docs**: [openmlr.dev](https://openmlr.dev)

---

## Features

- **Plan + Execute modes** — Plan mode gathers context; Execute mode does the work. Toggle with `Cmd+M`.
- **Paper research** — OpenAlex, Semantic Scholar, arXiv, CrossRef, Papers With Code. Reads full papers, crawls citation graphs.
- **Paper writing** — Section-by-section drafting with auto-save. Export to Markdown/LaTeX.
- **Compute environments** — Execute code on local Docker, SSH remotes, or Modal cloud. Probe GPU/CPU capabilities.
- **Background jobs** — Celery + Redis. Close the browser, come back later.
- **Multi-provider LLMs** — OpenAI, Anthropic, OpenRouter, plus local models (Ollama, LM Studio).
- **MCP servers** — Connect external tools via the Model Context Protocol.
- **Onboarding flow** — Guided setup when no LLM provider is configured.

## Quick Start

```bash
git clone https://github.com/xprilion/OpenMLR.git
cd OpenMLR
cp .env.example .env
make up
# or: docker compose -f docker-compose.prod.yml up -d
```

Open `http://localhost:3000`. Create an account. Add your API keys in **Settings > Providers**.

> No API keys needed to start — the app guides you through configuration after login.

## Development

### Docker (recommended)
```bash
make dev-up         # Start with live reload
make dev-logs       # Watch logs
```

### Native
```bash
make install        # Install dependencies
make infra          # Start Postgres + Redis in Docker
make db-fresh       # Create tables
make dev            # Start dev servers (backend :3000, frontend :5173)
```

## Configuration

All LLM and tool API keys can be configured via the **Settings UI** after login. No environment variables are required to start.

For local development without Docker-managed databases:

```bash
DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/openmlr"
```

See [Configuration docs](https://openmlr.dev/configuration) for all options.

## Testing

```bash
make test           # All tests (backend + frontend + docs)
make test-backend   # Backend only
make test-frontend  # Frontend only
make lint           # Run linters
```

## Architecture

```
frontend/   React 19 + TypeScript + Vite
backend/    Python 3.12 + FastAPI + SQLAlchemy + Celery
site/       VitePress documentation
```

See [Architecture docs](https://openmlr.dev/architecture) for details.

## Contributing

1. Fork the repo
2. Create a feature branch
3. Make your changes
4. Run `make test && make lint`
5. Submit a PR

## License

MIT
