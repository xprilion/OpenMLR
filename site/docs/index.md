---
title: OpenMLR - AI-Powered ML Research Agent
description: OpenMLR plans tasks, researches papers, writes drafts, and executes code end-to-end in one conversation. Open source ML research assistant.
layout: home
hero:
  name: OpenMLR
  text: ML Research Agent
  tagline: Plans tasks, researches papers, writes drafts, and executes code — end to end, in one conversation.
  actions:
    - theme: brand
      text: Quick Start
      link: /quickstart
    - theme: alt
      text: View on GitHub
      link: https://github.com/xprilion/OpenMLR
features:
  - title: Plan
    details: Ask clarifying questions, gather context, break tasks into structured plans. No execution until you're ready.
  - title: Execute
    details: Research papers, write drafts, run code. All tools available. Follows the plan you built in Plan mode.
  - title: MCP Servers
    details: Connect remote MCP servers with custom authentication. Configure per-server mode availability. Live connection status. Reference servers with @ mentions.
---

## Quick Start

```bash
git clone https://github.com/xprilion/OpenMLR.git
cd OpenMLR
cp .env.example .env
make up
```

Open `http://localhost:3000`. Create an account. Configure API keys in **Settings > Providers**.

> No API keys needed to start — the app guides you through setup after login.

### One-Click Deploy

<div style="display: flex; gap: 10px; margin-top: 10px;">
  <a href="https://render.com/deploy?repo=https://github.com/xprilion/OpenMLR" target="_blank" rel="noopener">
    <img src="https://render.com/images/deploy-to-render-button.svg" alt="Deploy to Render" width="146" height="32">
  </a>
  <a href="https://www.heroku.com/deploy?template=https://github.com/xprilion/OpenMLR" target="_blank" rel="noopener">
    <img src="https://www.herokucdn.com/deploy/button.svg" alt="Deploy to Heroku" width="196" height="32">
  </a>
</div>

See [Quick Start](/quickstart) for all deployment options or [Setup & Installation](/setup) for detailed instructions.

## How It Works

OpenMLR uses two modes to keep the agent focused:

- **Plan mode (P)** — The agent asks questions, gathers context, and creates structured plans. No code execution, no file writes. Messages have an amber border.
- **Execute mode (E)** — The agent does the work: researches papers, writes drafts, runs experiments. All tools available. Messages have a blue border.

Switch modes with the **P/E button** in the input area or press **Cmd+M** (Mac) / **Ctrl+M** (Windows/Linux) to toggle.

## Key Features

- **Paper research** — OpenAlex, Semantic Scholar, arXiv, CrossRef, Papers With Code. Full paper reading, citation graphs.
- **Paper writing** — Section-by-section drafting with auto-save. Preview + export (Markdown/LaTeX) in the Paper tab.
- **MCP servers** — Connect remote HTTP/HTTPS MCP servers with custom auth. Per-server mode config, live connection status, @ mentions.
- **@ mentions** — Type `@` in the chat to reference MCP servers or workspace files. The agent uses its tools to interact with the referenced resources.
- **Sub-agent streaming** — Research tool spawns independent agents with nested tool call visibility.
- **Background jobs** — Celery + Redis. Close the browser, come back later.
- **Per-conversation parallelism** — Multiple conversations process simultaneously.
- **Onboarding flow** — Guided setup when no LLM provider is configured.
