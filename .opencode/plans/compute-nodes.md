# Design Document: Compute Node Ecosystem & Workspace Isolation

**Status:** Draft  
**Author:** OpenCode Agent  
**Date:** 2026-04-26  

---

## 1. Goals

1. **Secure SSH/LAN compute node management** with host-key verification, key-based auth, and per-node credential pairing.
2. **Filesystem isolation** via a per-conversation workspace at `~/.openmlr/workspace-{conv-uuid}`.
3. **Per-conversation compute binding** (sticky default + per-convo override), matching the existing model-selection UX pattern.
4. **Agent-aware compute planning** — the agent can inspect available nodes, match tasks to capabilities, and execute remotely with streamed results.
5. **Zero auto-discovery** — all nodes are added manually.

---

## 2. Non-Goals

- Auto-discovery via mDNS/Zeroconf (explicitly out of scope).
- Kubernetes or Slurm cluster management.
- Billing/cost tracking for cloud nodes.

---

## 3. Terminology

| Term | Meaning |
|------|---------|
| **Compute Node** | A target execution environment: local workspace, SSH remote, or Modal sandbox. |
| **Key Asset** | An SSH private key stored on disk in `.keys/`. Metadata (filename, fingerprint, associated nodes) lives in the DB. |
| **Workspace** | A dedicated directory `~/.openmlr/workspace-{conv-uuid}` mounted into all local executions for that conversation. |
| **Active Compute** | The compute node currently bound to a conversation. Defaults to the user's sticky default; can be overridden per conversation. |

---

## 4. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                     Frontend (React)                          │
│  Chat Header: [Model] + [Compute] selectors                  │
│  Settings > Compute Nodes: CRUD, key pairing, health checks  │
└──────────────────────────┬───────────────────────────────────┘
                           │ REST + SSE
┌──────────────────────────▼───────────────────────────────────┐
│                     Backend (FastAPI)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │ KeyManager   │  │ ComputeNode  │  │ Workspace    │        │
│  │ (.keys dir)  │  │ Registry     │  │ Manager      │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
│         │                 │                  │               │
│         ▼                 ▼                  ▼               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              SessionManager (per-conv)                  │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │  │
│  │  │   Agent     │  │   Tool      │  │  Sandbox    │    │  │
│  │  │   Session   │──│   Router    │──│  Manager    │    │  │
│  │  │             │  │             │  │ (active)    │    │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘    │  │
│  └────────────────────────────────────────────────────────┘  │
│         │                                    │               │
│         ▼                                    ▼               │
│  ┌──────────────┐                 ┌──────────────────────┐   │
│  │  PostgreSQL  │                 │  Local / SSH / Modal │   │
│  │   (metadata) │                 │    Compute Nodes     │   │
│  └──────────────┘                 └──────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

---

## 5. Key Asset Management (`.keys/`)

### 5.1 Directory Layout

```
<project-root>/.keys/
├── id_ed25519_workstation
├── id_ed25519_workstation.pub
├── id_rsa_labserver
├── id_rsa_labserver.pub
└── .gitignore  # ignores everything (keys must NEVER be committed)
```

The `.keys/` directory is created on first run. It is mounted into the backend container via Docker Compose volume:

```yaml
volumes:
  - ./.keys:/app/.keys:ro  # read-only in container; write via API
```

### 5.2 Key Lifecycle

| Action | User Flow | Backend Behavior |
|--------|-----------|------------------|
| **Upload** | User pastes or uploads a private key in Settings > Compute > Keys | Backend writes to `.keys/{filename}` with `0o600` permissions; stores `{filename, fingerprint, algorithm, comment, created_at}` in `ssh_keys` table |
| **Generate** | User clicks "Generate Key Pair" | Backend runs `ssh-keygen -t ed25519 -f .keys/{name} -C "openmlr-{user_id}@{timestamp}"`; stores metadata |
| **Delete** | User clicks "Delete" | Backend deletes file from `.keys/` and all `compute_node` rows referencing it; warns if nodes will break |
| **List** | Settings page loads | Backend returns metadata (no private key content ever transmitted) |

