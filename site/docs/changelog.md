# Changelog

## v0.2.0

Major rewrite of the mode system, paper writing, processing architecture, and UI routing.

### Mode System
- Simplified from Plan/Research/Write to **Plan + Execute** (two modes)
- Plan mode: ask questions, gather context, create plans. No execution.
- Execute mode: all tools available. Follow the plan.
- Toggle with P/E button, `Cmd+B` (Plan), or `Cmd+E` (Execute)
- Amber border for Plan messages, blue border for Execute messages
- Three-layer mode enforcement: system prompt, tool filtering, runtime blocking

### Paper Writing
- Writing tool with **auto-save to database** — survives across workers and restarts
- Paper preview in the **Paper tab** in the UI
- Client-side export to Markdown and LaTeX
- Outline, sections, and bibliography managed as structured data

### Processing Architecture
- **Per-conversation processing state** — multiple conversations run in parallel
- **Background jobs via Celery + Redis** — close the browser, come back later
- **Redis-based interrupt relay** — actually kills running worker tasks, not just a flag check
- **Sub-agent streaming** — research tool shows nested tool calls in real-time

### Settings & UI
- **Settings as routed pages** (`/settings/providers`, `/settings/agent`, `/settings/sandbox`, `/settings/writing`) — no longer a modal
- **Sticky model selection** — persisted per-user in the database
- **Onboarding flow** — guided setup when no LLM provider is configured
- **Route restructure** — app served from `/` instead of `/app`
- **SSE reconnection catch-up** — missed events replayed on reconnect
- **PLAN.md auto-generated** and pinned in resources panel

### Testing & CI
- **149 backend tests + 29 frontend tests** — comprehensive coverage
- **GitHub CI** — tests run on push and pull request
- `make test` runs all tests (backend + frontend + docs build)
- `make test-backend`, `make test-frontend`, `make test-docs` for targeted runs
