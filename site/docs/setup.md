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

## Install

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

## Configure

```bash
cp .env.example .env
```

Edit `.env` with at least a database URL and one LLM provider key:

```bash
DATABASE_URL="postgresql://user:pass@localhost:5432/openmlr"
OPENROUTER_API_KEY=sk-or-...    # or OPENAI_API_KEY or ANTHROPIC_API_KEY
```

See [Configuration](/configuration) for all options.

## Create database

```bash
make db-fresh   # first time: creates all tables
```

## Run

**Development** (auto-reload):
```bash
make dev
```
Opens backend on `:3000` and Vite dev server on `:5173`. Use `:5173` for development.

**Production**:
```bash
make start
```
Builds the frontend and serves everything from `:3000`.

## First launch

1. Open `http://localhost:5173` (dev) or `http://localhost:3000` (prod)
2. Create an account (first user is auto-created)
3. The model is auto-detected from your configured API keys
4. Start a conversation in **Plan** mode

## Docker

```bash
make docker-build
make docker-run    # reads .env for DATABASE_URL and API keys
```

## All Makefile targets

Run `make help` to see all available commands:

| Target | Description |
|--------|-------------|
| `make install` | Install all dependencies |
| `make dev` | Run both servers in parallel |
| `make build` | Build production frontend |
| `make start` | Build + start production server |
| `make db-create` | Create tables (safe) |
| `make db-fresh` | Drop + recreate tables |
| `make check` | Type-check backend + frontend |
| `make test` | Run backend tests |
| `make docs-dev` | Preview docs locally |
| `make docs-build` | Build docs site |
| `make clean` | Remove build artifacts |
