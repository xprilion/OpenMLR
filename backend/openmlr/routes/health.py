"""Health check endpoint for deployment platforms."""

from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter(tags=["health"])

VERSION = "0.1.0"


@router.get("/api/health")
async def health():
    """Health check endpoint for load balancers and deployment platforms."""
    return {
        "status": "ok",
        "version": VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health")
async def health_alt():
    """Alternative health endpoint (some platforms expect /health)."""
    return await health()