### 5.3 Security

- **Filesystem**: Private keys are written with `0o600`, directory with `0o700`.
- **Network**: Private key content is NEVER returned in API responses. Only filenames, fingerprints, and public key content are exposed.
- **Validation**: Uploaded keys are validated with `cryptography` library before writing.

---

## 6. Compute Node Registry

### 6.1 Database Schema

**`compute_nodes` table** (new)

```sql
CREATE TABLE compute_nodes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,           -- e.g. "Workstation", "Lab Server"
    type VARCHAR(20) NOT NULL,            -- "local", "ssh", "modal"
    config JSONB NOT NULL DEFAULT '{}',   -- host, port, username, key_filename, workdir, etc.
    capabilities JSONB DEFAULT '{}',      -- cached probe results
    health_status VARCHAR(20) DEFAULT 'unknown', -- online, offline, degraded, unknown
    last_probed_at TIMESTAMP WITH TIME ZONE,
    last_seen_at TIMESTAMP WITH TIME ZONE,
    is_default BOOLEAN DEFAULT FALSE,
    priority INTEGER DEFAULT 0,           -- fallback ordering
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, name)
);
```

**`ssh_keys` table** (new)

```sql
CREATE TABLE ssh_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL UNIQUE,
    fingerprint VARCHAR(255) NOT NULL,    -- SHA256 fingerprint
    algorithm VARCHAR(50) NOT NULL,       -- ssh-ed25519, rsa, etc.
    public_key TEXT NOT NULL,
    comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 6.2 Config JSONB Structure

```json
{
  "host": "ml-workstation.local",
  "port": 22,
  "username": "researcher",
  "key_filename": "id_ed25519_workstation",
  "workdir": "/home/researcher/openmlr-workspaces",
  "host_key_fingerprint": "SHA256:abc123...",
  "jump_host": null,
  "timeout_seconds": 30,
  "modal": {
    "image": "python:3.12",
    "gpu": "A100",
    "packages": ["torch", "transformers"]
  }
}
```

### 6.3 API Endpoints

**Key Management**
- `GET /api/keys` — list key metadata (no private content)
- `POST /api/keys` — upload or generate a key
  - Body: `{ "action": "upload" | "generate", "filename": "...", "private_key": "..." (upload only), "passphrase": "" }`
- `DELETE /api/keys/{filename}` — delete key + warn of dependent nodes

**Compute Nodes**
- `GET /api/compute/nodes` — list all nodes with capabilities
- `POST /api/compute/nodes` — create node
- `GET /api/compute/nodes/{id}` — get single node
- `PUT /api/compute/nodes/{id}` — update node config
- `DELETE /api/compute/nodes/{id}` — delete node
- `POST /api/compute/nodes/{id}/test` — connectivity check (lightweight)
- `POST /api/compute/nodes/{id}/probe` — deep capability discovery (heavyweight)
- `POST /api/compute/nodes/{id}/set-default` — set as sticky default

**Per-Conversation Compute**
- `GET /api/conversations/{uuid}/compute` — get active compute for conversation
- `POST /api/conversations/{uuid}/compute` — bind compute to conversation
- `DELETE /api/conversations/{uuid}/compute` — unbind (falls back to default)

### 6.4 SSH Security (Critical Fix)

Replace `paramiko.AutoAddPolicy()` with **strict host-key verification**:

```python
class StrictHostKeyPolicy(paramiko.MissingHostKeyPolicy):
    def __init__(self, expected_fingerprint: str):
        self.expected = expected_fingerprint

    def missing_host_key(self, client, hostname, key):
        actual = key.get_fingerprint().hex()
        if self.expected and actual != self.expected:
            raise paramiko.SSHException(
                f"Host key mismatch for {hostname}: expected {self.expected}, got {actual}"
            )
        # If no fingerprint stored yet, accept and save
        return
