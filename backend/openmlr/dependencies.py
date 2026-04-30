"""FastAPI dependencies — auth, database sessions, config."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .auth.security import decode_access_token
from .config import AgentConfig, load_config
from .db.engine import get_db as _get_db
from .db.models import User

security = HTTPBearer(auto_error=False)

_config_cache: AgentConfig | None = None


def get_config() -> AgentConfig:
    global _config_cache
    if _config_cache is None:
        _config_cache = load_config()
    return _config_cache


async def get_db() -> AsyncSession:
    """Dependency: yields an async database session."""
    async for session in _get_db():
        yield session


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency: require authenticated user via JWT Bearer token."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    result = await db.execute(
        select(User).where(User.id == int(payload["sub"]), User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Like get_current_user but returns None instead of raising."""
    if credentials is None:
        return None
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        return None
    result = await db.execute(
        select(User).where(User.id == int(payload["sub"]), User.is_active == True)
    )
    return result.scalar_one_or_none()
