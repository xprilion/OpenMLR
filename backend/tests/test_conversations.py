"""Integration tests for /api/conversations/* endpoints.

Uses the ``client`` (unauthenticated) and ``auth_client`` (authenticated)
httpx fixtures from ``conftest.py``.

Because the conversation routes access ``request.app.state.session_manager``
and ``request.app.state.event_bus``, we attach lightweight stubs to the app
state before the lifespan runs (the test ``client`` fixture skips lifespan).
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Fixture: wire ``app.state.session_manager`` & ``app.state.event_bus``
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(autouse=True)
async def _patch_app_state():
    """Attach stub session_manager and event_bus to the FastAPI app state.

    The agent routes read these via ``request.app.state``; without a running
    lifespan they are absent, so we set minimal mocks here.
    """
    from openmlr.app import app

    sm = MagicMock()
    sm.current_conversation_id = None
    sm.remove_session = AsyncMock(return_value=None)

    bus = MagicMock()
    bus.broadcast = AsyncMock(return_value=None)

    app.state.session_manager = sm
    app.state.event_bus = bus

    yield

    # Cleanup — avoid leaking into other test modules
    if hasattr(app.state, "session_manager"):
        del app.state.session_manager
    if hasattr(app.state, "event_bus"):
        del app.state.event_bus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_conversation(auth_client, **overrides):
    """Shortcut: create a conversation and return the response body."""
    payload = {"title": "Test Conv", "model": "test-model", "mode": "general"}
    payload.update(overrides)
    resp = await auth_client.post("/api/conversations", json=payload)
    assert resp.status_code == 200
    return resp.json()


# ---------------------------------------------------------------------------
# POST /api/conversations
# ---------------------------------------------------------------------------


async def test_create_conversation(auth_client):
    """POST /api/conversations creates a new conversation and returns it."""
    body = await _create_conversation(auth_client, title="My Chat")
    conv = body["conversation"]
    assert conv["title"] == "My Chat"
    assert conv["mode"] == "general"
    assert conv["model"] == "test-model"
    assert conv["user_message_count"] == 0
    assert "uuid" in conv
    assert "id" in conv
    assert "created_at" in conv


async def test_create_conversation_default_title(auth_client):
    """Omitting the title uses the default 'New conversation'."""
    resp = await auth_client.post(
        "/api/conversations",
        json={"model": None, "mode": "research"},
    )
    assert resp.status_code == 200
    conv = resp.json()["conversation"]
    assert conv["title"] == "New conversation"
    assert conv["mode"] == "research"


async def test_create_conversation_unauthenticated(client):
    """POST /api/conversations without auth returns 401."""
    resp = await client.post(
        "/api/conversations",
        json={"title": "Should Fail"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/conversations  (list)
# ---------------------------------------------------------------------------


async def test_list_conversations_empty(auth_client):
    """GET /api/conversations returns an empty list when no conversations exist."""
    resp = await auth_client.get("/api/conversations")
    assert resp.status_code == 200
    assert resp.json()["conversations"] == []


async def test_list_conversations(auth_client):
    """GET /api/conversations returns all conversations for the user."""
    await _create_conversation(auth_client, title="First")
    await _create_conversation(auth_client, title="Second")

    resp = await auth_client.get("/api/conversations")
    assert resp.status_code == 200
    convs = resp.json()["conversations"]
    assert len(convs) == 2
    titles = {c["title"] for c in convs}
    assert titles == {"First", "Second"}


async def test_list_conversations_unauthenticated(client):
    """GET /api/conversations without auth returns 401."""
    resp = await client.get("/api/conversations")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/conversations/{uuid}  (detail)
# ---------------------------------------------------------------------------


async def test_get_conversation_detail(auth_client):
    """GET /api/conversations/{uuid} returns the conversation with messages."""
    created = await _create_conversation(auth_client, title="Detail Test")
    uuid = created["conversation"]["uuid"]

    resp = await auth_client.get(f"/api/conversations/{uuid}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["conversation"]["uuid"] == uuid
    assert body["conversation"]["title"] == "Detail Test"
    assert isinstance(body["messages"], list)
    assert isinstance(body["tasks"], list)
    assert isinstance(body["resources"], list)


async def test_get_conversation_not_found(auth_client):
    """GET /api/conversations/{uuid} with a non-existent uuid returns 404."""
    resp = await auth_client.get("/api/conversations/nonexistent-uuid")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/conversations/{uuid}
# ---------------------------------------------------------------------------


async def test_delete_conversation(auth_client):
    """DELETE /api/conversations/{uuid} removes the conversation."""
    created = await _create_conversation(auth_client, title="To Delete")
    uuid = created["conversation"]["uuid"]

    resp = await auth_client.delete(f"/api/conversations/{uuid}")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    # Verify it's gone
    resp = await auth_client.get(f"/api/conversations/{uuid}")
    assert resp.status_code == 404


async def test_delete_conversation_not_found(auth_client):
    """DELETE /api/conversations/{uuid} with unknown uuid returns 404."""
    resp = await auth_client.delete("/api/conversations/does-not-exist")
    assert resp.status_code == 404


async def test_delete_conversation_unauthenticated(client):
    """DELETE /api/conversations/{uuid} without auth returns 401."""
    resp = await client.delete("/api/conversations/any-uuid")
    assert resp.status_code == 401
