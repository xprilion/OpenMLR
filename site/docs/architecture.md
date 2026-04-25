# Architecture

## Overview

OpenMLR is a full-stack application with a React frontend, Python backend, and PostgreSQL database. It's designed to run as a self-hosted service with optional background job processing.

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend                                 │
│  React 19 + Vite + react-router-dom                             │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │ Landing │ │  Login  │ │  Chat   │ │Settings │ │ Reports │   │
│  │  Page   │ │  Page   │ │   UI    │ │  Panel  │ │ Drawer  │   │
│  └─────────┘ └─────────┘ └────┬────┘ └─────────┘ └─────────┘   │
└────────────────────────────────┼────────────────────────────────┘
                                 │ SSE + REST
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Backend                                  │
│  Python 3.12 + FastAPI + SQLAlchemy + Celery                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    Agent Harness                         │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │    │
│  │  │  Loop    │ │ Context  │ │   Tool   │ │   LLM    │   │    │
│  │  │ (300 it) │ │ Manager  │ │  Router  │ │ Provider │   │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                       Tools                              │    │
│  │  papers, research, writing, search, github, sandbox...  │    │
│  └─────────────────────────────────────────────────────────┘    │
└────────────────────────────────────┬────────────────────────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              ▼                      ▼                      ▼
        ┌──────────┐           ┌──────────┐           ┌──────────┐
        │ Postgres │           │  Redis   │           │  Celery  │
        │    DB    │           │  (jobs)  │           │  Worker  │
        └──────────┘           └──────────┘           └──────────┘
```

## Directory Structure

```
OpenMLR/
├── frontend/                    # React 19 + Vite
│   ├── src/
│   │   ├── components/          # UI components
│   │   │   ├── LandingPage.tsx  # Public landing page
│   │   │   ├── LoginPage.tsx    # Auth forms
│   │   │   ├── AuthGuard.tsx    # Route protection
│   │   │   ├── Sidebar.tsx      # Conversation list
│   │   │   ├── MessageList.tsx  # Chat messages
│   │   │   ├── InputArea.tsx    # Message input + mode selector
│   │   │   ├── ModelModal.tsx   # Model picker
│   │   │   ├── ApprovalModal.tsx# Sandbox confirmations
│   │   │   ├── SettingsPanel.tsx# User settings
│   │   │   ├── QuestionDrawer.tsx# Agent questions UI
│   │   │   ├── RightPanel.tsx   # Tasks + resources
│   │   │   └── ReportDrawer.tsx # Completion reports
│   │   ├── hooks/
│   │   │   ├── useSSE.ts        # Server-Sent Events
│   │   │   └── useJobStatus.ts  # Background job polling
│   │   ├── api.ts               # REST client
│   │   └── types.ts             # TypeScript types
│   └── index.html
│
├── backend/
│   ├── openmlr/
│   │   ├── app.py               # FastAPI entry point
│   │   ├── config.py            # Layered config (YAML → env → auto)
│   │   ├── dependencies.py      # DI (auth, db)
│   │   │
│   │   ├── agent/               # Core agent harness
│   │   │   ├── loop.py          # Agentic loop (300 iterations)
│   │   │   ├── context.py       # Token tracking, compaction
│   │   │   ├── session.py       # Per-conversation state
│   │   │   ├── llm.py           # Multi-provider LLM calls
│   │   │   ├── prompts.py       # System prompt builder
│   │   │   ├── doom_loop.py     # Repetition detection
│   │   │   └── types.py         # Data classes
│   │   │
│   │   ├── tools/               # Agent tools
│   │   │   ├── registry.py      # Tool router + mode restrictions
│   │   │   ├── local.py         # bash, read, write, edit
│   │   │   ├── papers.py        # OpenAlex, ArXiv, CrossRef
│   │   │   ├── research.py      # Research sub-agent
│   │   │   ├── writing.py       # Paper drafting
│   │   │   ├── ask_user.py      # Structured questions
│   │   │   ├── plan.py          # Task tracking
│   │   │   ├── search.py        # Brave web search
│   │   │   ├── github.py        # GitHub search
│   │   │   ├── sandbox_tools.py # Sandbox wrappers
│   │   │   └── mcp.py           # MCP integration
│   │   │
│   │   ├── sandbox/             # Code execution
│   │   │   ├── interface.py     # Abstract interface
│   │   │   ├── local.py         # Docker-based
│   │   │   ├── ssh.py           # Remote SSH
│   │   │   └── modal_sandbox.py # Modal cloud
│   │   │
│   │   ├── auth/                # JWT authentication
│   │   │   ├── router.py        # /api/auth/* routes
│   │   │   └── security.py      # bcrypt + JOSE
│   │   │
│   │   ├── db/                  # Database layer
│   │   │   ├── engine.py        # AsyncSession setup
│   │   │   ├── models.py        # SQLAlchemy models
│   │   │   └── operations.py    # CRUD operations
│   │   │
│   │   ├── routes/              # API routes
│   │   │   ├── agent.py         # /api/message, /api/conversations
│   │   │   ├── settings.py      # /api/settings, /api/models
│   │   │   └── health.py        # /health, /api/health
│   │   │
│   │   ├── services/            # Business logic
│   │   │   ├── event_bus.py     # SSE broadcasting
│   │   │   ├── session_manager.py # Session lifecycle
│   │   │   └── job_manager.py   # Celery job tracking
│   │   │
│   │   └── tasks/               # Background jobs
│   │       └── agent_tasks.py   # Celery task definitions
│   │
│   └── configs/
│       └── prompts/
│           └── system_prompt.yaml # Jinja2 system prompt
│
├── site/                        # VitePress documentation
│   └── docs/
│
├── docker-compose.yml           # Production deployment
├── docker-compose.coolify.yml   # Coolify-specific
├── Dockerfile                   # Multi-stage build
└── railway.json                 # Railway deployment
```

## Data Flow

### User Message Processing

```
1. User types message → InputArea.tsx
2. POST /api/message → agent.py:send_message()
3. Load/create session → SessionManager
4. Add user message to context
5. Start agent loop:
   a. Build messages array (system + history + user)
   b. Call LLM with streaming
   c. Parse response for tool calls
   d. Execute tools via ToolRouter
   e. Add results to context
   f. Repeat until no tool calls or max iterations