```

On first connect to a new SSH node:
1. Backend connects with `WarningPolicy()` to retrieve the host key.
2. Returns the fingerprint to the frontend with a "Verify Host Key" prompt.
3. User confirms → fingerprint is saved to `config.host_key_fingerprint`.
4. All subsequent connections use `StrictHostKeyPolicy`.

---

## 7. Workspace Isolation

### 7.1 Directory Layout

```
~/.openmlr/
├── workspace-550e8400-e29b-41d4-a716-446655440000/
│   ├── .openmlr-meta/          # internal state (not visible to agent)
│   ├── data/                   # datasets uploaded or downloaded
│   ├── models/                 # trained model checkpoints
│   ├── code/                   # scripts written by agent
│   └── outputs/                # plots, logs, results
├── workspace-6ba7b810-9dad-11d1-80b4-00c04fd430c8/
│   └── ...
└── config.json                 # global user preferences (optional future)
```

### 7.2 Lifecycle

| Event | Action |
|-------|--------|
| Conversation created | `mkdir -p ~/.openmlr/workspace-{uuid}` |
| `sandbox_exec` in local mode | Commands run with `cwd=~/.openmlr/workspace-{uuid}` |
| `sandbox_write` in local mode | Files written relative to workspace root |
| `sandbox_read` in local mode | Files read relative to workspace root |
| Conversation deleted | Workspace is **archived** to `~/.openmlr/archive/workspace-{uuid}-{timestamp}.tar.gz` |
| User setting changed | N/A — workspaces are immutable boundaries |

### 7.3 SSH Remote Workspaces

For SSH nodes, the workspace concept maps to a **remote directory** on the target machine:

```json
{
  "workdir": "/home/researcher/openmlr-workspaces/workspace-550e8400-..."
}
```

The backend ensures the remote directory exists before first execution:
```bash
ssh user@host "mkdir -p /home/researcher/openmlr-workspaces/workspace-{uuid}"
```

### 7.4 Modal Workspaces

Modal sandboxes are ephemeral; "workspace" maps to the sandbox's working directory. Files are not persisted across sandbox destruction.

---

## 8. Per-Conversation Compute Binding

### 8.1 Sticky Defaults (User-Level)

Stored in `user_settings` under category `compute`:

```json
{
  "compute": {
    "default_node_id": 3,
    "default_node_name": "Workstation"
  }
}
```

### 8.2 Per-Conversation Override

Stored in `Conversation.extra` JSONB (existing column):

```json
{
  "compute_node_id": 5,
  "compute_node_name": "Lab Server"
}
```

If `extra.compute_node_id` is null, the conversation uses the user's sticky default.

### 8.3 UX Pattern (Mirrors Model Selection)

**Header selectors in Chat UI:**
```
[Model: anthropic/claude-sonnet-4]  [Compute: ★ Workstation (SSH)]
```

- Clicking **Compute** opens a dropdown: list of all nodes + "Default" option.
- Selecting a compute node:
  1. Calls `POST /api/conversations/{uuid}/compute` with `{node_id}`.
  2. Updates `Conversation.extra`.
  3. Session manager re-creates the sandbox manager for that conversation.
- Selecting "Default" clears the override (deletes key from `extra`).

### 8.4 Session Creation Flow

In `SessionManager.get_or_create_session()`:

```python
# 1. Load user's sticky default compute
user_settings = await ops.get_all_settings(db, user_id, category="compute")
default_node_id = user_settings.get("compute", {}).get("default_node_id")

# 2. Check conversation override
conv = await ops.get_conversation_by_id(db, conversation_id)
override_node_id = conv.extra.get("compute_node_id") if conv.extra else None

effective_node_id = override_node_id or default_node_id

