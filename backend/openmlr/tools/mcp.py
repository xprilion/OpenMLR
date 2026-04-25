"""MCP (Model Context Protocol) server integration."""

import os
import re
from typing import Optional
from ..agent.types import ToolSpec


def substitute_env_vars(text: str) -> str:
    """Substitute ${VAR_NAME} patterns with environment variable values."""
    def _replace(match):
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))
    return re.sub(r'\$\{(\w+)\}', _replace, text)


def process_mcp_config(config: dict) -> dict:
    """Process MCP server config, substituting env vars."""
    processed = {}
    for key, value in config.items():
        if isinstance(value, str):
            processed[key] = substitute_env_vars(value)
        elif isinstance(value, dict):
            processed[key] = process_mcp_config(value)
        elif isinstance(value, list):
            processed[key] = [
                substitute_env_vars(v) if isinstance(v, str) else v
                for v in value
            ]
        else:
            processed[key] = value
    return processed


async def connect_mcp_servers(
    mcp_configs: dict,
    tool_router,
    blocklist: Optional[set[str]] = None,
) -> int:
    """
    Connect to configured MCP servers and register their tools.
    Returns total number of MCP tools registered.
    """
    if not mcp_configs:
        return 0

    total_registered = 0

    try:
        from fastmcp import Client as MCPClient
    except ImportError:
        # fastmcp not installed — skip MCP
        return 0

    for server_name, server_config in mcp_configs.items():
        config = process_mcp_config(server_config)
        transport = config.get("transport", "http")
        url = config.get("url", "")
        command = config.get("command", "")

        try:
            if transport == "http" and url:
                client = MCPClient(url)
            elif transport == "stdio" and command:
                args = config.get("args", [])
                client = MCPClient(command, args=args)
            else:
                continue

            # Connect and register tools
            async with client:
                count = await tool_router.register_mcp_tools(
                    client,
                    blocklist=blocklist or set(),
                )
                total_registered += count

        except Exception:
            # Individual MCP server failure shouldn't break the whole system
            continue

    return total_registered
