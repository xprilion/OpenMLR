"""Celery tasks for background agent processing."""

import asyncio
import logging

from ..agent.types import AgentEvent
from ..celery_app import celery_app
from ..db import operations as ops
from ..db.engine import get_worker_session
from ..services.redis_pubsub import publish_event

logger = logging.getLogger("openmlr.tasks")


@celery_app.task(bind=True, name="openmlr.tasks.agent_tasks.process_agent_message")
def process_agent_message(
    self,
    job_id: str,
    conversation_id: int,
    user_id: int,
    message: str,
    mode: str = None,
    model: str = None,
    uuid: str = None,
):
    """
    Background task to process an agent message.

    This task:
    1. Updates job status to "running"
    2. Creates/gets the agent session
    3. Processes the message through the agent loop
    4. Publishes events to Redis for any connected SSE clients
    5. Updates job status to "completed" or "failed"
    """
    worker_id = self.request.id
    logger.info(f"Worker {worker_id} starting job {job_id} for conversation {conversation_id}")

    # Run the async agent processing in an event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(
            _async_process_message(
                job_id=job_id,
                conversation_id=conversation_id,
                user_id=user_id,
                message=message,
                mode=mode,
                model=model,
                uuid=uuid,
                worker_id=worker_id,
            )
        )
    except Exception as e:
        logger.exception(f"Job {job_id} failed: {e}")
        loop.run_until_complete(_mark_job_failed(job_id, str(e)))
        raise
    finally:
        loop.close()


async def _async_process_message(
    job_id: str,
    conversation_id: int,
    user_id: int,
    message: str,
    mode: str,
    model: str,
    uuid: str,
    worker_id: str,
):
    """Async implementation of message processing."""
    from ..agent.loop import run_agent_turn
    from ..agent.prompts import build_system_prompt
    from ..agent.session import Session
    from ..config import load_config
    from ..sandbox.manager import SandboxManager
    from ..tools.registry import create_tool_router

    # Get worker-specific session factory to avoid event loop conflicts
    worker_session = get_worker_session()

    # Update job status to running
    async with worker_session() as db:
        await ops.update_job_status(db, job_id, "running", worker_id=worker_id)

        # Load existing messages for context
        messages = await ops.get_messages(db, conversation_id)
        existing_messages = [{"role": m.role, "content": m.content} for m in messages]

        # Increment user message count
        await ops.increment_user_message_count(db, conversation_id)

        # Add user message to database
        await ops.add_message(db, conversation_id, "user", message)

    # Broadcast that we're processing
    await publish_event(
        AgentEvent(
            event_type="status",
            data={"status": "thinking...", "job_id": job_id},
        )
    )

    # Create agent session
    config = load_config()
    if model:
        config.model_name = model

    session = Session(config=config, conversation_id=conversation_id)
    sandbox_manager = SandboxManager()
    tool_router = create_tool_router(sandbox_manager)

    # Build and set system prompt
    session.context_manager.system_prompt = build_system_prompt(
        tool_specs=tool_router.get_raw_specs(),
        mode=mode or "general",
        username="user",
    )

    # Load existing messages into context
    for msg in existing_messages:
        session.context_manager.add_message(msg)

    # Wire event broadcasting to Redis pub/sub
    async def _broadcast(event: AgentEvent):
        # Add job_id to events for client filtering
        if event.data is None:
            event.data = {}
        event.data["job_id"] = job_id
        event.data["conversation_uuid"] = uuid
        await publish_event(event)

        # Persist assistant messages and tool outputs
        if event.event_type == "assistant_message" and event.data.get("content"):
            async with worker_session() as db:
                await ops.add_message(db, conversation_id, "assistant", event.data["content"])
        elif event.event_type == "tool_output" and event.data:
            async with worker_session() as db:
                await ops.add_message(
                    db,
                    conversation_id,
                    "tool",
                    event.data.get("output", ""),
                    {
                        "tool": event.data.get("tool"),
                        "tool_call_id": event.data.get("tool_call_id"),
                        "success": event.data.get("success"),
                    },
                )

    session.on_event(_broadcast)

    # Start a background task that polls Redis for an interrupt signal
    # and cancels the session when found.
    async def _poll_interrupt():
        from ..services.redis_pubsub import check_interrupt, clear_interrupt

        try:
            while True:
                await asyncio.sleep(2)
                if await check_interrupt(conversation_id):
                    logger.info(
                        f"Interrupt detected via Redis for conversation {conversation_id}, cancelling session"
                    )
                    session.cancel()
                    await clear_interrupt(conversation_id)
                    break
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.warning(f"Interrupt poll error: {e}")

    interrupt_task = asyncio.create_task(_poll_interrupt())

    try:
        # Run the agent turn
        await run_agent_turn(session, tool_router, message, mode=mode)

        # Mark job as completed
        async with worker_session() as db:
            await ops.update_job_status(db, job_id, "completed")

        # Broadcast completion
        await publish_event(
            AgentEvent(
                event_type="job_complete",
                data={"job_id": job_id, "conversation_uuid": uuid, "status": "completed"},
            )
        )

    except Exception as e:
        logger.exception(f"Agent processing failed for job {job_id}: {e}")
        async with worker_session() as db:
            await ops.update_job_status(db, job_id, "failed", error=str(e))

        await publish_event(
            AgentEvent(
                event_type="job_complete",
                data={
                    "job_id": job_id,
                    "conversation_uuid": uuid,
                    "status": "failed",
                    "error": str(e),
                },
            )
        )
        raise

    finally:
        # Stop the interrupt polling task
        interrupt_task.cancel()
        try:
            await interrupt_task
        except asyncio.CancelledError:
            pass

        # Cleanup
        try:
            await sandbox_manager.destroy()
        except Exception:
            pass

        # Clear any lingering interrupt key
        try:
            from ..services.redis_pubsub import clear_interrupt

            await clear_interrupt(conversation_id)
        except Exception:
            pass

        # Broadcast ready status
        await publish_event(
            AgentEvent(
                event_type="status",
                data={"status": "ready", "job_id": job_id},
            )
        )


async def _mark_job_failed(job_id: str, error: str):
    """Mark a job as failed in the database."""
    worker_session = get_worker_session()
    async with worker_session() as db:
        await ops.update_job_status(db, job_id, "failed", error=error)
