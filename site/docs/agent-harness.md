---
title: Agent Harness - OpenMLR
description: Deep dive into OpenMLR's agent execution engine. Agent loop, tool dispatch, context management, doom loop detection, and sub-agent streaming.
---

# Agent Harness

The agent harness is the core execution engine that processes user messages, manages tool calls, and maintains conversation context.

## Overview

The harness is designed for extended, multi-turn research workflows:

- **Long-running sessions** — Up to 300 tool calls per user message
- **Mode enforcement** — Restricts tools based on Plan/Execute mode
- **Context management** — Automatic compaction when approaching model limits
- **Doom loop detection** — Breaks out of repetitive tool call patterns
- **DB-persisted writing** — Paper drafts survive across workers and restarts
- **Redis interrupt relay** — Actually kills running tasks, not just a flag check
- **Sub-agent streaming** — Research tool spawns nested agents with visible tool calls

## Agent Loop

```
┌─────────────────────────────────────────────────────────┐
│                    Agent Loop                             │
│                                                          │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐             │
│  │ Context  │──▶│   LLM    │──▶│  Parse   │             │
│  │ Manager  │   │  Stream  │   │ Response │             │
│  └──────────┘   └──────────┘   └────┬─────┘             │
│       ▲                             │                    │
│       │                    ┌────────▼────────┐           │
│       │                    │   Tool Router   │           │
│       │                    │ (mode filtering)│           │
│       │                    └────────┬────────┘           │
│       │                             │                    │
│       │                    ┌────────▼────────┐           │
│       │                    │  Execute Tools  │           │
│       │                    └────────┬────────┘           │
│       │                             │                    │
│  ┌────┴────────────┐      ┌────────▼────────┐           │
│  │ Doom Detection  │◀─────│  Add Results    │           │
│  │ (break loops)   │      │  to Context     │           │
│  └─────────────────┘      └─────────────────┘           │
└─────────────────────────────────────────────────────────┘
```

The loop runs for each user message:

1. Check if context needs compaction
2. Call LLM with streaming (system prompt + history + tools)
3. Parse response for tool calls
4. Filter tools through mode restrictions
5. Execute allowed tools, return errors for blocked ones
6. Add results to context
7. Check for doom loops
8. Repeat until LLM produces no tool calls or max iterations reached

## Mode Enforcement

Tools are restricted based on the current mode at three layers:

1. **System prompt** — Instructs the agent about mode constraints
2. **Tool filtering** — Only mode-allowed tools are sent to the LLM
3. **Runtime blocking** — Blocked calls return an error instead of executing

See [Modes](/modes) for the full breakdown.

## Context Management

**Token tracking** uses a character-based estimate (~4 chars per token).

**Compaction** triggers at 90% of the model's context window:
- Summarizes old messages while preserving recent ones
- Keeps the last N messages untouched (default: 5)
- Preserves completion reports, key decisions, and PLAN.md
- Broadcasts `context_usage` events for the UI gauge

## Doom Loop Detection

Detects when the agent gets stuck in repetitive patterns:

**Identical consecutive calls** — Same tool + same arguments 3+ times:
```
bash(ls) → bash(ls) → bash(ls)  → DETECTED
```

**Repeating sequences** — A-B-A-B patterns:
```
read(a) → edit(a) → read(a) → edit(a)  → DETECTED
```

When detected, a correction prompt is injected telling the agent to try a different approach.

## DB-Persisted Writing Projects

Paper writing uses the `writing_projects` table:
- Outline, sections, and bibliography are stored as structured data
- Every write/update auto-saves to the database immediately
- Writing state survives Celery worker restarts, server redeployments, and browser refreshes
- The Paper tab in the UI reads directly from the database
- Client-side export to Markdown or LaTeX

## Redis Interrupt Relay

When a user clicks Stop:

1. Frontend sends `POST /api/interrupt`
2. Web process publishes interrupt signal to Redis channel
3. Celery worker receives the signal
4. Worker kills the running agent task immediately
5. `interrupted` event is broadcast via SSE

This is a real kill, not a cooperative flag check. The agent stops within seconds regardless of what tool is executing.

## Sub-Agent Streaming

The `research` tool spawns an independent sub-agent:

- Sub-agent has its own context window and tool set
- Parent agent sees nested tool calls streamed in real-time
- Frontend displays nested tool calls inline within the research tool output
- Useful for deep dives that would consume too much of the main context

## Per-Conversation Processing

Each conversation gets isolated state:

- Own agent session, tool router, and sandbox manager
- Processing state tracked independently (`idle` / `processing` / `interrupted`)
- Multiple conversations can process in parallel
- Interrupting one does not affect others

## Configuration

Key settings in `AgentConfig`:

```python
@dataclass
class AgentConfig:
    model_name: str = ""                    # LLM to use (empty = auto-detect)
    max_iterations: int = 300               # Tool calls per turn
    stream: bool = True                     # Stream responses
    compact_threshold_ratio: float = 0.90   # Compact at 90%
    untouched_messages: int = 5             # Keep last N during compaction
    default_max_tokens: int = 200000        # Fallback context size
    yolo_mode: bool = False                 # Skip confirmations
```
