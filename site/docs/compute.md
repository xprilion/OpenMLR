---
title: Compute Environments - OpenMLR
description: Configure and manage compute environments in OpenMLR. Local Docker, SSH remotes, and Modal cloud execution for ML research tasks.
---

# Compute Environments

OpenMLR supports multiple compute backends for code execution. Configure compute nodes in **Settings > Compute** to run experiments on local Docker containers, remote SSH servers, or Modal cloud sandboxes.

## Overview

| Type | Description | Best For |
|------|-------------|----------|
| **Local** | Docker containers on your machine | Development, quick tests |
| **SSH** | Remote servers via SSH | GPU clusters, lab machines |
| **Modal** | Serverless cloud compute | Scalable GPU workloads |

## Local Compute

Executes commands in Docker containers on the host machine.

### Configuration

| Field | Required | Description |
|-------|----------|-------------|
| Name | Yes | Unique identifier for this node |
| Workspace | No | Host directory to mount (default: current directory) |

### How It Works

1. Commands run inside a Docker container (`python:3.12-slim` by default)
2. The workspace directory is mounted at `/workspace` in the container
3. Results are captured and returned to the agent

### Docker-in-Docker vs Direct Execution

When running OpenMLR in Docker Compose:
- The worker container detects it's already inside a container
- Commands execute directly in the worker container (no nested Docker)
- File operations use the mounted workspace

When running natively:
- Commands spawn isolated Docker containers
- Each execution gets a fresh environment

## SSH Compute

Execute commands on remote machines via SSH. Ideal for GPU clusters or dedicated lab machines.

### Configuration

| Field | Required | Description |
|-------|----------|-------------|
| Name | Yes | Unique identifier |
| Host | Yes | Hostname or IP address |
| Port | No | SSH port (default: 22) |
| Username | Yes | SSH username |
| Key | Yes | SSH private key (managed in Settings > Compute > Keys) |
| Workspace | No | Remote directory for file operations |

### SSH Key Management

1. Go to **Settings > Compute**
2. Click **Manage Keys**
3. Generate a new Ed25519 or RSA key pair, or upload an existing key
4. Copy the public key to your remote server's `~/.ssh/authorized_keys`

### Connection Pooling

SSH connections are pooled and reused across tool calls to minimize connection overhead. Idle connections are automatically cleaned up after 5 minutes.

## Modal Compute

Run code on [Modal](https://modal.com) serverless infrastructure. Great for GPU workloads without managing infrastructure.

### Configuration

| Field | Required | Description |
|-------|----------|-------------|
| Name | Yes | Unique identifier |
| GPU | No | GPU type (`T4`, `A10G`, `A100`, etc.) |
| Timeout | No | Maximum execution time in seconds |

### Environment Variables

Set Modal credentials via environment variables or Settings > Providers:

```bash
MODAL_TOKEN_ID=your-token-id
MODAL_TOKEN_SECRET=your-token-secret
```

### GPU Options

| GPU | VRAM | Best For |
|-----|------|----------|
| `T4` | 16GB | Inference, small training |
| `A10G` | 24GB | Medium training, fine-tuning |
| `A100` | 40/80GB | Large model training |

## Compute Tools

The agent has access to compute-related tools:

| Tool | Mode | Description |
|------|------|-------------|
| `compute_list` | Plan, Execute | List available compute nodes |
| `compute_probe` | Plan, Execute | Probe node capabilities (OS, GPU, Python versions) |
| `compute_select` | Execute | Switch to a different compute node |

### Probing Capabilities

The `compute_probe` tool returns:
- Operating system and architecture
- Available GPUs with VRAM, CUDA version, driver version
- Python versions installed
- Available disk space

Example output:
```
OS: Linux x86_64 (Ubuntu 22.04)
GPUs:
  - NVIDIA A100-SXM4-80GB (80GB)
    CUDA: 12.4, Driver: 545.23.08
Python: 3.12, 3.11, 3.10
Disk: 850GB free
```

## Setting a Default Node

1. Go to **Settings > Compute**
2. Click the star icon next to a node to set it as default
3. New conversations will use this node for execution

## Workspace Isolation

Each conversation gets its own workspace directory:
- **Local**: `workspaces/{conversation_uuid}/`
- **SSH**: `{remote_workspace}/{conversation_uuid}/`
- **Modal**: Ephemeral filesystem per execution

Files created during execution persist within the conversation but are isolated from other conversations.

## Security Considerations

- **Local**: Commands run in Docker containers with limited host access
- **SSH**: Use dedicated keys with restricted permissions; consider a separate user for OpenMLR
- **Modal**: Code runs in isolated serverless containers

::: warning
Never expose compute nodes with unrestricted access. Use SSH keys without passphrases only in trusted environments.
:::