# 3. Initialize sandbox manager with effective node
sandbox_manager = SandboxManager()
if effective_node_id:
    node = await ops.get_compute_node(db, effective_node_id)
    if node:
        await sandbox_manager.create(node.type, node.config)
```

---

## 9. Agent Compute Tools

New tools registered in the `ToolRouter`:

### 9.1 Tool Specifications

| Tool | Parameters | Description |
|------|------------|-------------|
| `compute_list` | `{}` | List all compute nodes with capabilities and health |
| `compute_probe` | `{"node_name": "..."}` | Run deep capability discovery on a node |
| `compute_select` | `{"node_name": "..."}` | Switch active compute for this conversation |
| `compute_plan` | `{"task": "...", "requirements": {"gpu": true, "min_ram_gb": 32}}` | Recommend best node for a task |

### 9.2 System Prompt Enhancement

The system prompt includes a **Compute Environment** section:

```markdown
## Compute Environment

Active compute: Workstation (SSH) — ml-workstation.local
- OS: Ubuntu 22.04
- CPU: 32 cores
- RAM: 128 GB
- GPU: RTX 4090 (24 GB VRAM)
- CUDA: 12.4
- Python: 3.11
- Key packages: torch 2.3, transformers 4.40, jax 0.4

Other available nodes:
- Laptop (Local): CPU-only, 16 GB RAM
- Cloud (Modal): A100 80 GB, offline

Use `compute_plan` before starting long-running tasks to verify the active node meets requirements.
```

### 9.3 Compute Planning Algorithm

```python
def plan_compute(task_description: str, requirements: dict, nodes: list) -> dict:
    scores = []
    for node in nodes:
        if node.health_status != "online":
            continue
        score = 0
        caps = node.capabilities

        # GPU requirement
        if requirements.get("gpu"):
            if not caps.get("gpu_available"):
                continue
            score += 10
            # Prefer more VRAM
            vram = caps.get("gpu_vram_gb", 0)
            score += min(vram / 10, 5)

        # RAM requirement
        min_ram = requirements.get("min_ram_gb", 0)
        available_ram = caps.get("available_ram_gb", 0)
        if available_ram < min_ram:
            continue
        score += min(available_ram / min_ram, 3)

        # Prefer lower latency (local > LAN > cloud)
        if node.type == "local":
            score += 5
        elif node.type == "ssh":
            score += 2

        scores.append({"node": node, "score": score})

    scores.sort(key=lambda x: x["score"], reverse=True)
    return scores[0] if scores else None
```

---

## 10. Capability Discovery

### 10.1 Probed Attributes

```python
@dataclass
class ComputeCapabilities:
    platform: str              # "Linux 6.5.0-15-generic"
    cpu_cores: int
    cpu_arch: str              # "x86_64"
    total_ram_gb: float
    available_ram_gb: float
    total_disk_gb: float
    available_disk_gb: float
    gpu_available: bool
    gpu_count: int
    gpu_info: list[dict]       # [{"model": "RTX 4090", "vram_gb": 24, "cuda": "12.4"}]
    python_versions: list[str] # ["3.11.4", "3.10.12"]
    docker_available: bool
    conda_envs: list[str]
    installed_packages: list[str]  # ["torch==2.3.0", "transformers==4.40.0"]
    has_internet: bool
    latency_ms: float
