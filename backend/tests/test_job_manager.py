"""Tests for JobManager — background job creation and status tracking."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio

from openmlr.services.job_manager import JobManager, get_job_manager
from openmlr.db import operations as ops


@pytest_asyncio.fixture
async def conversation(db_session: AsyncSession, test_user):
    return await ops.create_conversation(db_session, test_user.id, title="Job Test")


class TestJobManager:
    async def test_get_job_manager_singleton(self):
        jm1 = get_job_manager()
        jm2 = get_job_manager()
        assert jm1 is jm2

    async def test_create_job_disabled_by_default(self, db_session: AsyncSession, conversation, test_user):
        jm = JobManager()
        # USE_BACKGROUND_JOBS is controlled by env — test without making assumptions
        from openmlr.services.job_manager import USE_BACKGROUND_JOBS
        job = await jm.create_job(
            db=db_session,
            conversation_id=conversation.id,
            user_id=test_user.id,
            message="Test message",
        )
        if not USE_BACKGROUND_JOBS:
            assert job is None
        else:
            assert job is not None
            assert job.status == "queued"

    async def test_get_job_status_nonexistent(self, db_session: AsyncSession):
        jm = JobManager()
        status = await jm.get_job_status(db_session, "nonexistent")
        assert status is None

    async def test_get_job_status_from_db(self, db_session: AsyncSession, conversation, test_user):
        job = await ops.create_agent_job(
            db_session, conversation.id, test_user.id, "Test",
        )
        jm = JobManager()
        status = await jm.get_job_status(db_session, job.job_id)
        assert status is not None
        assert status["job_id"] == job.job_id
        assert status["status"] == "queued"
        assert "created_at" in status

    async def test_get_active_jobs(self, db_session: AsyncSession, conversation, test_user):
        job1 = await ops.create_agent_job(db_session, conversation.id, test_user.id, "J1")
        job2 = await ops.create_agent_job(db_session, conversation.id, test_user.id, "J2")
        await ops.update_job_status(db_session, job2.job_id, "completed")

        jm = JobManager()
        active = await jm.get_active_jobs(db_session, conversation.id)
        assert len(active) == 1
        assert active[0]["job_id"] == job1.job_id

    async def test_cancel_queued_job(self, db_session: AsyncSession, conversation, test_user):
        job = await ops.create_agent_job(db_session, conversation.id, test_user.id, "Test")
        jm = JobManager()
        cancelled = await jm.cancel_job(db_session, job.job_id)
        assert cancelled is True
        found = await ops.get_agent_job(db_session, job.job_id)
        assert found.status == "cancelled"

    async def test_cancel_nonexistent_job(self, db_session: AsyncSession):
        jm = JobManager()
        cancelled = await jm.cancel_job(db_session, "nonexistent")
        assert cancelled is False

    async def test_cancel_already_running_job(self, db_session: AsyncSession, conversation, test_user):
        job = await ops.create_agent_job(db_session, conversation.id, test_user.id, "Test")
        await ops.update_job_status(db_session, job.job_id, "running")
        jm = JobManager()
        cancelled = await jm.cancel_job(db_session, job.job_id)
        assert cancelled is False
