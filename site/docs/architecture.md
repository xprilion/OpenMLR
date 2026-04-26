---
title: Architecture Overview - OpenMLR
description: OpenMLR system architecture. Python FastAPI backend, React frontend, Celery background jobs, and the complete request flow for ML research workflows.
---

# Architecture

## Overview

OpenMLR is a full-stack application with three packages:

| Package | Stack | Purpose |
|---------|-------|---------|
| `backend/` | Python 3.12, FastAPI, SQLAlchemy async, Celery | API, agent harness, tools, background jobs |
| `frontend/` | React 19, TypeScript, Vite | Chat UI, settings pages, paper preview |
| `site/` | VitePress | Documentation |

## Request Flow

```
┌──────────────────────────────────────────────────────────┐
│                      Frontend                             │
│  React 19 + Vite + react-router-dom                      │
│  /login  /  /:uuid  /settings/*                          │
└────────────────────┬─────────────────────────────────────┘
                     │ SSE + REST
                     ▼
┌──────────────────────────────────────────────────────────┐
│                      Backend                              │
│  FastAPI + SQLAlchemy async                               │
│  ┌──────────────────────────────────────────────────┐    │
│  │              Agent Harness                        │    │
│  │  Loop → LLM → Parse → Tool Router → Execute      │    │
│  │         ↑                           │             │    │
│  │         └───── results ─────────────┘             │    │
│  └──────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────┐    │
│  │  Tools: papers, research, writing, bash, sandbox  │    │
│  └──────────────────────────────────────────────────┘    │
└──────────┬──────────────┬──────────────┬─────────────────┘
           │              │              │
     ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐
     │ PostgreSQL │ │   Redis   │ │  Celery   │
     │     DB     │ │  pub/sub  │ │  Worker   │
     └───────────┘ └───────────┘ └───────────┘
```

## Database Schema

```sql
-- Auth
users (id, username, password_hash, display_name, created_at)
user_settings (id, user_id, category, key, value, updated_at)

-- Conversations
conversations (id, uuid, user_id, title, model, mode, created_at, updated_at)
messages (id, conversation_id, role, content, metadata, created_at)

-- Research & Writing
research_corpus (id, user_id, paper_id, title, authors, abstract, year, source, url)
writing_projects (id, user_id, title, outline, sections, bibliography, updated_at)

-- Execution
sandbox_configs (id, user_id, name, type, config)

-- Task tracking
conversation_tasks (id, conversation_id, content, status, priority)
conversation_resources (id, conversation_id, title, type, content)

-- Background jobs
agent_jobs (id, job_id, conversation_id, user_id, status, message, mode, model, error)
```

## SSE Event Flow

The frontend connects to `/api/events?token=JWT` and receives real-time updates:

```
User sends message
       │
       ▼
  processing          → "thinking..."
       │
       ▼
  assistant_chunk     → streaming text tokens (repeats)
       │
       ▼
  tool_call           → {name, arguments}
       │
       ▼
  tool_output         → {name, output}
       │
       ▼
  (repeat LLM → tools until done)
       │
       ▼
  turn_complete       → processing finished
```

Key events: `processing`, `assistant_chunk`, `assistant_stream_end`, `tool_call`, `tool_output`, `plan_update`, `resources_update`, `context_usage`, `turn_complete`, `error`, `interrupted`.

SSE supports reconnection catch-up — if the client disconnects and reconnects, it receives missed events.

## Background Jobs with Redis Interrupt

When `USE_BACKGROUND_JOBS=true`:

```
User sends message
       │
       ▼
Web process creates AgentJob in DB
       │
       ▼
Celery task queued to Redis
       │
       ▼
Worker picks up job, runs agent loop
       │
       ▼
Events published to Redis pub/sub
       │
       ▼
Web process relays events to SSE clients
```

**Interrupt flow**: When a user clicks Stop, the web process publishes an interrupt signal to Redis. The worker receives it and actually kills the running task — not just a flag check on the next iteration.

## Per-Conversation Processing

Each conversation has its own isolated processing state:

- Multiple conversations can process simultaneously
- Each gets its own agent session, tool router, and sandbox manager
- Processing state (`idle`, `processing`, `interrupted`) is tracked per conversation
- One conversation being interrupted does not affect others

## Deployment Options

| Platform | Config | Notes |
|----------|--------|-------|
| Docker Compose | `docker-compose.yml` | Default, includes all services |
| Render | Deploy button | Includes Postgres + Redis |
| Heroku | Deploy button | Dyno-based |
| Coolify | `docker-compose.coolify.yml` | Self-hosted PaaS |

See [Setup](/setup) for detailed instructions.
