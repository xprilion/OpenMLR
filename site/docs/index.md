---
layout: home
hero:
  name: OpenMLR
  text: ML Research Intern
  tagline: Plans tasks, reads papers, writes drafts, and runs experiments — end to end.
  actions:
    - theme: brand
      text: Get Started
      link: /setup
    - theme: alt
      text: View on GitHub
      link: https://github.com/xprilion/OpenMLR
features:
  - title: Plan
    details: Structured questions with options, task breakdown, scope clarification before any work begins.
  - title: Research
    details: Search OpenAlex, ArXiv, CrossRef. Read papers section-by-section. Crawl citation graphs. Find code on GitHub.
  - title: Write
    details: Section-by-section paper drafting with bibliography management and Markdown/LaTeX export.
  - title: Execute
    details: Docker-isolated code execution locally, on SSH remotes, or Modal cloud sandboxes.
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

See [Setup & Installation](/setup) for Coolify, local development, and more options.

## Why OpenMLR?

Ever started researching a topic, opened 47 browser tabs, took notes in three different apps, lost track of that one paper you saw yesterday, and then had to context-switch to run some experiments?

OpenMLR keeps everything in one place. Your research context stays with you from the first "what should I look into?" to the final PDF export.

**No more:**
- Lost tabs and forgotten citations
- Copy-pasting between arxiv, notes, and code
- "Where did I see that figure?"
- Starting over because you closed your browser

## How it works

```
Plan → Research → Write → Execute
```

Each mode restricts which tools are available, keeping the agent focused:

| Mode | What it does | Tools available |
|------|--------------|-----------------|
| **Plan** | Asks clarifying questions, breaks down tasks | Questions, task tracking |
| **Research** | Searches papers, crawls citations | OpenAlex, ArXiv, web search, GitHub |
| **Write** | Drafts sections, manages bibliography | Writing tools, citation lookup |
| **Execute** | Runs code when needed | Docker, SSH, Modal (available in all modes) |

The agent can suggest switching modes, but you approve the switch. No more half-baked drafts with missing citations.
