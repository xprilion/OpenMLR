---
title: Projects & Workspaces - OpenMLR
description: Persistent project workspaces in OpenMLR. Knowledge graphs, file trees, interactive terminals, and cross-conversation persistence for ML research.
---

# Projects & Workspaces

Projects are the central organizing unit in OpenMLR. A project provides a persistent workspace where all research artifacts -- papers, code, data, notes, experiment logs, and a knowledge graph -- accumulate across multiple conversations.

## Overview

| Concept | Description |
|---------|-------------|
| **Project** | A named research initiative (e.g., "Attention Mechanism Survey") |
| **Workspace** | The filesystem directory backing a project, stored in a Docker volume |
| **Knowledge Graph** | A lightweight graph of entities and relationships, persisted as JSON |
| **Conversation** | A chat session; multiple conversations can belong to one project |

### Key Principle: Workspace vs. Compute

The workspace and compute resource are **decoupled**:

- **Workspace** (persistent, local): Always available. Stores all project files. Survives compute changes and new conversations.
- **Compute** (swappable): Only used for code execution. Can be local Docker, SSH remote, or Modal cloud. Changing compute does not affect workspace files.

## Creating a Project

Projects are **mandatory** -- every conversation must belong to a project. New users create their first project during onboarding (after selecting an LLM provider and model).

To create additional projects:

1. Click the project selector dropdown in the header
2. Click "New Project"
3. Enter a name and optional description
4. A workspace directory is created automatically, and a new conversation is started in the project

## Workspace Directory Structure

```
.workspaces/
  my-project/
    code/                   # Scripts, notebooks, source code
    data/                   # Downloaded datasets
    models/                 # Trained models, checkpoints
    outputs/                # Experiment results, plots, figures
    papers/                 # Paper drafts (auto-saved by writing tool)
    research/
      searches/             # Saved search results (JSON)
      notes/                # Agent-generated research notes (.md)
      citations/            # Bibliography, references
    logs/
      tool_failures/        # Timestamped logs of failed tools/APIs
      compute/              # Compute probe results
      experiments/          # Experiment execution logs
    venvs/                  # Python virtual environments
    .project-meta/
      project.json          # Project metadata
      knowledge.json        # Knowledge graph (networkx JSON)
      state.json            # Cross-conversation state
      plans/                # Task plans per conversation
```

## Knowledge Graph

Each project has a lightweight knowledge graph powered by [networkx](https://networkx.org/). The graph stores entities and their relationships, enabling cross-conversation knowledge accumulation.

### Entity Types

| Type | Description | Example |
|------|-------------|---------|
| `paper` | Research paper | "Attention Is All You Need" |
| `concept` | Abstract concept | "Self-attention" |
| `method` | Technique or algorithm | "Multi-head attention" |
| `dataset` | Dataset | "WMT 2014 EN-DE" |
| `finding` | Research finding | "Attention outperforms RNNs on translation" |
| `question` | Open research question | "Does attention scale to 1B params?" |
| `experiment` | Experiment run | "BLEU comparison on WMT" |
| `tool` | Software tool | "PyTorch" |
| `author` | Researcher | "Vaswani et al." |
| `code_artifact` | Code implementation | "transformer.py" |

### Relationship Types

| Relationship | Description |
|-------------|-------------|
| `cites` | Paper cites another paper |
| `proposes` | Paper proposes a method |
| `implements` | Code implements a method |
| `evaluates_on` | Experiment uses a dataset |
| `introduces` | Paper introduces a dataset |
| `relates_to` | General association |
| `answers` | Finding answers a question |
| `depends_on` | Method/code depends on another |
| `uses` | Experiment uses a method |
| `produces` | Experiment produces a finding |
| `contradicts` | Finding contradicts another |
| `extends` | Method extends another |

### Agent Usage

The agent uses the `workspace` tool to interact with the knowledge graph:

```
workspace knowledge_add entity_id="attention-paper" entity_type="paper" label="Attention Is All You Need"
workspace knowledge_add entity_id="mha" entity_type="method" label="Multi-Head Attention"
workspace knowledge_relate source_id="attention-paper" target_id="mha" relationship="proposes"
workspace knowledge_summary   # Get full graph context
```

## Cross-Conversation Persistence

When you start a new conversation within a project, the agent can:

1. Read the knowledge graph summary to understand prior work
2. Check recent tool failures to avoid known issues
3. Review research notes from previous conversations
4. Build on existing code and data in the workspace

This is powered by the `.project-meta/state.json` file, which tracks:
- Key findings across conversations
- Open research questions
- Active experiments

## File Tree

The right panel includes a **Files** tab (visible when a project is active) that shows the workspace directory tree. You can:

- Browse directories
- View file contents
- See file sizes and types

## Interactive Terminal

A terminal panel at the bottom of the screen provides a real shell connected to the project workspace directory. Use it for:

- Quick file inspections
- Running one-off commands
- Interactive debugging
- Package management

The terminal connects to the workspace directory regardless of which compute resource is selected.

## Docker Volume

Project workspaces are stored in a Docker volume that persists across container rebuilds:

**Development** (`docker-compose.yml`):
```yaml
volumes:
  workspaces:  # Named volume
```

**Production** (`docker-compose.prod.yml`):
```yaml
volumes:
  - ${OPENMLR_WORKSPACES_PATH:-./.workspaces}:/app/.workspaces
```

For production, set `OPENMLR_WORKSPACES_PATH` in your `.env` to a bind mount location for easy backup.

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/projects` | GET | List projects |
| `/api/projects` | POST | Create project |
| `/api/projects/:uuid` | GET | Project details |
| `/api/projects/:uuid` | PUT | Update project |
| `/api/projects/:uuid` | DELETE | Archive project |
| `/api/projects/:uuid/conversations` | GET | List project conversations |
| `/api/projects/:uuid/attach/:conv_uuid` | POST | Attach conversation |
| `/api/projects/:uuid/detach/:conv_uuid` | POST | Detach conversation |
| `/api/projects/:uuid/files` | GET | List workspace files |
| `/api/projects/:uuid/files/:path` | GET | Read file |
| `/api/projects/:uuid/files/:path` | PUT | Write file |
| `/api/projects/:uuid/files/:path` | DELETE | Delete file |
| `ws://host/api/terminal/:uuid` | WS | Interactive terminal |
