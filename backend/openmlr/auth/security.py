"""Authentication security — password hashing (bcrypt) and JWT tokens."""

import logging
import os
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

# JWT Secret - require explicit setting in production, generate random for dev
_jwt_secret = os.environ.get("JWT_SECRET_KEY")
if not _jwt_secret:
    if os.environ.get("ENVIRONMENT", "development") == "production":
        raise RuntimeError(
            "JWT_SECRET_KEY environment variable is required in production. "
            'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
        )
    # Generate a random secret for development (changes on restart - fine for dev)
    _jwt_secret = secrets.token_urlsafe(32)
    logger.warning(
        "JWT_SECRET_KEY not set - using random secret (sessions won't persist across restarts)"
    )

SECRET_KEY = _jwt_secret
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def create_access_token(user_id: int, username: str) -> str:
    expire = datetime.now(UTC) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
