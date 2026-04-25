# OpenMLR

A self-hosted ML research intern that plans tasks, reads papers, writes drafts,
and runs experiments — end to end.

**Docs**: [docs.openmlr.dev](https://docs.openmlr.dev)

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
- **Multi-provider LLMs** — OpenAI, Anthropic, OpenRouter (auto-detected from
  configured keys)
- **Per-message modes** — Plan, Research, Write selector on every message;
  code execution available in all modes
- **Task management** — right-side panel with tasks, resources, search budget;
  draggable separator; slide-out report viewer
- **MCP support** — connect any Model Context Protocol server as additional tools
- **User accounts** — JWT auth, per-user settings and API keys

## Quick Start

```bash
git clone https://github.com/xprilion/open-mlr.git
cd open-mlr
make install
cp .env.example .env   # edit with DATABASE_URL + at least one LLM key
make db-fresh
make dev
```

Open `http://localhost:5173`. Create an account on first visit.

See [Setup & Installation](https://docs.openmlr.dev/setup) for details.

## Makefile

Run `make help` for all targets:

| Target | Description |
|--------|-------------|
| `make install` | Install all deps (backend + frontend) |
| `make dev` | Run dev servers (backend :3000 + Vite :5173) |
| `make build` | Build production frontend |
| `make start` | Build + start production server |
| `make db-fresh` | Drop + recreate tables (first run) |
| `make check` | Type-check backend + frontend |
| `make test` | Run pytest |
| `make docker-build` | Build Docker image |
| `make docker-run` | Run container |
| `make docs-dev` | Preview docs locally |
| `make docs-build` | Build docs site |
| `make docs-publish` | Deploy docs to GitHub Pages |
| `make clean` | Remove build artifacts |

## Architecture

```
frontend/   React 19 + Vite + react-router-dom
backend/    Python 3.12 + FastAPI + SQLAlchemy + asyncpg
site/       VitePress documentation
```

See [Architecture](https://docs.openmlr.dev/architecture) for the full breakdown.

## License

MIT
