"""Job manager — handles background job creation and status tracking."""

import logging
import os

from sqlalchemy.ext.asyncio import AsyncSession

from ..db import operations as ops
from ..db.models import AgentJob

logger = logging.getLogger("openmlr.services.job_manager")

# Check if background jobs are enabled
USE_BACKGROUND_JOBS = os.environ.get("USE_BACKGROUND_JOBS", "false").lower() in ("true", "1", "yes")


class JobManager:
    """Manages background agent job creation and tracking."""

    def __init__(self):
        self._celery_app = None

    @property
    def celery_app(self):
        """Lazy load Celery app to avoid import issues."""
        if self._celery_app is None and USE_BACKGROUND_JOBS:
            from ..celery_app import celery_app
            self._celery_app = celery_app
        return self._celery_app

    async def create_job(
        self,
        db: AsyncSession,
        conversation_id: int,
        user_id: int,
        message: str,
        mode: str = None,
        model: str = None,
        uuid: str = None,
    ) -> AgentJob | None:
        """
        Create a new background job for processing an agent message.

        Returns the job record, or None if background jobs are disabled.
        """
        if not USE_BACKGROUND_JOBS:
            return None

        # Create job record in database
        job = await ops.create_agent_job(
            db=db,
            conv_id=conversation_id,
            user_id=user_id,
            message=message,
            mode=mode,
        )

        # Enqueue Celery task
        from ..tasks.agent_tasks import process_agent_message
        process_agent_message.delay(
            job_id=job.job_id,
            conversation_id=conversation_id,
            user_id=user_id,
            message=message,
            mode=mode,
            model=model,
            uuid=uuid,
        )

        logger.info(f"Created background job {job.job_id} for conversation {conversation_id}")
        return job

    async def get_job_status(
        self,
        db: AsyncSession,
        job_id: str,
    ) -> dict | None:
        """Get the current status of a job."""
        job = await ops.get_agent_job(db, job_id)
        if not job:
            return None

        return {
            "job_id": job.job_id,
            "status": job.status,
            "error": job.error,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        }

    async def get_active_jobs(
        self,
        db: AsyncSession,
        conversation_id: int,
    ) -> list[dict]:
        """Get all active (queued/running) jobs for a conversation."""
        jobs = await ops.get_active_jobs_for_conversation(db, conversation_id)
        return [
            {
                "job_id": job.job_id,
                "status": job.status,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
            }
            for job in jobs
        ]

    async def cancel_job(
        self,
        db: AsyncSession,
        job_id: str,
    ) -> bool:
        """Cancel a job if it's still queued."""
        job = await ops.get_agent_job(db, job_id)
        if not job:
            return False

        if job.status == "queued":
            # Can cancel queued jobs
            await ops.update_job_status(db, job_id, "cancelled")

            # Revoke the Celery task
            if self.celery_app:
                self.celery_app.control.revoke(job_id, terminate=False)

            return True

        # Can't cancel running/completed jobs easily
        return False


# Global instance
_job_manager: JobManager | None = None


def get_job_manager() -> JobManager:
    """Get the global job manager instance."""
    global _job_manager
    if _job_manager is None:
        _job_manager = JobManager()
    return _job_manager
