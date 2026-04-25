"""Agent routes — conversations, messages, SSE, undo, compact."""

import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("openmlr.routes")

from ..db.engine import get_db
from ..db.models import User
from ..db import operations as ops
from ..dependencies import get_current_user
from ..models import ConversationCreate, MessageSend, ApprovalRequest, ModelSwitch
from ..agent.types import AgentEvent

router = APIRouter(prefix="/api", tags=["agent"])


def _sm(request: Request):
    return request.app.state.session_manager


def _bus(request: Request):
    return request.app.state.event_bus


# ── SSE Events ───────────────────────────────────────────

@router.get("/events")
async def events(request: Request, token: str = None):
    """SSE event stream. Uses raw StreamingResponse for immediate flushing."""
    if token:
        from ..auth.security import decode_access_token
        payload = decode_access_token(token)
        if not payload:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=401, content={"error": "Invalid token"})

    event_bus = _bus(request)
    queue = event_bus.subscribe()
    logger.info(f"SSE client connected (subscribers: {event_bus.subscriber_count})")

    async def _stream():
        import json
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=25)
                    et = event.get("event_type", "?") if isinstance(event, dict) else "?"
                    payload = f"data: {json.dumps(event)}\n\n"
                    yield payload
                except asyncio.TimeoutError:
                    yield ":ping\n\n"
        except asyncio.CancelledError:
            pass
        except GeneratorExit:
            pass
        finally:
            event_bus.unsubscribe(queue)
            logger.info(f"SSE client disconnected (subscribers: {event_bus.subscriber_count})")

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable nginx buffering if behind proxy
        },
    )


@router.get("/events/test")
async def events_test(request: Request):
    """Test SSE endpoint — sends 3 events then closes. Use to verify SSE works."""
    import json

    async def _test_stream():
        for i in range(3):
            yield f"data: {json.dumps({'event_type': 'test', 'data': {'n': i}})}\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(
        _test_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Conversations ────────────────────────────────────────

@router.get("/conversations")
async def list_conversations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    convs = await ops.get_conversations(db, user.id)
    return {"conversations": [_conv_dict(c) for c in convs]}