```

### 10.2 Probe Commands

| Attribute | Local / SSH Command | Modal Command |
|-----------|---------------------|---------------|
| OS | `uname -s -r` | Same |
| CPU | `nproc && uname -m` | Same |
| RAM | `free -g` | Same |
| Disk | `df -BG /` | Same |
| GPU | `nvidia-smi --query-gpu=name,memory.total --format=csv,noheader` | Same |
| Python | `python3 --version; ls /usr/bin/python*` | Same |
| Packages | `pip list --format=freeze 2>/dev/null | head -50` | Same |
| Docker | `docker info 2>/dev/null` | N/A |

### 10.3 Caching Strategy

- Probe results are stored in `compute_nodes.capabilities` JSONB.
- **On-demand refresh**: `compute_probe` tool forces a refresh.
- **Background refresh**: Celery beat task runs every 5 minutes for nodes marked `online`.
- **Stale threshold**: Capabilities older than 1 hour are considered stale; UI shows warning.

---

## 11. Execution Enhancements

### 11.1 Connection Pooling (SSH)

```python
class SSHConnectionPool:
    """Maintains persistent SSH connections per node with TTL."""

    def __init__(self, ttl_seconds: int = 300):
        self._pools: dict[int, paramiko.SSHClient] = {}
        self._last_used: dict[int, float] = {}
        self._ttl = ttl_seconds

    async def get(self, node_id: int, config: dict) -> paramiko.SSHClient:
        client = self._pools.get(node_id)
        if client and client.get_transport() and client.get_transport().is_active():
            self._last_used[node_id] = time.monotonic()
            return client
        # Reconnect
        client = await self._connect(config)
        self._pools[node_id] = client
        self._last_used[node_id] = time.monotonic()
        return client

    async def cleanup(self):
        now = time.monotonic()
        for node_id, last in list(self._last_used.items()):
            if now - last > self._ttl:
                self._pools.pop(node_id, None)
```

### 11.2 Streaming Output

Extend `sandbox_exec` to support streaming for long-running jobs:

```python
# Tool parameter
{
  "command": "python train.py",
  "timeout": 3600,
  "stream": true  # NEW
}
```

When `stream=true`:
1. Backend opens the SSH channel / Docker exec / Modal exec.
2. Reads stdout/stderr in chunks.
3. Broadcasts `tool_log` SSE events with partial output.
4. On completion, sends final `tool_output` event.

### 11.3 File Sync

New tools for batch transfer:

| Tool | Description |
|------|-------------|
| `compute_sync_up` | Sync local workspace files to remote node (rsync/scp) |
| `compute_sync_down` | Sync remote files back to local workspace |

```python
# compute_sync_up
{
  "paths": ["data/", "code/train.py"],
  "direction": "up"
}
```

---

## 12. Frontend: Settings UI

### 12.1 Settings Navigation

Replace "Sandbox" with "Compute" in the settings nav:

```typescript
const navItems = [
  { path: '/settings/providers', label: 'Providers', icon: Key },
  { path: '/settings/agent', label: 'Agent', icon: Bot },
  { path: '/settings/mcp', label: 'MCP Servers', icon: Server },
  { path: '/settings/compute', label: 'Compute', icon: Cpu },  // NEW
  { path: '/settings/writing', label: 'Writing', icon: PenTool },
];
```

### 12.2 Compute Settings Page Structure

```
┌──────────────────────────────────────────────────────────────┐
│ Compute                                                       │
├──────────────────────────────────────────────────────────────┤
│ SSH Keys                                                [+ Add]│
├──────────────────────────────────────────────────────────────┤
│ • id_ed25519_workstation    SHA256:abc...   [Delete]        │
│ • id_rsa_labserver          SHA256:def...   [Delete]        │
├──────────────────────────────────────────────────────────────┤
│ Compute Nodes                                             [+ Add]│
├──────────────────────────────────────────────────────────────┤
│ ★ Workstation (SSH)      ● Online  RTX 4090  [Default]     │
│   Host: ml-workstation.local                                 │
│   Key: id_ed25519_workstation                                │
│   Workspace: ~/.openmlr/workspace-...                        │
│   [Test] [Probe] [Edit] [Delete]                             │
├──────────────────────────────────────────────────────────────┤
│ Laptop (Local)           ● Online  CPU-only                  │
│   [Set Default] [Probe] [Edit] [Delete]                      │
├──────────────────────────────────────────────────────────────┤
│ Cloud GPU (Modal)        ○ Offline  A100                     │
│   [Set Default] [Probe] [Edit] [Delete]                      │
└──────────────────────────────────────────────────────────────┘
```

### 12.3 Add Node Modal

**Step 1: Type**
- Radio: Local Workspace / SSH Remote / Modal Cloud

**Step 2: Config**
- SSH: host, port, username, key selector (dropdown of uploaded keys), workdir
- Local: workdir (defaults to `~/.openmlr/workspace-{conv-uuid}`)
- Modal: image, GPU type, packages

**Step 3: Test & Verify**
- "Test Connection" button
- If SSH and first connect: show host key fingerprint, ask user to verify
- On success: save node

### 12.4 Chat Header Compute Selector

```tsx
// In ChatUI header, next to ModelModal
<ComputeSelector
  currentNode={activeNode}
  nodes={allNodes}
  onChange={(nodeId) => api.setConversationCompute(currentConvUuid, nodeId)}
