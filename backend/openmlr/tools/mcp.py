"""MCP (Model Context Protocol) server integration.

Only HTTP/HTTPS MCP servers are supported. Each server config can include
custom authentication via headers or query parameters.
"""

import logging
import os
import re

log = logging.getLogger(__name__)


def substitute_env_vars(text: str) -> str:
    """Substitute ${VAR_NAME} patterns with environment variable values."""

    def _replace(match):
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))

    return re.sub(r"\$\{(\w+)\}", _replace, text)


def process_mcp_config(config: dict) -> dict:
    """Process MCP server config, substituting env vars."""
    processed = {}
    for key, value in config.items():
        if isinstance(value, str):
            processed[key] = substitute_env_vars(value)
        elif isinstance(value, dict):
            processed[key] = process_mcp_config(value)
        elif isinstance(value, list):
            processed[key] = [substitute_env_vars(v) if isinstance(v, str) else v for v in value]
        else:
            processed[key] = value
    return processed


def _build_url_with_params(url: str, params: dict[str, str] | None) -> str:
    """Append query parameters to a URL."""
    if not params:
        return url
    from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

    parsed = urlparse(url)
    existing = parse_qs(parsed.query, keep_blank_values=True)
    for k, v in params.items():
        existing[k] = [v]
    new_query = urlencode({k: v[0] for k, v in existing.items()})
    return urlunparse(parsed._replace(query=new_query))


def _create_mcp_client(url: str, headers: dict | None = None):
    """Create a fastmcp Client with optional custom headers on the transport.

    Uses StreamableHttpTransport by default (POST-based, newer standard).
    Falls back to SSETransport for URLs ending in /sse (legacy convention).
    """
    from fastmcp import Client as MCPClient
    from fastmcp.client.transports.http import StreamableHttpTransport
    from fastmcp.client.transports.sse import SSETransport

    if headers:
        # Pick transport based on URL convention (same logic as fastmcp's infer_transport)
        if url.rstrip("/").endswith("/sse"):
            transport = SSETransport(url=url, headers=headers)
        else:
            transport = StreamableHttpTransport(url=url, headers=headers)
        return MCPClient(transport)
    return MCPClient(url)


class MCPManager:
    """
    Manages MCP server connections for a session.
    Only HTTP/HTTPS MCP servers are supported.
    """

    def __init__(self):
        self._clients: dict[str, object] = {}  # server_name -> client
        self._connected: set[str] = set()
        self._configs: dict[str, dict] = {}  # server_name -> processed config

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
            from fastmcp import Client as _MCPClient  # noqa: F401 — validates import
        except ImportError:
            log.warning("fastmcp not installed — MCP servers will not be available")
            return 0

        for server_name, server_config in mcp_configs.items():
            # Skip disabled servers
            if not server_config.get("enabled", True):
                self._configs[server_name] = process_mcp_config(server_config)
                continue

            # Skip already connected servers
            if server_name in self._connected:
                continue

            config = process_mcp_config(server_config)
            self._configs[server_name] = config
            url = config.get("url", "")

            if not url:
                log.warning(f"MCP server {server_name}: missing URL")
                continue

            # Validate URL scheme
            if not url.startswith(("http://", "https://")):
                log.warning(
                    f"MCP server {server_name}: only http/https URLs are supported, got {url[:20]}"
                )
                continue

            try:
                # Build URL with query params if configured
                params = config.get("params")
                final_url = _build_url_with_params(url, params)

                # Build headers dict if configured
                headers = config.get("headers") or None

                client = _create_mcp_client(final_url, headers)

                # Connect and register tools
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
        self._configs.clear()

    @property
    def connected_servers(self) -> set[str]:
        """Return names of connected MCP servers."""
        return self._connected.copy()

    def get_server_statuses(self) -> list[dict]:
        """Return status info for all known servers."""
        statuses = []
        for name, config in self._configs.items():
            statuses.append(
                {
                    "name": name,
                    "url": config.get("url", ""),
                    "enabled": config.get("enabled", True),
                    "connected": name in self._connected,
                }
            )
        return statuses


async def test_mcp_connection(
    url: str, headers: dict | None = None, params: dict | None = None
) -> dict:
    """
    Test an MCP server connection.
    Returns {"ok": True, "tools": int} on success or {"ok": False, "error": str} on failure.
    """
    try:
        from fastmcp import Client as _MCPClient  # noqa: F401 — validates import
    except ImportError:
        return {"ok": False, "error": "fastmcp not installed on server"}

    final_url = _build_url_with_params(url, params)

    try:
        client = _create_mcp_client(final_url, headers)
        await client.__aenter__()
        try:
            tools = await client.list_tools()
            tool_count = len(tools) if tools else 0
            return {"ok": True, "tools": tool_count}
        finally:
            await client.__aexit__(None, None, None)
    except Exception as e:
        return {"ok": False, "error": str(e)}


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
