"""MCP (Model Context Protocol) server integration."""

import logging
import os
import re

log = logging.getLogger(__name__)


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


class MCPManager:
    """
    Manages MCP server connections for a session.
    Supports connecting to multiple servers and registering their tools.
    """

    def __init__(self):
        self._clients: dict[str, object] = {}  # server_name -> client
        self._connected: set[str] = set()

    async def connect_servers(
        self,
        mcp_configs: dict,
        tool_router,
        blocklist: set[str] | None = None,
    ) -> int:
        """
        Connect to configured MCP servers and register their tools.
        Only connects to servers that aren't already connected.
        Returns total number of NEW MCP tools registered.
        """
        if not mcp_configs:
            return 0

        total_registered = 0

        try:
            from fastmcp import Client as MCPClient
        except ImportError:
            log.warning("fastmcp not installed — MCP servers will not be available")
            return 0

        for server_name, server_config in mcp_configs.items():
            # Skip disabled servers
            if not server_config.get("enabled", True):
                continue

            # Skip already connected servers
            if server_name in self._connected:
                continue

            config = process_mcp_config(server_config)
            transport = config.get("transport", "http")
            url = config.get("url", "")
            command = config.get("command", "")

            try:
                if transport == "http" and url:
                    client = MCPClient(url)
                elif transport == "stdio" and command:
                    args = config.get("args", [])
                    env = config.get("env", {})
                    # Merge environment variables
                    full_env = {**os.environ, **env} if env else None
                    client = MCPClient(command, args=args, env=full_env)
                else:
                    log.warning(f"MCP server {server_name}: invalid config (transport={transport})")
                    continue

                # Connect and register tools
                # Note: We keep the client connection open for the session
                await client.__aenter__()
                count = await tool_router.register_mcp_tools(
                    client,
                    blocklist=blocklist or set(),
                )

                self._clients[server_name] = client
                self._connected.add(server_name)
                total_registered += count
                log.info(f"MCP server {server_name}: connected, registered {count} tools")

            except Exception as e:
                log.error(f"MCP server {server_name}: connection failed - {e}")
                continue

        return total_registered

    async def disconnect_all(self):
        """Disconnect all MCP server connections."""
        for server_name, client in self._clients.items():
            try:
                await client.__aexit__(None, None, None)
                log.info(f"MCP server {server_name}: disconnected")
            except Exception as e:
                log.warning(f"MCP server {server_name}: disconnect error - {e}")

        self._clients.clear()
        self._connected.clear()

    @property
    def connected_servers(self) -> set[str]:
        """Return names of connected MCP servers."""
        return self._connected.copy()


# Legacy function for backward compatibility
async def connect_mcp_servers(
    mcp_configs: dict,
    tool_router,
    blocklist: set[str] | None = None,
) -> int:
    """
    Connect to configured MCP servers and register their tools.
    Returns total number of MCP tools registered.

    DEPRECATED: Use MCPManager.connect_servers() for session-based management.
    """
    manager = MCPManager()
    return await manager.connect_servers(mcp_configs, tool_router, blocklist)