/>
```

Dropdown shows:
- "Default (★ Workstation)" — selects null override
- Separator
- All nodes with status dot (green/orange/gray)

---

## 13. Implementation Phases

### Phase 1: Foundation — Keys, Registry, Secure SSH
**Backend:**
- Create `.keys/` directory manager (read/write/validate/list)
- Create `ssh_keys` table and CRUD API (`/api/keys`)
- Create `compute_nodes` table and CRUD API (`/api/compute/nodes`)
- Fix SSH security: `StrictHostKeyPolicy`, fingerprint verification
- Update `SSHSandbox` to use `SSHConnectionPool` and key assets from `.keys/`

**Frontend:**
- Replace "Sandbox" nav with "Compute"
- Build `ComputeSettings` page with KeyManager and NodeRegistry sub-components
- Build `AddNodeModal` and `AddKeyModal`

**DB:**
- Alembic migration for `ssh_keys` and `compute_nodes`

### Phase 2: Workspaces & Per-Conversation Binding
**Backend:**
- `WorkspaceManager` — create/get workspace directory per conversation UUID
- Update `LocalSandbox` to use workspace as `workdir`
- Update `SSHSandbox` to ensure remote workspace exists
- Add `/api/conversations/{uuid}/compute` endpoints
- Store sticky default in `user_settings` category `compute`
- Store override in `Conversation.extra`

**Frontend:**
- `ComputeSelector` component in chat header
- Update `ChatUI` to load and display active compute
- Update conversation switch logic to restore active compute

### Phase 3: Capability Discovery & Agent Tools
**Backend:**
- Enhanced `probe_environment()` with structured `ComputeCapabilities`
- Background Celery task for health checks
- Add `compute_list`, `compute_probe`, `compute_select`, `compute_plan` tools
- Update system prompt builder to include compute environment context

**Frontend:**
- Node health status indicators (polling every 30s)
- "Probe" button in settings with progress spinner

### Phase 4: Streaming & Advanced Execution
**Backend:**
- Streaming `sandbox_exec` with `tool_log` SSE events
- `compute_sync_up` / `compute_sync_down` tools (rsync wrapper)
- Modal workspace persistence (optional)

**Frontend:**
- Live output streaming in message list for long-running commands
- Sync progress indicators

---

## 14. Security Checklist

| # | Concern | Mitigation |
|---|---------|------------|
| 1 | SSH key exposure | Keys stored on disk only; DB holds only metadata; API never returns private content |
| 2 | Host key spoofing | Strict fingerprint verification; warn on mismatch; reject unknown keys |
| 3 | Path traversal | All file operations validated against workspace root |
| 4 | Privilege escalation | Default to non-root; `can_sudo` not exposed to agent by default |
| 5 | Key file permissions | `0o600` on private keys, `0o700` on `.keys/` directory |
| 6 | Credential persistence | `.keys/` mounted via Docker volume; survives container restarts |
| 7 | Workspace isolation | Each conversation has unique workspace UUID; no cross-conversation access |

---

## 15. Migration Path

### From Existing `SandboxConfig`

The existing `sandbox_configs` table is superseded by `compute_nodes`.

**Migration strategy:**
1. Create `compute_nodes` and `ssh_keys` tables.
2. Migrate existing `sandbox_configs` rows:
   - `type=local` → `compute_nodes` with `type=local`
   - `type=ssh` → `compute_nodes` with `type=ssh`; extract `key_path` into a key asset if it points to `.keys/`
   - `type=modal` → `compute_nodes` with `type=modal`
3. Deprecate `sandbox_configs` table (drop in a future migration).
4. Update `SandboxSettings.tsx` → `ComputeSettings.tsx`.

---

## 16. Open Questions

1. **Key passphrase support**: Should we support SSH keys with passphrases? If yes, how do we cache the decrypted key securely in memory?
2. **Workspace cleanup policy**: Should we auto-delete archived workspaces after N days, or keep them indefinitely?
3. **Modal integration depth**: Should Modal nodes support `Modal.App.lookup()` reuse, or always create ephemeral sandboxes?
4. **Multi-node parallel execution**: Should the agent be able to run commands on multiple nodes simultaneously (e.g., distributed training), or is single-node-at-a-time sufficient for V1?

---

## 17. Files to Create / Modify

### New Files
```
backend/openmlr/keys/__init__.py
backend/openmlr/keys/manager.py
backend/openmlr/compute/__init__.py
backend/openmlr/compute/manager.py
backend/openmlr/compute/workspace.py
backend/openmlr/compute/probe.py
backend/openmlr/compute/planner.py
backend/openmlr/routes/keys.py
backend/openmlr/routes/compute.py
backend/openmlr/db/migrations/..._add_compute_nodes_and_ssh_keys.py
frontend/src/components/settings/ComputeSettings.tsx
frontend/src/components/settings/AddNodeModal.tsx
frontend/src/components/settings/AddKeyModal.tsx
frontend/src/components/ComputeSelector.tsx
```

### Modified Files
```
backend/openmlr/db/models.py          # Add ComputeNode, SSHKey models
backend/openmlr/db/operations.py      # Add compute node CRUD ops
backend/openmlr/routes/settings.py    # Add compute to provider list (optional)
backend/openmlr/sandbox/ssh.py        # StrictHostKeyPolicy, connection pool
backend/openmlr/sandbox/manager.py    # Integrate ComputeManager
backend/openmlr/sandbox/local.py      # Workspace-aware workdir
backend/openmlr/services/session_manager.py  # Bind compute on session creation
backend/openmlr/tools/registry.py     # Register compute_* tools
backend/openmlr/agent/prompts.py      # Inject compute env into system prompt
frontend/src/App.tsx                  # Add ComputeSelector to header
frontend/src/api.ts                   # Add compute endpoints
frontend/src/components/SettingsPage.tsx  # Update nav items
```

---

## Appendix A: Example User Journey

**Scenario:** User has a laptop and an SSH workstation.

1. **User opens Settings > Compute**
2. **Uploads key**: Pastes `id_ed25519_workstation` private key → saved to `.keys/`
3. **Adds node**: Creates "Workstation" (SSH, host=ml.local, key=id_ed25519_workstation)
4. **Verifies host key**: Backend shows fingerprint, user clicks "Trust"
5. **Sets default**: Clicks "Set Default" on Workstation
6. **Creates conversation**: New chat auto-binds to Workstation
7. **Agent probes**: User asks "What GPU do I have?" → agent runs `sandbox_probe` → sees RTX 4090
8. **Switches compute**: User clicks header dropdown, selects "Laptop (Local)"
9. **Agent adapts**: Next `sandbox_probe` shows CPU-only; agent avoids GPU tasks
10. **Runs training**: User asks "Train ResNet on CIFAR-10" → agent calls `compute_plan` → recommends Workstation → `compute_select` → runs training with streamed output
