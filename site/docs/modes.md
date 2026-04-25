# Modes

OpenMLR uses three per-message modes. Switch modes using the selector above
the input area. Code execution is available in all modes.

## Plan mode

**Purpose**: Clarify scope before doing work.

The agent will:
- Ask structured questions using a bottom drawer UI (2-4 options + free text)
- Break tasks into a plan visible in the right panel
- Not execute code or modify files
- Suggest switching to Research or Write mode when ready

## Research mode

**Purpose**: Find and synthesize information.

The agent will:
- Search papers via OpenAlex, ArXiv, CrossRef
- Read full paper sections from ar5iv HTML
- Crawl citation graphs and find related work
- Search GitHub for code examples
- Track all papers/resources in the right panel
- Respect the per-session search budget (default 25 API calls)

### Search budget

Each session has a limited number of paper API calls to prevent endless
searching. The budget is shown in the right panel. When exhausted, the agent
must ask the user before continuing.

## Write mode

**Purpose**: Draft academic content.

The agent will:
- Write paper sections using the `writing` tool
- Manage citations and bibliography
- Reference completion reports from the research phase
- Export to Markdown or LaTeX

## Task management

The right panel shows:
- **Tasks**: Plan items with status (pending → in progress → completed)
- **Resources**: Papers, code repos, datasets, and completion reports

When a task is marked completed, a **completion report** is auto-generated
with a summary and hints for upcoming tasks. Click report titles in the
resources list to view them in a slide-out drawer.

### Completion reports

Reports follow a markdown spec:

```markdown
# Task Completion Report: [task title]
**Completed**: [timestamp]
## Summary
[what was accomplished]
## Next Steps
[recommendations for upcoming tasks]
```

The agent re-reads these reports to maintain context across compactions.

## Context tracking

The right panel shows a token usage gauge. When approaching the model's
context window limit, the system auto-compacts the conversation by summarizing
older messages. The gauge color changes: green → yellow → red.
