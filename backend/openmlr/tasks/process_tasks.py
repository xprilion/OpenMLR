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


async def _check_orphaned_processes_async():
    """Async implementation of orphaned process checking."""
    from sqlalchemy import select

    from ..db.models import BackgroundProcess

    SessionFactory = get_worker_session()
    async with SessionFactory() as db:
        # Find all running processes
        result = await db.execute(
            select(BackgroundProcess).where(BackgroundProcess.status == "running")
        )
        running = list(result.scalars().all())

        if not running:
            return

        now = datetime.now(UTC)
        max_age = timedelta(hours=MAX_PROCESS_RUNTIME_HOURS)
        updated = 0

        for proc in running:
            pid = proc.pid
            is_alive = False

            if pid:
                try:
                    os.kill(pid, 0)
                    is_alive = True
                except ProcessLookupError:
                    is_alive = False
                except PermissionError:
                    is_alive = True  # Process exists but owned by different user

            if not is_alive:
                # Process is dead -- update status
                proc.status = "completed"
                proc.completed_at = now
                updated += 1
                logger.info(
                    f"Process {proc.uuid[:8]} (pid={pid}) is no longer running, marked as completed"
                )
            elif proc.started_at and (now - proc.started_at) > max_age:
                # Process exceeded max runtime -- try to kill it
                if pid:
                    try:
                        import signal

                        os.kill(pid, signal.SIGTERM)
                    except (ProcessLookupError, PermissionError):
                        pass

                proc.status = "killed"
                proc.completed_at = now
                updated += 1
                logger.warning(
                    f"Process {proc.uuid[:8]} (pid={pid}) exceeded "
                    f"{MAX_PROCESS_RUNTIME_HOURS}h runtime, killed"
                )

        if updated > 0:
            await db.commit()
            logger.info(f"Updated {updated} orphaned/expired background processes")
