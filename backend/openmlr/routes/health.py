"""Health check endpoint for deployment platforms."""

from datetime import UTC, datetime

from fastapi import APIRouter

from openmlr import __version__ as VERSION

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health():
    """Health check endpoint for load balancers and deployment platforms."""
    return {
        "status": "ok",
        "version": VERSION,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/health")
async def health_alt():
    """Alternative health endpoint (some platforms expect /health)."""
    return await health()
