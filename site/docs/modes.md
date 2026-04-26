# Modes

OpenMLR uses two modes — **Plan** and **Execute** — to keep the agent focused on the right kind of work.

## Plan Mode (P)

**Purpose**: Gather context, ask questions, create structured plans before doing any work.

**What the agent can do:**
- Ask clarifying questions via `ask_user` (structured options UI)
- Create and update task plans via `plan_tool`
- Read files and search the codebase (read-only filesystem tools)
- Search the web and papers for context
- Generate `PLAN.md` and pin it in resources

**What the agent cannot do:**
- Write or edit files
- Execute code (bash, sandbox)
- Write paper sections
- Use the `research` sub-agent

**Visual indicator**: Messages have an **amber border**.

**When to use**: Start here. Let the agent understand the problem, ask questions, and build a plan before switching to Execute.

## Execute Mode (E)

**Purpose**: Do the work. Follow the plan built in Plan mode.

**What the agent can do:**
- All tools except `ask_user`
- Research papers, crawl citations, spawn sub-agents
- Write and edit files
- Draft paper sections with auto-save
- Run code in bash or sandboxes (Docker/SSH/Modal)

**What the agent cannot do:**
- Use `ask_user` (no structured questions — it should be working, not asking)

**Visual indicator**: Messages have a **blue border**.

**When to use**: Once you have a plan and the agent knows what to do.

## Switching Modes

| Method | Action |
|--------|--------|
| **P/E button** | Click the mode toggle above the input area |
| **Cmd+B** | Switch to Plan mode |
| **Cmd+E** | Switch to Execute mode |

The mode applies per-message. You can switch freely between messages.

## Mode Enforcement

Mode restrictions are enforced at three layers:

1. **System prompt** — The agent is instructed about what it can and cannot do in the current mode
2. **Tool filtering** — The tool router only presents mode-allowed tools to the LLM
3. **Runtime blocking** — If a tool call somehow bypasses filtering, the router returns an error message instead of executing

When a blocked tool is called, the agent receives:
```
Tool 'bash' is not available in PLAN mode.
Plan mode is for planning and asking questions only.
```

## PLAN.md

When the agent creates a plan in Plan mode, it auto-generates a `PLAN.md` file that is pinned in the resources panel. This plan persists across context compactions and serves as the agent's reference during Execute mode.
