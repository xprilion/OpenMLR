---
title: Agent Tools Reference - OpenMLR
description: Complete reference for OpenMLR agent tools. Planning, research, filesystem, paper writing, and code execution tools with mode availability.
---

# Agent Tools

The agent has access to built-in tools organized by category. Tool availability depends on the current [mode](/modes).

## Planning Tools

| Tool | Description | Plan | Execute |
|------|-------------|:----:|:-------:|
| `ask_user` | Ask structured questions (2-4 options + free text per question) | yes | no |
| `plan_tool` | Create/update task plans, track resources, generate completion reports. In Execute mode, `create` and `add` operations require user approval. | yes | yes |

## Research Tools

| Tool | Description | Plan | Execute |
|------|-------------|:----:|:-------:|
| `papers` | Search papers, read ArXiv, get citations, find code/datasets | yes | yes |
| `web_search` | Brave web search | yes | yes |
| `research` | Spawn an independent research sub-agent with its own context | no | yes |
| `github_read_file` | Read files from GitHub repos | yes | yes |
| `github_list_repos` | List repos for a user/org | yes | yes |
| `github_find_examples` | Find code examples by filename pattern | yes | yes |
| `github_search_repos` | Search GitHub repositories by query | yes | yes |
| `github_get_readme` | Get README from a repository | yes | yes |

### Papers Operations

| Operation | Source | Description |
|-----------|--------|-------------|
| `search` | OpenAlex | Full-text search with year/citation filters (primary) |
| `arxiv_search` | arXiv | Search arXiv directly — best for ML/CS/Physics preprints |
| `semantic_search` | Semantic Scholar | Search with abstracts, good for recent papers |
| `trending` | OpenAlex | Recent highly-cited papers |
| `details` | OpenAlex + CrossRef | Full metadata, abstract, OA links |
| `read_paper` | arXiv (ar5iv) | Parse HTML into sections, read by name/number |
| `citations` | OpenAlex | References + cited-by with batch fetching |
| `recommend` | OpenAlex | Related works |
| `author_papers` | OpenAlex | Papers by a specific author |
| `find_code` | Papers With Code | GitHub repos linked to papers |
| `find_datasets` | Papers With Code | Datasets linked to papers |

::: tip Search source recommendations
- **arXiv search**: Latest ML/AI preprints, CS research, physics papers
- **OpenAlex search**: Broad academic coverage across all fields, great for citation data
- **Semantic Scholar**: When you need abstracts or Semantic Scholar IDs
:::

### Research Sub-Agent

The `research` tool spawns an independent sub-agent with its own context window. The parent agent sees nested tool calls streamed in real-time. Useful for deep dives that would consume too much of the main conversation's context.

## Writing Tool

| Tool | Description | Plan | Execute |
|------|-------------|:----:|:-------:|
| `writing` | Paper authoring — manage outline, write sections, update bibliography | no | yes |

The writing tool manages a **writing project** stored in the database:
- **Outline**: Define paper structure (sections, subsections)
- **Sections**: Write/update individual sections with auto-save
- **Bibliography**: Manage citations and references
- **Auto-save**: All changes persist to the database immediately, surviving across workers and restarts

Paper preview and client-side export (Markdown/LaTeX) are available in the **Paper tab** in the UI.

## Filesystem Tools

| Tool | Description | Plan | Execute |
|------|-------------|:----:|:-------:|
| `read` | Read files with line numbers | yes | yes |
| `write` | Create/overwrite files | no | yes |
| `edit` | Find-and-replace in files | no | yes |
| `inspect_files` | Parallel file reading with relevance filtering | yes | yes |
| `list_dir` | List directory contents | yes | yes |
| `glob_files` | Find files by glob pattern | yes | yes |
| `grep_search` | Search file contents | yes | yes |

In Plan mode, only read-only filesystem tools are available.

### inspect_files

The `inspect_files` tool reads multiple files or entire directories concurrently and scores each file for relevance against a query. Useful when the agent needs to scan a directory to find which files are relevant without reading them one by one.

- Expands directories to file listings (hidden files excluded)
- Reads all files in parallel via `asyncio.gather`
- Scores relevance by keyword overlap with the query
- Returns relevant files with content, skips low-relevance files
- Safety limits: 50 files max, 200 lines per file, 2MB file-size gate

## Execution Tools

| Tool | Description | Plan | Execute |
|------|-------------|:----:|:-------:|
| `bash` | Execute shell commands (Docker-isolated when available) | no | yes |
| `sandbox` | Run code in Docker containers, SSH remotes, or Modal cloud | no | yes |

### Sandbox Types

| Type | Description |
|------|-------------|
| **Local (Docker)** | Docker container on the host machine |
| **SSH** | Remote machine via SSH |
| **Modal** | Cloud sandbox via Modal |

## Workspace Tools

| Tool | Description | Plan | Execute |
|------|-------------|:----:|:-------:|
| `workspace` | Project workspace operations — knowledge graph, notes, search, failure logs | yes | yes |

### Workspace Operations

| Operation | Description |
|-----------|-------------|
| `status` | View workspace summary (file counts, knowledge graph size, recent failures) |
| `search` | Search files by name or content |
| `note` | Save a research note with topic and content |
| `knowledge_add` | Add entity to the knowledge graph |
| `knowledge_relate` | Add relationship between entities |
| `knowledge_query` | Search entities in the knowledge graph |
| `knowledge_summary` | Get full knowledge graph context for the conversation |
| `recent_failures` | View recent tool/API failure logs |

See [Projects & Workspaces](/projects) for details on the knowledge graph entity and relationship types.

## Mode Restrictions

Tools are filtered based on the current mode before being sent to the LLM. See [Modes](/modes) for details on the enforcement layers.

In summary:
- **Plan mode**: `ask_user`, `plan_tool`, `workspace`, read-only filesystem, `inspect_files`, web search, papers, GitHub, HuggingFace, compute planning, and MCP tools configured for Plan mode
- **Execute mode**: Everything except `ask_user`, plus MCP tools configured for Execute mode
- **MCP tools**: Filtered by the per-server mode configuration set in Settings > MCP Servers (default: both modes)