6. Broadcast events via SSE → useSSE.ts
7. Frontend updates in real-time
```

### SSE Event Stream

```typescript
// Frontend subscribes
const { messages, isConnected } = useSSE('/api/events');

// Backend broadcasts
await event_bus.broadcast({
  event_type: "assistant_chunk",
  data: { chunk: "Hello" },
  conversation_uuid: "..."
});
```

| Event | Payload | When |
|-------|---------|------|
| `processing` | `{status}` | Agent starts thinking |
| `assistant_chunk` | `{chunk}` | Streaming text token |
| `assistant_stream_end` | `{}` | Stream finished |
| `assistant_message` | `{content}` | Non-streaming fallback |
| `tool_call` | `{name, arguments}` | Tool invoked |
| `tool_output` | `{name, output}` | Tool returned |
| `questions` | `{questions}` | Agent asks user |
| `plan_update` | `{tasks}` | Task list changed |
| `resources_update` | `{resources}` | Resources changed |
| `context_usage` | `{used, max, ratio}` | Token gauge |
| `search_budget` | `{used, max}` | Paper search budget |
| `turn_complete` | `{}` | Processing done |
| `error` | `{error}` | Error occurred |
| `interrupted` | `{}` | User cancelled |

## Database Schema

```sql
-- Users and authentication
users (id, username, password_hash, display_name, created_at)
user_settings (id, user_id, category, key, value, created_at, updated_at)

-- Conversations
conversations (id, uuid, user_id, title, model, mode, user_message_count, created_at, updated_at)
messages (id, conversation_id, role, content, metadata, created_at)

-- Research
research_corpus (id, user_id, paper_id, title, authors, abstract, year, source, url, added_at)

-- Writing
writing_projects (id, user_id, title, outline, sections, bibliography, created_at, updated_at)

-- Execution
sandbox_configs (id, user_id, name, type, config, created_at, updated_at)

-- Task tracking (persisted)
conversation_tasks (id, conversation_id, content, status, priority, created_at, updated_at)
conversation_resources (id, conversation_id, title, type, url, content, created_at)

-- Background jobs
agent_jobs (id, job_id, conversation_id, user_id, status, message, mode, model, error, created_at, started_at, completed_at)
```

## LLM Provider Routing

```
Model name format: provider/model-name

openai/gpt-4o           → OpenAI API
anthropic/claude-sonnet-4 → Anthropic API  
openrouter/...          → OpenRouter API
opencode-go/qwen3.6-plus → OpenCode Go API
ollama/llama3.1         → Local Ollama
lmstudio/default        → Local LM Studio
local/my-model          → Custom OpenAI-compatible
```

The `LLMProvider` class handles:
- API key selection based on prefix
- Base URL routing
- Anthropic vs OpenAI message format conversion
- Streaming and non-streaming calls
- Retry with exponential backoff

## Background Jobs

When `USE_BACKGROUND_JOBS=true`:

```
User sends message
       │
       ▼
Web creates AgentJob in DB
       │
       ▼
Celery task queued to Redis
       │
       ▼
Worker picks up job
       │
       ▼
Agent loop runs in worker
       │
       ▼
Events published to Redis pub/sub
       │
       ▼
Web relays to SSE clients
```

Benefits:
- Browser can close, job continues
- Horizontal scaling of workers
- Job status persistence

## Security Model

- **Authentication**: JWT tokens (bcrypt hashed passwords)
- **Authorization**: Per-user data isolation via `user_id` foreign keys
- **API Keys**: Stored in `user_settings` or env vars
- **Sandboxing**: Docker isolation for code execution
- **Confirmations**: Required for sandbox creation, destructive ops (unless `yolo_mode`)

## Deployment Options

| Platform | Config File | Notes |
|----------|-------------|-------|
| Docker Compose | `docker-compose.yml` | Default, all-in-one |
| Railway | `railway.json` | Multi-service template |
| Coolify | `docker-compose.coolify.yml` | One-click deploy |
| Manual | - | Run backend + frontend separately |

See [Setup](/setup) for detailed instructions.
