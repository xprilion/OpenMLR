# Agent Tools

The agent has access to 18 built-in tools. Tools are invoked automatically
based on the task at hand.

## Filesystem

| Tool | Description |
|------|-------------|
| `bash` | Execute shell commands in a Docker container (falls back to host if Docker unavailable) |
| `read` | Read files with line numbers |
| `write` | Create/overwrite files |
| `edit` | Find-and-replace in files |

## Research

| Tool | Description |
|------|-------------|
| `papers` | Search OpenAlex, read ArXiv papers, get citations, find code/datasets |
| `web_search` | Brave web search |
| `research` | Spawn an independent research sub-agent with its own context |
| `github_read_file` | Read files from GitHub repos |
| `github_list_repos` | List repos for a user/org |
| `github_find_examples` | Search GitHub for code examples |

### Papers operations

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

## Planning & interaction

| Tool | Description |
|------|-------------|
| `plan_tool` | Create/update task plans, track resources, generate completion reports |
| `ask_user` | Ask structured questions (2-4 options + free text per question) |
| `writing` | Manage paper writing projects (outline, sections, bibliography, export) |

## Execution environments

| Tool | Description |
|------|-------------|
| `sandbox_probe` | Check environment (Python version, GPU, disk, packages) |
| `sandbox_create` | Create a new sandbox (local/SSH/Modal) |
| `sandbox_exec` | Run commands in active sandbox |
| `sandbox_read` / `sandbox_write` | File I/O in sandbox |
