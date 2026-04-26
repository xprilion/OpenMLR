"""Tests for database CRUD operations."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio

from openmlr.db import operations as ops


class TestConversationOperations:
    async def test_create_conversation(self, db_session: AsyncSession, test_user):
        conv = await ops.create_conversation(db_session, test_user.id, title="Test Conv")
        assert conv.id is not None
        assert conv.title == "Test Conv"
        assert conv.user_id == test_user.id
        assert conv.mode == "general"

    async def test_create_conversation_with_model(self, db_session: AsyncSession, test_user):
        conv = await ops.create_conversation(db_session, test_user.id, model="gpt-4o", mode="coding")
        assert conv.model == "gpt-4o"
        assert conv.mode == "coding"

    async def test_get_conversations_empty(self, db_session: AsyncSession, test_user):
        convs = await ops.get_conversations(db_session, test_user.id)
        assert convs == []

    async def test_get_conversations(self, db_session: AsyncSession, test_user):
        await ops.create_conversation(db_session, test_user.id, title="Conv 1")
        await ops.create_conversation(db_session, test_user.id, title="Conv 2")
        convs = await ops.get_conversations(db_session, test_user.id)
        assert len(convs) == 2
        assert convs[0].title == "Conv 2"  # most recent first

    async def test_get_conversation_by_id(self, db_session: AsyncSession, test_user):
        conv = await ops.create_conversation(db_session, test_user.id, title="Find Me")
        found = await ops.get_conversation_by_id(db_session, conv.id)
        assert found is not None
        assert found.title == "Find Me"

    async def test_get_conversation_by_id_not_found(self, db_session: AsyncSession):
        found = await ops.get_conversation_by_id(db_session, 9999)
        assert found is None

    async def test_get_conversation_by_uuid(self, db_session: AsyncSession, test_user):
        conv = await ops.create_conversation(db_session, test_user.id)
        found = await ops.get_conversation_by_uuid(db_session, conv.uuid)
        assert found is not None
        assert found.id == conv.id

    async def test_get_conversation_by_uuid_not_found(self, db_session: AsyncSession):
        found = await ops.get_conversation_by_uuid(db_session, "nonexistent")
        assert found is None

    async def test_delete_conversation(self, db_session: AsyncSession, test_user):
        conv = await ops.create_conversation(db_session, test_user.id)
        deleted = await ops.delete_conversation(db_session, conv.id)
        assert deleted is True
        found = await ops.get_conversation_by_id(db_session, conv.id)
        assert found is None

    async def test_delete_nonexistent(self, db_session: AsyncSession):
        deleted = await ops.delete_conversation(db_session, 9999)
        assert deleted is False

    async def test_update_title(self, db_session: AsyncSession, test_user):
        conv = await ops.create_conversation(db_session, test_user.id, title="Old")
        await ops.update_conversation_title(db_session, conv.id, "New Title")
        found = await ops.get_conversation_by_id(db_session, conv.id)
        assert found.title == "New Title"

    async def test_update_model(self, db_session: AsyncSession, test_user):
        conv = await ops.create_conversation(db_session, test_user.id)
        await ops.update_conversation_model(db_session, conv.id, "claude-sonnet-4")
        found = await ops.get_conversation_by_id(db_session, conv.id)
        assert found.model == "claude-sonnet-4"

    async def test_increment_user_message_count(self, db_session: AsyncSession, test_user):
        conv = await ops.create_conversation(db_session, test_user.id)
        assert conv.user_message_count == 0
        await ops.increment_user_message_count(db_session, conv.id)
        found = await ops.get_conversation_by_id(db_session, conv.id)
        assert found.user_message_count == 1

    async def test_conversations_isolated_by_user(self, db_session: AsyncSession, test_user):
        # Create another user
        from openmlr.auth.security import hash_password
        from openmlr.db.models import User
        user2 = User(username="user2", password_hash=hash_password("pwd"), is_active=True)
        db_session.add(user2)
        await db_session.flush()

        await ops.create_conversation(db_session, test_user.id, title="User 1 Conv")
        await ops.create_conversation(db_session, user2.id, title="User 2 Conv")

        convs_u1 = await ops.get_conversations(db_session, test_user.id)
        convs_u2 = await ops.get_conversations(db_session, user2.id)
        assert len(convs_u1) == 1
        assert len(convs_u2) == 1
        assert convs_u1[0].title == "User 1 Conv"
        assert convs_u2[0].title == "User 2 Conv"


class TestMessageOperations:
    @pytest_asyncio.fixture(autouse=True)
    async def _conv(self, db_session: AsyncSession, test_user):
        self.conv = await ops.create_conversation(db_session, test_user.id, title="Msg Test")

    async def test_add_message(self, db_session: AsyncSession):
        msg = await ops.add_message(db_session, self.conv.id, "user", "Hello!")
        assert msg.id is not None
        assert msg.role == "user"
        assert msg.content == "Hello!"
        assert msg.conversation_id == self.conv.id

    async def test_add_message_with_metadata(self, db_session: AsyncSession):
        msg = await ops.add_message(
            db_session, self.conv.id, "assistant", "Done",
            metadata={"tool": "search", "duration": 1.5},
        )
        assert msg.meta == {"tool": "search", "duration": 1.5}

    async def test_get_messages_empty(self, db_session: AsyncSession):
        msgs = await ops.get_messages(db_session, self.conv.id)
        assert msgs == []

    async def test_get_messages(self, db_session: AsyncSession):
        await ops.add_message(db_session, self.conv.id, "user", "First")
        await ops.add_message(db_session, self.conv.id, "assistant", "Second")
        msgs = await ops.get_messages(db_session, self.conv.id)
        assert len(msgs) == 2
        assert msgs[0].content == "First"
        assert msgs[1].content == "Second"

    async def test_clear_messages(self, db_session: AsyncSession):
        await ops.add_message(db_session, self.conv.id, "user", "A")
        await ops.add_message(db_session, self.conv.id, "assistant", "B")
        await ops.clear_messages(db_session, self.conv.id)
        msgs = await ops.get_messages(db_session, self.conv.id)
        assert msgs == []


class TestSettingsOperations:
    async def test_set_and_get_user_setting(self, db_session: AsyncSession, test_user):
        await ops.set_user_setting(db_session, test_user.id, "agent", "default_model", "gpt-4o")
        val = await ops.get_user_setting(db_session, test_user.id, "agent", "default_model")
        assert val == "gpt-4o"

    async def test_set_user_setting_update(self, db_session: AsyncSession, test_user):
        await ops.set_user_setting(db_session, test_user.id, "agent", "yolo_mode", True)
        await ops.set_user_setting(db_session, test_user.id, "agent", "yolo_mode", False)
        val = await ops.get_user_setting(db_session, test_user.id, "agent", "yolo_mode")
        assert val is False

    async def test_get_nonexistent_setting(self, db_session: AsyncSession, test_user):
        val = await ops.get_user_setting(db_session, test_user.id, "agent", "nonexistent")
        assert val is None

    async def test_get_all_settings(self, db_session: AsyncSession, test_user):
        await ops.set_user_setting(db_session, test_user.id, "agent", "model", "gpt-4o")
        await ops.set_user_setting(db_session, test_user.id, "providers", "openai_key", "sk-123")
        settings = await ops.get_all_settings(db_session, test_user.id)
        assert "agent" in settings
        assert "providers" in settings
        assert settings["agent"]["model"] == "gpt-4o"
        assert settings["providers"]["openai_key"] == "sk-123"

    async def test_get_all_settings_by_category(self, db_session: AsyncSession, test_user):
        await ops.set_user_setting(db_session, test_user.id, "agent", "model", "gpt-4o")
        await ops.set_user_setting(db_session, test_user.id, "providers", "key", "val")
        agent_settings = await ops.get_all_settings(db_session, test_user.id, category="agent")
        assert "agent" in agent_settings
        assert "providers" not in agent_settings

    async def test_delete_user_setting(self, db_session: AsyncSession, test_user):
        await ops.set_user_setting(db_session, test_user.id, "agent", "model", "gpt-4o")
        await ops.delete_user_setting(db_session, test_user.id, "agent", "model")
        val = await ops.get_user_setting(db_session, test_user.id, "agent", "model")
        assert val is None

    async def test_set_user_setting_int_value(self, db_session: AsyncSession, test_user):
        await ops.set_user_setting(db_session, test_user.id, "agent", "max_iterations", 100)
        val = await ops.get_user_setting(db_session, test_user.id, "agent", "max_iterations")
        assert val == 100

    async def test_set_user_setting_float_value(self, db_session: AsyncSession, test_user):
        await ops.set_user_setting(db_session, test_user.id, "agent", "threshold", 0.85)
        val = await ops.get_user_setting(db_session, test_user.id, "agent", "threshold")
        assert val == 0.85

    async def test_get_user_agent_settings(self, db_session: AsyncSession, test_user):
        await ops.set_user_setting(db_session, test_user.id, "agent", "default_model", "claude")
        await ops.set_user_setting(db_session, test_user.id, "agent", "yolo_mode", True)
        settings = await ops.get_user_agent_settings(db_session, test_user.id)
        assert settings["default_model"] == "claude"
        assert settings["yolo_mode"] is True


class TestTaskOperations:
    @pytest_asyncio.fixture(autouse=True)
    async def _conv(self, db_session: AsyncSession, test_user):
        self.conv = await ops.create_conversation(db_session, test_user.id)

    async def test_upsert_tasks_create(self, db_session: AsyncSession):
        tasks = [
            {"title": "Task 1", "status": "pending"},
            {"title": "Task 2", "status": "in_progress"},
        ]
        result = await ops.upsert_conversation_tasks(db_session, self.conv.id, tasks)
        assert len(result) == 2
        assert result[0].title == "Task 1"
        assert result[0].order_index == 0
        assert result[1].order_index == 1

    async def test_upsert_tasks_replace(self, db_session: AsyncSession):
        await ops.upsert_conversation_tasks(db_session, self.conv.id, [
            {"title": "Old Task"},
        ])
        result = await ops.upsert_conversation_tasks(db_session, self.conv.id, [
            {"title": "New Task"},
        ])
        assert len(result) == 1
        assert result[0].title == "New Task"

    async def test_get_tasks_empty(self, db_session: AsyncSession):
        tasks = await ops.get_conversation_tasks(db_session, self.conv.id)
        assert tasks == []

    async def test_get_tasks(self, db_session: AsyncSession):
        await ops.upsert_conversation_tasks(db_session, self.conv.id, [
            {"title": "T1", "status": "pending", "priority": "high"},
            {"title": "T2", "status": "completed"},
        ])
        tasks = await ops.get_conversation_tasks(db_session, self.conv.id)
        assert len(tasks) == 2
        assert tasks[0].title == "T1"
        assert tasks[0].priority == "high"

    async def test_update_task_status(self, db_session: AsyncSession):
        await ops.upsert_conversation_tasks(db_session, self.conv.id, [
            {"title": "Do this", "status": "pending"},
        ])
        ok = await ops.update_task_status(db_session, self.conv.id, 0, "completed")
        assert ok is True
        tasks = await ops.get_conversation_tasks(db_session, self.conv.id)
        assert tasks[0].status == "completed"

    async def test_update_task_status_out_of_range(self, db_session: AsyncSession):
        await ops.upsert_conversation_tasks(db_session, self.conv.id, [
            {"title": "Only one"},
        ])
        ok = await ops.update_task_status(db_session, self.conv.id, 5, "completed")
        assert ok is False


class TestResourceOperations:
    @pytest_asyncio.fixture(autouse=True)
    async def _conv(self, db_session: AsyncSession, test_user):
        self.conv = await ops.create_conversation(db_session, test_user.id)

    async def test_add_resource(self, db_session: AsyncSession):
        res = await ops.add_conversation_resource(
            db_session, self.conv.id,
            title="Paper 1", resource_type="paper", url="https://example.com",
        )
        assert res.id is not None
        assert res.title == "Paper 1"
        assert res.type == "paper"
        assert res.url == "https://example.com"

    async def test_get_resources(self, db_session: AsyncSession):
        await ops.add_conversation_resource(db_session, self.conv.id, title="R1", resource_type="doc")
        await ops.add_conversation_resource(db_session, self.conv.id, title="R2", resource_type="code")
        resources = await ops.get_conversation_resources(db_session, self.conv.id)
        assert len(resources) == 2

    async def test_get_resource_by_id(self, db_session: AsyncSession):
        res = await ops.add_conversation_resource(
            db_session, self.conv.id, title="Test", resource_type="doc",
        )
        found = await ops.get_resource_by_id(db_session, res.resource_id)
        assert found is not None
        assert found.title == "Test"

    async def test_upsert_resources_replace(self, db_session: AsyncSession):
        await ops.add_conversation_resource(db_session, self.conv.id, title="Old", resource_type="doc")
        result = await ops.upsert_conversation_resources(db_session, self.conv.id, [
            {"title": "New", "type": "doc"},
        ])
        assert len(result) == 1
        assert result[0].title == "New"

    async def test_upsert_plan_resource_new(self, db_session: AsyncSession):
        res = await ops.upsert_plan_resource(db_session, self.conv.id, "# Plan content")
        assert res.title == "PLAN.md"
        assert res.type == "plan"
        assert res.content == "# Plan content"

    async def test_upsert_plan_resource_update(self, db_session: AsyncSession):
        await ops.upsert_plan_resource(db_session, self.conv.id, "First version")
        res = await ops.upsert_plan_resource(db_session, self.conv.id, "Updated version")
        assert res.content == "Updated version"

    async def test_upsert_paper_resource(self, db_session: AsyncSession):
        res = await ops.upsert_paper_resource(
            db_session, self.conv.id, "My Paper", "## Abstract\nContent",
        )
        assert res.title == "My Paper"
        assert res.type == "paper"
        assert "Abstract" in res.content

    async def test_upsert_resource_create(self, db_session: AsyncSession):
        res = await ops.upsert_resource(
            db_session, self.conv.id,
            resource_id="custom-id", title="Custom", resource_type="report",
            content="Report content",
        )
        assert res.resource_id == "custom-id"
        assert res.content == "Report content"

    async def test_upsert_resource_update(self, db_session: AsyncSession):
        await ops.upsert_resource(
            db_session, self.conv.id,
            resource_id="rid", title="Old Title", resource_type="doc", content="Old",
        )
        res = await ops.upsert_resource(
            db_session, self.conv.id,
            resource_id="rid", title="New Title", resource_type="doc", content="New",
        )
        assert res.title == "New Title"
        assert res.content == "New"


class TestAgentJobOperations:
    @pytest_asyncio.fixture(autouse=True)
    async def _conv(self, db_session: AsyncSession, test_user):
        self.conv = await ops.create_conversation(db_session, test_user.id)

    async def test_create_agent_job(self, db_session: AsyncSession):
        job = await ops.create_agent_job(
            db_session, self.conv.id, self.conv.user_id, "Process this",
        )
        assert job.job_id is not None
        assert job.status == "queued"
        assert job.message == "Process this"

    async def test_get_agent_job(self, db_session: AsyncSession):
        job = await ops.create_agent_job(
            db_session, self.conv.id, self.conv.user_id, "Test",
        )
        found = await ops.get_agent_job(db_session, job.job_id)
        assert found is not None
        assert found.status == "queued"

    async def test_get_agent_job_not_found(self, db_session: AsyncSession):
        found = await ops.get_agent_job(db_session, "nonexistent")
        assert found is None

    async def test_get_active_jobs(self, db_session: AsyncSession):
        job1 = await ops.create_agent_job(db_session, self.conv.id, self.conv.user_id, "Job 1")
        job2 = await ops.create_agent_job(db_session, self.conv.id, self.conv.user_id, "Job 2")
        # Complete one
        await ops.update_job_status(db_session, job1.job_id, "completed")
        active = await ops.get_active_jobs_for_conversation(db_session, self.conv.id)
        assert len(active) == 1
        assert active[0].job_id == job2.job_id

    async def test_update_job_status_to_running(self, db_session: AsyncSession):
        job = await ops.create_agent_job(db_session, self.conv.id, self.conv.user_id, "Test")
        ok = await ops.update_job_status(db_session, job.job_id, "running")
        assert ok is True
        found = await ops.get_agent_job(db_session, job.job_id)
        assert found.status == "running"
        assert found.started_at is not None

    async def test_update_job_status_to_completed(self, db_session: AsyncSession):
        job = await ops.create_agent_job(db_session, self.conv.id, self.conv.user_id, "Test")
        await ops.update_job_status(db_session, job.job_id, "completed")
        found = await ops.get_agent_job(db_session, job.job_id)
        assert found.status == "completed"
        assert found.completed_at is not None

    async def test_update_job_status_not_found(self, db_session: AsyncSession):
        ok = await ops.update_job_status(db_session, "nonexistent", "completed")
        assert ok is False

    async def test_update_job_status_with_error(self, db_session: AsyncSession):
        job = await ops.create_agent_job(db_session, self.conv.id, self.conv.user_id, "Test")
        await ops.update_job_status(db_session, job.job_id, "failed", error="Something broke")
        found = await ops.get_agent_job(db_session, job.job_id)
        assert found.error == "Something broke"
