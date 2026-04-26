# Agent Harness

The agent harness is the core execution engine that processes user messages, manages tool calls, and maintains conversation context across long research sessions.

## Overview

OpenMLR's agent harness is designed for extended, multi-turn research workflows. Unlike simple chatbot loops, it handles:

- **Long-running sessions** — Up to 300 tool calls per user message
- **Context management** — Automatic compaction when approaching model limits  
- **Mode enforcement** — Restricts tools based on Plan/Research/Write mode
- **Doom loop detection** — Breaks out of repetitive tool call patterns
- **Streaming output** — Real-time text and tool output via SSE

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Session Manager                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │  Session 1  │  │  Session 2  │  │  Session N  │          │
│  │  (conv_id)  │  │  (conv_id)  │  │  (conv_id)  │          │
│  └──────┬──────┘  └─────────────┘  └─────────────┘          │
└─────────┼───────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│                      Agent Loop                              │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐ │
│  │ Context  │──▶│   LLM    │──▶│  Parse   │──▶│ Execute  │ │
│  │ Manager  │   │  Stream  │   │  Tools   │   │  Tools   │ │
│  └──────────┘   └──────────┘   └──────────┘   └────┬─────┘ │
│       ▲                                            │        │
│       │         ┌──────────────────────────────────┘        │
│       │         ▼                                           │
│  ┌────┴─────────────────┐   ┌────────────────────────────┐ │
│  │   Doom Detection     │   │     Tool Router            │ │
│  │   (break loops)      │   │   (mode filtering)         │ │
│  └──────────────────────┘   └────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Agent Loop (`agent/loop.py`)

The main execution engine. Processes one user message at a time, iterating through LLM calls and tool executions.

```python
# Simplified flow
for iteration in range(max_iterations):  # Default: 300
    if needs_compaction():
        compact_context()
    
    response = await llm.generate_stream(messages, tools)
    
    if response.has_tool_calls:
        for tool_call in response.tool_calls:
            if doom_loop_detected():
                inject_correction_prompt()
                continue
            
            result = await tool_router.call(tool_call)
            messages.append(tool_result)
    else:
        # No more tool calls, turn complete
        break
```

**Key behaviors:**
- Exits when LLM produces no tool calls (natural completion)
- Exits on user interrupt (`/stop` command)
- Auto-compacts context at 90% of model's token limit
- Injects mode hints for Plan/Research/Write modes

### 2. Context Manager (`agent/context.py`)

Tracks message history and token usage. Handles compaction to stay within model limits.

**Token tracking:**
```python
def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)  # ~4 chars per token
```

**Compaction:**
- Triggered at 90% of model's max tokens (configurable)
- Summarizes old messages while preserving recent ones
- Keeps completion reports and key decisions intact
- Preserves the last N messages untouched (default: 5)

**Usage tracking:**
```python
{
    "used": 45000,      # Current token count
    "max": 200000,      # Model's context window
    "ratio": 0.225      # Percentage used
}
```

### 3. Tool Router (`tools/registry.py`)

Central registry for all tools. Handles mode-based filtering and dispatching.

**Mode restrictions:**

| Mode | Allowed Tools |
|------|---------------|
| **plan** | `ask_user`, `plan_tool`, `read_file`, `list_dir`, `glob_files`, `grep_search` |
| **research** | All plan tools + `web_search`, `papers`, `research`, `github_*` |
| **write** | All plan tools + `writing`, `web_search` (for citations), `papers` |
| **general** | All tools (no restrictions) |

**When a blocked tool is called:**
```
Tool 'bash' is not available in PLAN mode. 
Plan mode is for planning and asking questions only.
Suggest switching to research or write mode using ask_user with suggest_mode.
```

### 4. Doom Loop Detection (`agent/doom_loop.py`)

Detects when the agent gets stuck in repetitive patterns.

**Pattern 1: Identical consecutive calls**
```
bash(ls) → bash(ls) → bash(ls)  # 3+ identical = doom loop
```

**Pattern 2: Repeating sequences**
```
read_file(a) → edit_file(a) → read_file(a) → edit_file(a)  # A-B-A-B pattern
```

**Correction prompt injected:**
```
[DOOM LOOP DETECTED] You have called `bash` with identical arguments 3 times 
in a row. This is not making progress. Try a completely different approach:
- Use a different tool
- Change the arguments significantly
- Re-read the error message carefully
- Ask the user for help if you're stuck
```

### 5. Session Manager (`services/session_manager.py`)

Manages multiple concurrent conversations. Each conversation gets its own isolated session.

**Session lifecycle:**
1. Created on first message to a conversation
2. Persists across browser refreshes (messages in DB)
3. Destroyed when conversation deleted or server restart

**Per-session state:**
- `Session` — Message history, config, event callbacks
- `ToolRouter` — Registered tools, MCP connections
- `SandboxManager` — Docker containers, SSH connections

## Event Flow

All events are broadcast via Server-Sent Events (SSE):

```
User Message → processing → assistant_chunk (streaming) → tool_call → 
               tool_output → assistant_chunk → ... → turn_complete
```

| Event | Data | When |
|-------|------|------|
| `processing` | `{status: "thinking..."}` | Agent starts |
| `assistant_chunk` | `{chunk: "text"}` | Streaming tokens |
| `assistant_stream_end` | `{}` | Stream complete |
| `tool_call` | `{name, arguments}` | Tool invoked |
| `tool_output` | `{name, output}` | Tool returned |
| `questions` | `{questions: [...]}` | `ask_user` called |
| `plan_update` | `{tasks: [...]}` | Task list changed |
| `context_usage` | `{used, max, ratio}` | Token gauge |
| `turn_complete` | `{}` | Processing done |
| `error` | `{error: "..."}` | Error occurred |

## Configuration

Key settings in `AgentConfig`:

```python
@dataclass
class AgentConfig:
    model_name: str = ""                    # LLM to use
    max_iterations: int = 300               # Tool calls per turn
    stream: bool = True                     # Stream responses
    compact_threshold_ratio: float = 0.90   # Compact at 90%
    untouched_messages: int = 5             # Keep last N during compaction
    default_max_tokens: int = 200000        # Fallback context size
    yolo_mode: bool = False                 # Skip confirmations
```

## Extending the Harness

### Adding a new tool

```python
# In tools/my_tool.py
from ..agent.types import ToolSpec

MY_TOOL_SPEC = ToolSpec(
    name="my_tool",
    description="Does something useful",
    parameters={
        "type": "object",
        "properties": {
            "arg1": {"type": "string", "description": "First argument"},
        },
        "required": ["arg1"],
    },
)

async def my_tool(arg1: str) -> str:
    # Implementation
    return f"Result: {arg1}"

# In tools/registry.py, add to create_tool_router()
router.register(ToolSpec(...))
```

### Adding mode restrictions

```python
# In tools/registry.py
MODE_TOOL_RESTRICTIONS = {
    "my_mode": {
        "allowed": {"tool1", "tool2"},
        "blocked_message": "Tool '{tool}' not allowed in my_mode.",
    },
}
```

### Custom compaction logic

Override `ContextManager.compact()` to customize how old messages are summarized.

## Debugging

Enable debug logging:

```bash
LOG_LEVEL=DEBUG uvicorn openmlr.app:app
```

Key log messages:
- `[LLM] Model: ...` — Which model is being used
- `[DOOM LOOP DETECTED]` — Loop detected and corrected
- `Context nearing limit, compacting...` — Auto-compaction triggered
