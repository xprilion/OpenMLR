# Agent Tools

The agent has access to built-in tools organized by category. Tool availability depends on the current [mode](/modes).

## Planning Tools

| Tool | Description | Plan | Execute |
|------|-------------|:----:|:-------:|
| `ask_user` | Ask structured questions (2-4 options + free text per question) | yes | no |
| `plan_tool` | Create/update task plans, track resources, generate completion reports | yes | yes |

## Research Tools

| Tool | Description | Plan | Execute |
|------|-------------|:----:|:-------:|
| `papers` | Search OpenAlex, read ArXiv papers, get citations, find code/datasets | yes | yes |
| `web_search` | Brave web search | yes | yes |
| `research` | Spawn an independent research sub-agent with its own context | no | yes |
| `github_search` | Search GitHub for repos and code | yes | yes |
| `github_read` | Read files from GitHub repos | yes | yes |

### Papers Operations

| Operation | Source | Description |
|-----------|--------|-------------|
| `search` | OpenAlex | Full-text search with year/citation filters |
| `trending` | OpenAlex | Recent highly-cited papers |
| `details` | OpenAlex + CrossRef | Full metadata, abstract, OA links |
| `read_paper` | ArXiv (ar5iv) | Parse HTML into sections, read by name/number |
| `citations` | OpenAlex | References + cited-by with batch fetching |
| `recommend` | OpenAlex | Related works |
| `find_code` | Papers With Code | GitHub repos linked to papers |
| `find_datasets` | Papers With Code | Datasets linked to papers |

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
| `list_dir` | List directory contents | yes | yes |
| `glob_files` | Find files by glob pattern | yes | yes |
| `grep_search` | Search file contents | yes | yes |

In Plan mode, only read-only filesystem tools are available.

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

## Mode Restrictions

Tools are filtered based on the current mode before being sent to the LLM. See [Modes](/modes) for details on the enforcement layers.

In summary:
- **Plan mode**: `ask_user`, `plan_tool`, read-only filesystem, web search, papers, GitHub
- **Execute mode**: Everything except `ask_user`
