# Quick Start

Get OpenMLR up and running in less than 2 minutes.

## 1. Get the code
```bash
git clone https://github.com/xprilion/OpenMLR.git
cd OpenMLR
```

## 2. Configure Environment
Create a `.env` file from the example:
```bash
cp .env.example .env
```
Open `.env` and add at least one LLM API key:
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `OPENROUTER_API_KEY`

## 3. Launch
```bash
docker compose up -d
```

## 4. Access
- **URL**: [http://localhost:3000](http://localhost:3000)
- **Login**: Create your account on the first visit.
- **Modes**: Use **Plan Mode** (`Cmd+B`) to research and **Execute Mode** (`Cmd+E`) to write code and papers.

---

### What's next?
- [Setup & Installation](/setup) for local development without Docker.
- [Configuration](/configuration) for advanced options.
- [Agent Harness](/agent-harness) to learn how the agent works.
