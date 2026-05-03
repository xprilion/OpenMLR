"""Celery tasks for background process lifecycle management."""

import logging
import os
from datetime import UTC, datetime, timedelta

from ..celery_app import celery_app
from ..db.engine import get_worker_session

logger = logging.getLogger("openmlr.tasks.process")

# Maximum runtime before a process is considered orphaned (48 hours)
MAX_PROCESS_RUNTIME_HOURS = 48


@celery_app.task(name="openmlr.tasks.process_tasks.check_orphaned_processes")
def check_orphaned_processes():
    """Periodic task: check for orphaned background processes.

    Runs every 5 minutes via Celery beat. For each process marked as
    'running' in the DB:
    1. Check if the PID is still alive on the host.
    2. If dead, update status to 'completed' or 'failed'.
    3. If running beyond MAX_PROCESS_RUNTIME_HOURS, mark as 'killed'.
    """
    import asyncio

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_check_orphaned_processes_async())
    finally:
        loop.close()


def _is_pid_alive(pid: int) -> bool:
    """Check if a PID is still running."""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # Process exists but owned by different user


def _check_single_process(proc, now: datetime, max_age: timedelta) -> bool:
    """Check a single process and update its status if needed.

    Returns True if the process record was updated.
    """
    pid = proc.pid
    is_alive = _is_pid_alive(pid) if pid else False

    if not is_alive:
        proc.status = "completed"
        proc.completed_at = now
        logger.info(
            f"Process {proc.uuid[:8]} (pid={pid}) is no longer running, marked as completed"
        )
        return True

    if proc.started_at and (now - proc.started_at) > max_age:
        if pid:
            try:
                import signal

                os.kill(pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass

        proc.status = "killed"
        proc.completed_at = now
        logger.warning(
            f"Process {proc.uuid[:8]} (pid={pid}) exceeded "
            f"{MAX_PROCESS_RUNTIME_HOURS}h runtime, killed"
        )
        return True

    return False


async def _check_orphaned_processes_async():
    """Async implementation of orphaned process checking."""
    from sqlalchemy import select

    from ..db.models import BackgroundProcess

    session_factory = get_worker_session()
    async with session_factory() as db:
        result = await db.execute(
            select(BackgroundProcess).where(BackgroundProcess.status == "running")
        )
        running = list(result.scalars().all())

        if not running:
            return

        now = datetime.now(UTC)
        max_age = timedelta(hours=MAX_PROCESS_RUNTIME_HOURS)
        updated = sum(1 for proc in running if _check_single_process(proc, now, max_age))

        if updated > 0:
            await db.commit()
            logger.info(f"Updated {updated} orphaned/expired background processes")
