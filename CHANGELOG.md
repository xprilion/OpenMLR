# Changelog

## v0.4.0

Projects, workspaces, interactive terminal, multi-provider model picker, security hardening, and centralized version management.

### Projects & Workspaces
- **Project management** — Create, rename, archive, and manage projects via the sidebar or Settings. Each project gets a persistent workspace directory with standard subdirectories (`code/`, `data/`, `papers/`, `research/`, etc.)
- **Default project** — Every user gets an auto-created "All Conversations" project; conversations can be moved between projects
- **File browser** — Interactive file tree panel for browsing project workspace files, with lazy-loading directories, file-type icons, inline text preview, and file sizes on hover
- **File operations API** — Browse, read, write, delete, and upload files within project workspaces via REST endpoints
- **Knowledge graph** — Per-project persistent knowledge graph (backed by `networkx`) for cross-conversation memory. Supports 10 entity types (paper, concept, method, dataset, etc.) and 13 relationship types (cites, implements, extends, etc.). Context is injected into new conversations automatically
- **Workspace persistence** — Saves search results, research notes, parsed papers, tool failure logs, compute probes, experiment logs, and cross-conversation state to the project workspace
- **Workspace agent tools** — New `workspace` tool with 8 operations: `status`, `search`, `note`, `knowledge_add`, `knowledge_relate`, `knowledge_query`, `knowledge_summary`, and `recent_failures`
- **Project manage modal** — Bulk project management UI with inline rename, conversation counts, and delete with confirmation

### Interactive Terminal
- **WebSocket PTY terminal** — Full interactive bash shell in the browser via xterm.js, connected to a real server-side PTY process scoped to the project workspace
- **Environment scrubbing** — Terminal sessions receive a minimal allowlisted environment; server secrets (API keys, DATABASE_URL, JWT_SECRET_KEY, etc.) are never exposed
- **Terminal UI** — Maximize/minimize toggle, connection status indicator, manual reconnect, 5,000-line scrollback, JetBrains Mono font

### Model Picker & Providers
- **Multi-provider model catalog** — Browse models from OpenAI, Anthropic, OpenRouter, OpenCode Go, Ollama, and LM Studio in a unified picker. Live model list fetched from `models.dev` with hardcoded fallbacks
- **Custom providers** — Register arbitrary OpenAI-compatible, Anthropic SDK, OpenRouter, or LiteLLM endpoints with custom base URLs and API keys. Fetch and cache model lists from custom endpoints
- **Model picker UI** — Two-tab modal with search/filter, provider logos, recently used models (up to 5), and a custom model ID input for arbitrary model strings
- **Provider settings** — Tabbed settings page (Models, Search, Papers, Compute, Others) with per-provider status indicators, inline API key management, and an "Add Custom Provider" modal
- **Automatic SDK routing** — Models are routed to the correct SDK (OpenAI or Anthropic) based on provider and model name. Custom providers specify their SDK type explicitly
- **Recently used models** — Last 5 used models tracked per-user and shown at the top of the picker

### Security
- **Path traversal prevention** — All file operations use `Path.relative_to()` containment checking; symlinks pointing outside the workspace are blocked for both reads and deletes
- **Resource limits** — File uploads capped at 100 MB, writes at 10 MB, reads truncated at 500 KB; knowledge graph limited to 10,000 nodes / 50,000 edges; terminal input capped at 4 KB per message
- **Process isolation** — Terminal shells spawned with `start_new_session=True`, `close_fds=True`, `--norc --noprofile`; zombie prevention via SIGTERM/SIGKILL escalation with proper `waitpid` reaping
- **Protected directories** — Top-level workspace directories (`code`, `data`, `papers`, etc.) cannot be deleted via the API
- **Config allowlist** — `POST /api/config` only accepts a hardcoded list of 10 environment variable names

### Version Management
- **Single source of truth** — New `VERSION` file at repo root; all version references derive from it
- **Automatic version bumping** — `make version-patch`, `make version-minor`, `make version-major` commands bump and propagate across the entire monorepo
- **Explicit version setting** — `make version-set V=X.Y.Z` for arbitrary version changes
- **Version display** — Current version shown in the webapp sidebar footer and docs site footer

### Bug Fixes
- Fixed `test_list_projects_api` failing due to auto-created default project not being accounted for
- Fixed `KeyManager` path to use `/app/.keys` instead of `/.keys`
- Fixed dev entrypoint to always sync dependencies on startup
- Fixed eslint pre-commit hook path resolution for new files
- Added missing `python-multipart` dependency for file upload endpoint

### Internal
- 65 new tests for projects, workspaces, knowledge graph, and workspace tools (740 backend tests, 186 frontend tests total)
- Unified version strings: removed hardcoded versions from `app.py`, `health.py`, `test_app.py`
- Changelog moved to repo root; synced into docs site at build time with VitePress frontmatter
- Pydantic request/response models for all API endpoints (`backend/openmlr/models.py`)

---

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
