"""Integration tests for /api/auth/* endpoints.

Uses the ``client`` (unauthenticated) and ``auth_client`` (authenticated)
httpx fixtures from ``conftest.py`` which hit the FastAPI app backed by an
in-memory SQLite database.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


async def test_register_success(client):
    """POST /api/auth/register with valid data returns a token and user."""
    resp = await client.post(
        "/api/auth/register",
        json={
            "username": "newuser",
            "password": "strongpassword",
            "display_name": "New User",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["user"]["username"] == "newuser"
    assert body["user"]["display_name"] == "New User"
    assert "id" in body["user"]


async def test_register_duplicate_username(client):
    """POST /api/auth/register with an already-taken username returns 400."""
    payload = {"username": "dupuser", "password": "password123"}

    first = await client.post("/api/auth/register", json=payload)
    assert first.status_code == 200

    second = await client.post("/api/auth/register", json=payload)
    assert second.status_code == 400
    assert "already taken" in second.json()["detail"].lower()


async def test_register_uses_username_as_default_display_name(client):
    """When display_name is omitted, it defaults to the username."""
    resp = await client.post(
        "/api/auth/register",
        json={"username": "nodisplay", "password": "password123"},
    )
    assert resp.status_code == 200
    assert resp.json()["user"]["display_name"] == "nodisplay"


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


async def test_login_success(client):
    """POST /api/auth/login with correct credentials returns a token."""
    # Register first
    await client.post(
        "/api/auth/register",
        json={"username": "loginuser", "password": "mypassword"},
    )

    resp = await client.post(
        "/api/auth/login",
        json={"username": "loginuser", "password": "mypassword"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["user"]["username"] == "loginuser"


async def test_login_wrong_password(client):
    """POST /api/auth/login with wrong password returns 401."""
    await client.post(
        "/api/auth/register",
        json={"username": "wrongpw", "password": "correct"},
    )

    resp = await client.post(
        "/api/auth/login",
        json={"username": "wrongpw", "password": "incorrect"},
    )
    assert resp.status_code == 401
    assert "invalid" in resp.json()["detail"].lower()


async def test_login_nonexistent_user(client):
    """POST /api/auth/login for a user that doesn't exist returns 401."""
    resp = await client.post(
        "/api/auth/login",
        json={"username": "ghost", "password": "anything"},
    )
    assert resp.status_code == 401
    assert "invalid" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# GET /api/auth/me
# ---------------------------------------------------------------------------


async def test_me_authenticated(auth_client, test_user):
    """GET /api/auth/me with a valid token returns the current user."""
    resp = await auth_client.get("/api/auth/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == test_user.id
    assert body["username"] == "testuser"
    assert body["display_name"] == "Test User"
    assert body["is_active"] is True
    assert "created_at" in body


async def test_me_unauthenticated(client):
    """GET /api/auth/me without an auth header returns 401."""
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/auth/check
# ---------------------------------------------------------------------------


async def test_check_no_users(client):
    """GET /api/auth/check on a fresh DB returns has_users=false."""
    resp = await client.get("/api/auth/check")
    assert resp.status_code == 200
    assert resp.json()["has_users"] is False


async def test_check_has_users_after_registration(client):
    """GET /api/auth/check returns has_users=true after a user registers."""
    await client.post(
        "/api/auth/register",
        json={"username": "checkuser", "password": "password123"},
    )

    resp = await client.get("/api/auth/check")
    assert resp.status_code == 200
    assert resp.json()["has_users"] is True
