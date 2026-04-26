---
title: Changelog - OpenMLR
description: OpenMLR version history and release notes. Track new features, improvements, and changes across all versions.
---

# Changelog

## v0.3.0

Compute environments, UI improvements, and bug fixes.

### Compute Environments
- **Multi-backend compute** — Execute code on local Docker, SSH remotes, or Modal cloud
- **SSH key management** — Generate Ed25519/RSA keys, upload existing keys via Settings > Compute
- **Compute probing** — Detect OS, GPUs (with CUDA version), Python versions, and disk space
- **Compute selection** — Switch between configured compute nodes mid-conversation
- **Connection pooling** — SSH connections are reused across tool calls for performance
- **Docker-in-Docker detection** — Worker container executes commands directly when already in Docker

### UI Improvements
- **Collapsible Tasks & Resources** — Click section headers in the right panel to collapse/expand
- **Fixed right panel layout** — Right panel no longer causes page scroll issues when toggled
- **Improved scroll behavior** — Message list scrolls correctly without affecting page layout

### Bug Fixes
- Fixed `scrollIntoView` causing entire page to scroll when RightPanel is open
- Fixed `_get_draft` database call using wrong function name
- Fixed test suite failures related to async database mocking

### Internal
- Added `_running_in_container()` detection for Docker Compose worker environments
- Improved test coverage for compute and writing tools
- Updated Settings nav to reflect current menu structure

---

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