@router.post("/conversations")
async def create_conversation(
    body: ConversationCreate,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conv = await ops.create_conversation(
        db, user.id, title=body.title, model=body.model, mode=body.mode,
    )
    _sm(request).current_conversation_id = conv.id
    return {"conversation": _conv_dict(conv)}


@router.get("/conversations/{uuid}")
async def get_conversation(
    uuid: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conv = await _get_conv_or_404(db, uuid, user.id)
    msgs = await ops.get_messages(db, conv.id)
    return {
        "conversation": _conv_dict(conv),
        "messages": [_msg_dict(m) for m in msgs],
    }


@router.delete("/conversations/{uuid}")
async def delete_conversation(
    uuid: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conv = await _get_conv_or_404(db, uuid, user.id)
    await _sm(request).remove_session(conv.id)
    await ops.delete_conversation(db, conv.id)
    return {"ok": True}


@router.post("/conversations/{uuid}/switch")
async def switch_conversation(
    uuid: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conv = await _get_conv_or_404(db, uuid, user.id)
    sm = _sm(request)
    msg_dicts = await _load_messages(db, conv.id)

    active = await sm.get_or_create_session(
        conv.id, conv.uuid,
        model=conv.model, mode=conv.mode or "general",
        existing_messages=msg_dicts, username=user.display_name or user.username,
    )
    sm.current_conversation_id = conv.id

    await _bus(request).broadcast(
        AgentEvent(event_type="model_info", data={"model": active.session.config.model_name})
    )
    return {"ok": True}


# ── Messaging ────────────────────────────────────────────

@router.post("/message")
async def send_message(
    body: MessageSend,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sm = _sm(request)
    event_bus = _bus(request)

    if not sm.current_conversation_id:
        conv = await ops.create_conversation(db, user.id)
        sm.current_conversation_id = conv.id
    else:
        conv = await ops.get_conversation_by_id(db, sm.current_conversation_id)

    if not conv:
        raise HTTPException(status_code=400, detail="No active conversation")

    # Persist user message to DB
    await ops.add_message(db, conv.id, "user", body.message)
    await ops.increment_user_message_count(db, conv.id)

    # Only load history when creating a NEW session.
    # Exclude the user message we just saved — _run_agent will add it to context.
    session_is_new = sm.get_session(conv.id) is None
    if session_is_new:
        all_msgs = await _load_messages(db, conv.id)
        # Remove the last user message (the one we just saved) — loop adds it
        history = all_msgs[:-1] if all_msgs and all_msgs[-1].get("role") == "user" else all_msgs
    else:
        history = None

    active = await sm.get_or_create_session(
        conv.id, conv.uuid,
        model=conv.model, mode=conv.mode or "general",
        existing_messages=history, username=user.display_name or user.username,
    )

    # Wire DB persistence once per session
    if not active._persist_wired:
        _wire_persistence(active, db, conv.id)
        active._persist_wired = True

    asyncio.create_task(sm.process_message(conv.id, body.message, mode=body.mode))

    # Title generation after 1st and 3rd messages
    user_count = (conv.user_message_count or 0) + 1
    if user_count in (1, 3):
        msg_dicts = await _load_messages(db, conv.id)
        asyncio.create_task(
            _auto_title(sm, event_bus, db, conv.id, conv.uuid, msg_dicts)
        )

    return {"ok": True}


# ── Agent controls ───────────────────────────────────────

@router.get("/reports/{report_id}")
async def get_report(
    report_id: str,
    user: User = Depends(get_current_user),
):
    """Get a completion report by ID."""
    from ..tools.plan import get_report_content
    content = get_report_content(report_id)
    if not content:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"report_id": report_id, "content": content}


@router.post("/answers")
async def submit_answers(
    request: Request,
    user: User = Depends(get_current_user),
):
    """Submit answers to structured questions from ask_user tool."""
    body = await request.json()
    answers = body.get("answers", {})  # {question_id: selected_label}

    active = _sm(request).get_current_session()
    if active and hasattr(active.session, 'pending_answers') and active.session.pending_answers:
        if not active.session.pending_answers.done():
            active.session.pending_answers.set_result(answers)
    return {"ok": True}


@router.post("/interrupt")
async def interrupt(request: Request, user: User = Depends(get_current_user)):
    """Cancel the current agent turn."""
    active = _sm(request).get_current_session()
    if active:
        active.session.cancel()
        await _bus(request).broadcast(AgentEvent(event_type="interrupted"))
    return {"ok": True}


@router.post("/approval")
async def submit_approval(
    body: ApprovalRequest,
    request: Request,
    user: User = Depends(get_current_user),
):
    active = _sm(request).get_current_session()
    if active and active.session.pending_approval:
        from ..agent.loop import _handle_approval
        asyncio.create_task(
            _handle_approval(active.session, active.tool_router, body.approvals)
        )
    return {"ok": True}


@router.post("/undo")
async def undo(request: Request, user: User = Depends(get_current_user)):
    active = _sm(request).get_current_session()
    if active:
        from ..agent.loop import _undo
        await _undo(active.session)
    return {"ok": True}


@router.post("/compact")
async def compact(request: Request, user: User = Depends(get_current_user)):
    active = _sm(request).get_current_session()
    if active:
        from ..agent.loop import _compact
        await _compact(active.session)
    return {"ok": True}


@router.post("/model")
async def switch_model(
    body: ModelSwitch,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    active = _sm(request).get_current_session()
    if active:
        active.session.update_model(body.model)
        await ops.update_conversation_model(db, active.conversation_id, body.model)
    await _bus(request).broadcast(
        AgentEvent(event_type="model_info", data={"model": body.model})
    )
    return {"ok": True}


# ── Helpers ──────────────────────────────────────────────

async def _get_conv_or_404(db, uuid: str, user_id: int):
    conv = await ops.get_conversation_by_uuid(db, uuid)
    if not conv or conv.user_id != user_id:
        raise HTTPException(status_code=404, detail="Not found")
    return conv


async def _load_messages(db, conv_id: int) -> list[dict]:
    msgs = await ops.get_messages(db, conv_id)
    return [{"role": m.role, "content": m.content} for m in msgs]


def _conv_dict(c) -> dict:
    return {
        "id": c.id,
        "uuid": c.uuid,
        "title": c.title,
        "model": c.model,
        "mode": c.mode,
        "user_message_count": c.user_message_count,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


def _msg_dict(m) -> dict:
    return {
        "id": m.id,
        "role": m.role,
        "content": m.content,
        "metadata": m.meta,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


def _wire_persistence(active, db, conv_id: int):
    async def _persist(event: AgentEvent):
        try:
            if event.event_type == "assistant_message" and event.data and event.data.get("content"):
                await ops.add_message(db, conv_id, "assistant", event.data["content"])
            elif event.event_type == "tool_output" and event.data:
                await ops.add_message(db, conv_id, "tool", event.data.get("output", ""), {
                    "tool": event.data.get("tool"),
                    "tool_call_id": event.data.get("tool_call_id"),
                    "success": event.data.get("success"),
                })
        except Exception:
            pass
    active.session.on_event(_persist)


async def _auto_title(sm, event_bus, db, conv_id, uuid, messages):
    try:
        title = await sm.generate_title(conv_id, messages)
        if title:
            await ops.update_conversation_title(db, conv_id, title)
            await event_bus.broadcast(
                AgentEvent(event_type="conversation_updated", data={"uuid": uuid, "title": title})
            )
    except Exception:
        pass
