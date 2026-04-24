# Open-MLR

An AI assistant for machine learning engineering. Open-MLR autonomously researches, writes, and runs ML code — with direct access to documentation, GitHub repos, and your local filesystem.

## Features

- **Web UI** — Modern React-based chat interface with streaming responses, syntax highlighting, and dark mode
- **Multiple providers** — OpenAI, Anthropic, and OpenRouter support
- **Local tools** — `bash`, `read`, `write`, `edit` for direct filesystem operations
- **GitHub integration** — Search repos, find examples, read files
- **Research sub-agent** — Spawn independent research tasks without polluting the main context
- **Project-level config** — Each project stores its own model preference in `.open-mlr.config.json`
- **Streaming** — Real-time token streaming via SSE
- **Approval system** — Review tool calls before execution (with YOLO mode)
- **Context compaction** — Automatic summarization when context grows large

## Quick Start

### Prerequisites

- [Bun](https://bun.sh) (v1.1+)

### Installation

```bash
git clone git@github.com:xprilion/open-mlr.git
cd open-mlr
bun run install:all
```

### Configuration

Create a `.env` file in the project root:

```bash
# Required: at least one of these
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OPENROUTER_API_KEY=sk-or-...

# Optional
GITHUB_TOKEN=ghp_...
```

### Running

**Production:**
```bash
bun run build      # Build the frontend
bun run start      # Start the server on port 3000
```

**Development:**
```bash
bun run dev        # Starts both server and Vite dev server with hot reload
```

Then open `http://localhost:3000`.

## Usage

### Chat interface

Type messages in the chat box. The assistant will respond with streaming text and can invoke tools automatically.

### Model switching

Click the model name in the top-right header to open the model picker. Your choice is saved per-project in `.open-mlr.config.json`.

### Actions

The left sidebar provides quick actions:
- **Undo** — Remove the last turn
- **Compact** — Summarize old context to save tokens

### Tool approval

When the assistant makes tool calls, an approval modal appears. Click **Yes**, **No**, or **Yolo** (always approve).

## Model prefixes

| Provider | Prefix | Example |
|----------|--------|---------|
| OpenAI | `openai/` | `openai/gpt-4o` |
| Anthropic | `anthropic/` | `anthropic/claude-sonnet-4` |
| OpenRouter | `openrouter/` | `openrouter/openai/gpt-4o` |

Bare model names (e.g. `gpt-4o`) default to OpenAI.

## Project config

Open-MLR creates `.open-mlr.config.json` in the current working directory to store project-level preferences like the selected model. This file is gitignored by default.

```json
{
  "model_name": "anthropic/claude-sonnet-4"
}
```

## Architecture

```
┌──────────────────────────────────────┐
│           React Frontend             │
│     (Vite + SSE streaming)           │
└──────────────────┬───────────────────┘
                   │ HTTP / SSE
┌──────────────────▼───────────────────┐
│           Bun HTTP Server            │
│  ┌────────────────────────────────┐  │
│  │  Session + Agent Loop          │  │
│  │  • ContextManager              │  │
│  │  • ToolRouter                  │  │
│  │  • LLM (OpenAI/Anthropic)      │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

## Tech Stack

- **Backend**: Bun, TypeScript, OpenAI SDK, `ai` SDK (Anthropic)
- **Frontend**: React 19, Vite, react-markdown, remark-gfm
- **LLM Providers**: OpenAI, Anthropic, OpenRouter

## License

MIT
