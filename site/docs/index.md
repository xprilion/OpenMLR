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
      link: https://github.com/xprilion/open-mlr
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

## What is OpenMLR?

OpenMLR is a self-hosted AI research assistant that works like an ML research
intern. It plans, researches, writes, and executes ML tasks end-to-end using
structured workflows and real tool access.

### Key capabilities

- **Structured planning** — the agent asks clarifying questions with 2-4 options
  (plus free-text) before starting work, then builds a task list
- **Paper research** — searches OpenAlex (250M+ works), reads full papers from
  ArXiv, crawls citation graphs, finds related code and datasets
- **Academic writing** — drafts papers section-by-section with inline citations,
  manages bibliography, exports to Markdown or LaTeX
- **Code execution** — runs commands in Docker containers for isolation, with
  SSH and Modal cloud sandbox support
- **Task management** — right-side panel tracks tasks and resources; completion
  reports auto-generated when tasks finish
- **Context awareness** — tracks token usage, auto-compacts when approaching
  model limits, manages search budgets
- **Multi-provider LLMs** — OpenAI, Anthropic, OpenRouter, plus litellm for 100+ models
