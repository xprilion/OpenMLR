# Changelog

## v0.5.0

Project-scoped conversations, unified file workspace, Monaco code viewer, TODO approval flow, comprehensive agent guidance, and test infrastructure improvements.

### Project-Scoped Conversations
- **Mandatory projects** -- Every conversation must belong to a project; the "All Conversations" concept has been removed entirely
- **Onboarding project creation** -- 3-step onboarding flow: Providers > Model > Create First Project. Users name their project and understand the concept from the start
- **Orphan cleanup** -- Existing conversations without a project are automatically deleted when the conversation list is loaded
- **Project selector** -- No more null state; always shows a real project. Dropdown removed the "All" option

### Unified File Workspace
- **Resources materialized as files** -- PLAN.md, completion reports, and paper drafts are now written as real files to the project workspace (`.project-meta/plans/`, `.project-meta/reports/`, `papers/`) and appear in the Files panel
- **Resources panel removed** -- The separate Resources section in the right panel has been replaced by the unified FileTree. Tasks tab renamed to Todos and displayed alongside Files as stacked collapsible panels (no more tab buttons)
- **workspace_files_changed SSE event** -- FileTree auto-refreshes when resources are written to the workspace
- **File badges** -- Pin icon for PLAN.md, clipboard icon for reports, book icon for paper drafts in the FileTree

### Monaco Code Viewer
- **Agent/Editor tabs** -- Main content area now has two tabs: Agent (chat) and Editor (read-only code viewer)
- **Monaco Editor integration** -- VS Code engine (`@monaco-editor/react`) with full syntax highlighting, minimap, line numbers, bracket pair colorization, and word wrap. Supports 15+ languages (Python, TypeScript, JSON, Markdown, YAML, LaTeX, shell, etc.)
- **Multi-tab file viewer** -- Open multiple files as tabs in the Editor, close individually. Closing the last tab switches back to the Agent tab
- **FileTree integration** -- Clicking a file in the Files panel opens it in the Editor tab; inline preview removed

### Agent Improvements
- **Message persistence fix** -- Assistant text that precedes tool calls is now persisted to the database via an `assistant_message` event, surviving page refreshes
- **Plan-mode research budget** -- Warns after 5+ research tool calls in Plan mode; guides the agent to save comprehensive research for Execute mode tasks
- **TODO approval in Execute mode** -- Creating or adding tasks in Execute mode requires user approval via a dedicated review UI with current vs. proposed diff view and inline task editing
- **Blank section enforcement** -- Writing tool warns about incomplete sections after each write; `get_draft` appends a WARNING listing all `[Not yet written]` placeholders

### Workspace Targeting
- **Project workspace auto-targeting** -- `read`, `write`, `edit`, and `bash` tools automatically target the active project workspace directory. Files created by the agent appear in the Files panel
- **Workspace context wiring** -- Both inline and Celery worker sessions resolve the project workspace and set context for workspace tools (knowledge graph, notes) and local tools (file operations)

### Comprehensive Agent Guidance
- **System prompt v7** -- Full rewrite with a Tool Selection Decision Tree, Workspace Structure reference, expanded Code Execution constraints, and strengthened Plan/Execute mode rules
- **Expanded tool descriptions** -- `bash` (Docker constraints, common patterns), `read` (offset/limit usage), `write` (workspace targeting, anti-pattern for papers), `edit` (find-and-replace semantics), `research` (available tools, iteration limits), `writing` (full workflow, placeholder enforcement), `plan_tool` (enforcement rules, workspace file locations)
- **Research sub-agent prompt** -- Now lists available tools, constraints (60 iterations, ~190k token budget), stop conditions, error handling guidance, and clarifies that the sub-agent cannot write to the workspace

### Testing & Infrastructure
- **Pytest hang fix** -- Removed deprecated `event_loop` session fixture, added `_dispose_engine_at_exit` for async engine cleanup, set `asyncio_mode = "auto"` in pytest config. Full backend suite now exits cleanly in ~50s
- **47 new backend tests** -- Message persistence, research budget, project workspace targeting, incomplete section warnings, orphan cleanup, workspace path resolution, TODO approval Redis helpers, report persistence
- **22 new frontend tests** -- EditorPanel (12 tests), FileTree (10 tests)
- **ProjectSelector tests** -- 12 tests verifying no-null project selection
- **TodoReviewDrawer tests** -- 10 tests for the approval UI
- **Total: 858 backend + 226 frontend = 1,084 tests**

### Bug Fixes
- Fixed silent exception swallowing in `_wire_persistence` (now logs errors via `logger.exception`)
- Fixed inline-mode SSE events missing `conversation_uuid` (prevented cross-conversation event leakage)
- Fixed `pnpm-lock.yaml` not including `@monaco-editor/react` for Docker builds
- Fixed `test_list_conversations` and `test_conversations_isolated_by_user` for project-scoped queries
- Fixed `test_conversations.py` integration tests to create conversations with a project

---

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
