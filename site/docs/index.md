---
layout: home
hero:
  name: OpenMLR
  text: ML Research Agent
  tagline: Plans tasks, researches papers, writes drafts, and executes code — end to end, in one conversation.
  actions:
    - theme: brand
      text: Get Started
      link: /setup
    - theme: alt
      text: View on GitHub
      link: https://github.com/xprilion/OpenMLR
features:
  - title: Plan
    details: Ask clarifying questions, gather context, break tasks into structured plans. No execution until you're ready.
  - title: Execute
    details: Research papers, write drafts, run code. All tools available. Follows the plan you built in Plan mode.
---

## Quick start

```bash
git clone https://github.com/xprilion/OpenMLR.git
cd OpenMLR
cp .env.example .env   # Add your API keys
docker compose up -d
```

Open `http://localhost:3000`. Create an account. Start researching.

### One-click deploy

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/xprilion/OpenMLR)

[![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://www.heroku.com/deploy?template=https://github.com/xprilion/OpenMLR)

See [Setup & Installation](/setup) for local development and more options.

## How it works

OpenMLR uses two modes to keep the agent focused:

- **Plan mode (P)** — The agent asks questions, gathers context, and creates structured plans. No code execution, no file writes. Toggle with `Cmd+B`. Messages have an amber border.
- **Execute mode (E)** — The agent does the work: researches papers, writes drafts, runs experiments. All tools available. Toggle with `Cmd+E`. Messages have a blue border.

Switch modes with the P/E button in the input area or keyboard shortcuts. The agent follows the plan built during Plan mode.

## Key features

- **Paper research** — OpenAlex, ArXiv, CrossRef, Papers With Code. Full paper reading, citation graphs.
- **Paper writing** — Section-by-section drafting with auto-save. Preview + export (Markdown/LaTeX) in the Paper tab.
- **Sub-agent streaming** — Research tool spawns independent agents with nested tool call visibility.
- **Background jobs** — Celery + Redis. Close the browser, come back later.
- **Per-conversation parallelism** — Multiple conversations process simultaneously.
- **Onboarding flow** — Guided setup when no LLM provider is configured.
