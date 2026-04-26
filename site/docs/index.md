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
---

## Quick Start

```bash
git clone https://github.com/xprilion/OpenMLR.git
cd OpenMLR
cp .env.example .env
docker compose up -d
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

- **Plan mode (P)** — The agent asks questions, gathers context, and creates structured plans. No code execution, no file writes. Toggle with `Cmd+B`. Messages have an amber border.
- **Execute mode (E)** — The agent does the work: researches papers, writes drafts, runs experiments. All tools available. Toggle with `Cmd+E`. Messages have a blue border.

Switch modes with the P/E button in the input area or keyboard shortcuts.

## Key Features

- **Paper research** — OpenAlex, ArXiv, CrossRef, Papers With Code. Full paper reading, citation graphs.
- **Paper writing** — Section-by-section drafting with auto-save. Preview + export (Markdown/LaTeX) in the Paper tab.
- **Sub-agent streaming** — Research tool spawns independent agents with nested tool call visibility.
- **Background jobs** — Celery + Redis. Close the browser, come back later.
- **Per-conversation parallelism** — Multiple conversations process simultaneously.
- **Onboarding flow** — Guided setup when no LLM provider is configured.
