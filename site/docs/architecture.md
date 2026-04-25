# Architecture

## Overview

```
frontend/               React 19 + Vite + react-router-dom
  src/
    components/         LandingPage, LoginPage, AuthGuard, Sidebar,
                        MessageList, InputArea, ModelModal, ApprovalModal,
                        SettingsPanel, QuestionDrawer, RightPanel, ReportDrawer
    hooks/useSSE.ts     Server-Sent Events with reconnect + token auth
    api.ts              Fetch wrapper with JWT headers

backend/                Python 3.12 + FastAPI
  openmlr/
    app.py              FastAPI entry, lifespan, SPA serving
    config.py           Layered config (YAML → env → auto-detect)
    dependencies.py     Auth + DB dependency injection

    agent/
      llm.py            Multi-provider (OpenAI, Anthropic, OpenRouter)
      loop.py           Agentic loop (300 iter, streaming, tool execution)
      context.py        Token tracking, auto-compaction, undo
      session.py        Per-conversation state
      doom_loop.py      Repetitive pattern detection
      prompts.py        Jinja2 system prompt builder

    tools/
      local.py          Docker-isolated bash, read, write, edit
      papers.py         OpenAlex + CrossRef + ArXiv + Papers With Code
      research.py       Independent research sub-agent
      ask_user.py       Structured questions with options
      plan.py           Task tracking + completion reports
      writing.py        Paper drafting + bibliography
      github.py         Code search + file reading
      search.py         Brave web search
      sandbox_tools.py  Sandbox wrappers
      mcp.py            MCP server integration
      registry.py       ToolRouter

    sandbox/
      interface.py      Abstract SandboxInterface
      local.py          Docker-based local execution
      ssh.py            Remote via SSH/SFTP
      modal_sandbox.py  Modal cloud containers

    auth/               JWT (bcrypt + JOSE)
    db/                 SQLAlchemy async + Alembic
    routes/             agent.py, settings.py
    services/           EventBus (SSE), SessionManager
```

## Data flow

1. User sends message with mode (Plan/Research/Write) via `POST /api/message`
2. Route persists to DB, creates/loads session, fires `asyncio.create_task`
3. Agent loop: builds system prompt → calls LLM → parses tool calls → executes
4. Events stream via SSE: `assistant_chunk`, `tool_call`, `tool_output`, etc.
5. Frontend updates UI in real-time via the `useSSE` hook

## SSE events

| Event | When |
|-------|------|
| `processing` | Agent starts thinking |
| `assistant_chunk` | Streaming text token |
| `assistant_stream_end` | Stream finished |
| `assistant_message` | Full response (non-streaming fallback) |
| `tool_call` | Tool invocation started |
| `tool_output` | Tool result |
| `questions` | Agent asks structured questions |
| `plan_update` | Task list changed |
| `resources_update` | Resource list changed |
| `context_usage` | Token gauge update |
| `search_budget` | Paper search budget update |
| `turn_complete` | Agent finished processing |
| `error` | Error occurred |
| `interrupted` | User cancelled |

## Database tables

| Table | Purpose |
|-------|---------|
| `users` | Accounts (username, bcrypt hash) |
| `user_settings` | Per-user key-value config (category/key/value) |
| `conversations` | Chat sessions (uuid, title, model, mode) |
| `messages` | Message history (role, content, metadata) |
| `sandbox_configs` | Saved sandbox configurations |
| `research_corpus` | Papers in the research corpus |
| `writing_projects` | Paper drafts (outline, sections, bibliography) |
