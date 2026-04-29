"""MCP server management routes — test connections and get status."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import operations as ops
from ..db.engine import get_db
from ..db.models import User
from ..dependencies import get_current_user
from ..tools.mcp import test_mcp_connection

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/mcp", tags=["mcp"])


class TestRequest(BaseModel):
    url: str
    headers: dict[str, str] | None = None
    params: dict[str, str] | None = None


@router.post("/test")
async def test_connection(
    body: TestRequest,
    user: User = Depends(get_current_user),
):
    """Test an MCP server connection without saving it."""
    if not body.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Only http/https URLs are supported")

    result = await test_mcp_connection(
        url=body.url,
        headers=body.headers,
        params=body.params,
    )
    return result


@router.get("/status")
async def get_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get configured MCP servers with their enabled/disabled state."""
    user_settings = await ops.get_all_settings(db, user.id, category="mcp")
    mcp_settings = user_settings.get("mcp", {})
    servers_config = mcp_settings.get("servers", {})

    servers = []
    for name, config in servers_config.items():
        servers.append(
            {
                "name": name,
                "url": config.get("url", ""),
                "enabled": config.get("enabled", True),
                "connected": False,  # Will be updated via SSE in real-time
            }
        )

    return {"servers": servers}
