"""Authentication router — login, register, user info."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.security import create_access_token, hash_password, verify_password
from ..db.engine import get_db
from ..db.models import User
from ..dependencies import get_current_user
from ..models import TokenResponse, UserLogin, UserRegister

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(body: UserRegister, db: AsyncSession = Depends(get_db)):
    # Check if username is taken
    existing = await db.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken")

    user = User(
        username=body.username,
        display_name=body.display_name or body.username,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id, user.username)
    return TokenResponse(
        access_token=token,
        user={
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
        },
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    token = create_access_token(user.id, user.username)
    return TokenResponse(
        access_token=token,
        user={
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
        },
    )


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.get("/check")
async def check_setup(db: AsyncSession = Depends(get_db)):
    """Check if any users exist (for first-launch flow)."""
    result = await db.execute(select(func.count()).select_from(User))
    count = result.scalar()
    return {"has_users": count > 0}
