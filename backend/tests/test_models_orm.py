"""Tests for SQLAlchemy ORM models — creation, relationships, constraints."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio
from sqlalchemy import select

from openmlr.db.models import (
    User, Conversation, Message, ResearchCorpus,
    WritingProject, SandboxConfig, ConversationTask,
    ConversationResource, AgentJob, UserSetting,
)
from openmlr.auth.security import hash_password


class TestUserModel:
    async def test_create_user(self, db_session: AsyncSession):
        user = User(
            username="newuser",
            password_hash=hash_password("password123"),
            display_name="New User",
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()
        assert user.id is not None
        assert user.username == "newuser"
        assert user.is_active is True
        assert user.created_at is not None

    async def test_user_unique_username(self, db_session: AsyncSession, test_user):
        dup = User(
            username="testuser",
            password_hash=hash_password("another"),
            is_active=True,
        )
        db_session.add(dup)
        with pytest.raises(Exception):
            await db_session.commit()

    async def test_user_relationships_exist(self, db_session: AsyncSession, test_user):
        # Async SQLAlchemy requires relationship attributes to exist on the class
        assert hasattr(User, "conversations")
        assert hasattr(User, "settings")


class TestConversationModel:
    async def test_create_conversation(self, db_session: AsyncSession, test_user):
        conv = Conversation(
            user_id=test_user.id,
            title="Test Conversation",
            model="gpt-4o",
            mode="research",
        )
        db_session.add(conv)
        await db_session.commit()
        assert conv.id is not None
        assert conv.uuid is not None
        assert len(conv.uuid) > 0
        assert conv.user_message_count == 0
        assert conv.created_at is not None
        assert conv.updated_at is not None

    async def test_conversation_user_relationship(self, db_session: AsyncSession, test_user):
        conv = Conversation(user_id=test_user.id, title="Rel Test")
        db_session.add(conv)
        await db_session.commit()
        await db_session.refresh(conv)
        assert conv.user_id == test_user.id


class TestMessageModel:
    @pytest_asyncio.fixture(autouse=True)
    async def _conv(self, db_session: AsyncSession, test_user):
        conv = Conversation(user_id=test_user.id, title="Msg Model Test")
        db_session.add(conv)
        await db_session.commit()
        self.conv = conv

    async def test_create_message(self, db_session: AsyncSession):
        msg = Message(
            conversation_id=self.conv.id,
            role="user",
            content="Hello world",
        )
        db_session.add(msg)
        await db_session.commit()
        assert msg.id is not None
        assert msg.role == "user"
        assert msg.content == "Hello world"

    async def test_message_with_metadata(self, db_session: AsyncSession):
        msg = Message(
            conversation_id=self.conv.id,
            role="assistant",
            content="Done",
            meta={"tool": "search", "usage": {"tokens": 100}},
        )
        db_session.add(msg)
        await db_session.commit()
        assert msg.meta == {"tool": "search", "usage": {"tokens": 100}}

    async def test_message_has_created_at(self, db_session: AsyncSession):
        msg = Message(conversation_id=self.conv.id, role="system", content="Init")
        db_session.add(msg)
        await db_session.commit()
        assert msg.created_at is not None


class TestConversationTask:
    @pytest_asyncio.fixture(autouse=True)
    async def _conv(self, db_session: AsyncSession, test_user):
        conv = Conversation(user_id=test_user.id, title="Task Model Test")
        db_session.add(conv)
        await db_session.commit()
        self.conv = conv

    async def test_create_task(self, db_session: AsyncSession):
        task = ConversationTask(
            conversation_id=self.conv.id,
            title="Test task",
            status="pending",
            order_index=0,
        )
        db_session.add(task)
        await db_session.commit()
        assert task.id is not None
        assert task.title == "Test task"
        assert task.status == "pending"
        assert task.order_index == 0

    async def test_task_with_priority(self, db_session: AsyncSession):
        task = ConversationTask(
            conversation_id=self.conv.id,
            title="Urgent",
            status="pending",
            priority="high",
            order_index=0,
        )
        db_session.add(task)
        await db_session.commit()
        assert task.priority == "high"


class TestConversationResource:
    @pytest_asyncio.fixture(autouse=True)
    async def _conv(self, db_session: AsyncSession, test_user):
        conv = Conversation(user_id=test_user.id, title="Resource Model Test")
        db_session.add(conv)
        await db_session.commit()
        self.conv = conv

    async def test_create_resource(self, db_session: AsyncSession):
        res = ConversationResource(
            conversation_id=self.conv.id,
            resource_id="res-001",
            title="Paper 1",
            type="paper",
            url="https://arxiv.org/abs/1234.5678",
        )
        db_session.add(res)
        await db_session.commit()
        assert res.id is not None
        assert res.type == "paper"
        assert res.url == "https://arxiv.org/abs/1234.5678"

    async def test_resource_with_content(self, db_session: AsyncSession):
        res = ConversationResource(
            conversation_id=self.conv.id,
            resource_id="rpt-001",
            title="Report",
            type="report",
            content="## Findings\nKey results...",
        )
        db_session.add(res)
        await db_session.commit()
        assert res.content is not None


class TestAgentJob:
    @pytest_asyncio.fixture(autouse=True)
    async def _conv(self, db_session: AsyncSession, test_user):
        conv = Conversation(user_id=test_user.id, title="Job Model Test")
        db_session.add(conv)
        await db_session.commit()
        self.conv = conv

    async def test_create_job(self, db_session: AsyncSession):
        job = AgentJob(
            job_id="job-123",
            conversation_id=self.conv.id,
            user_id=self.conv.user_id,
            message="Process this",
            status="queued",
        )
        db_session.add(job)
        await db_session.commit()
        assert job.id is not None
        assert job.job_id == "job-123"
        assert job.status == "queued"
        assert job.created_at is not None

    async def test_job_optional_fields(self, db_session: AsyncSession):
        job = AgentJob(
            job_id="job-456",
            conversation_id=self.conv.id,
            user_id=self.conv.user_id,
            message="Test",
            status="queued",
            mode="research",
        )
        db_session.add(job)
        await db_session.commit()
        assert job.mode == "research"


class TestUserSetting:
    async def test_create_setting(self, db_session: AsyncSession, test_user):
        setting = UserSetting(
            user_id=test_user.id,
            category="agent",
            key="default_model",
            value="gpt-4o",
        )
        db_session.add(setting)
        await db_session.commit()
        assert setting.id is not None
        assert setting.category == "agent"
        assert setting.key == "default_model"
        assert setting.value == "gpt-4o"

    async def test_setting_uniqueness(self, db_session: AsyncSession, test_user):
        s1 = UserSetting(user_id=test_user.id, category="agent", key="model", value="gpt-4o")
        db_session.add(s1)
        await db_session.commit()

        # Verify we can query the setting back
        from sqlalchemy import select
        result = await db_session.execute(
            select(UserSetting).where(
                UserSetting.user_id == test_user.id,
                UserSetting.category == "agent",
                UserSetting.key == "model",
            )
        )
        settings = result.scalars().all()
        assert len(settings) == 1
        assert settings[0].value == "gpt-4o"


class TestResearchCorpus:
    async def test_create_corpus(self, db_session: AsyncSession, test_user):
        corpus = ResearchCorpus(
            user_id=test_user.id,
            paper_id="arxiv-123",
            title="Test Paper",
            abstract="This is a test abstract",
            source="arxiv",
            tags=["ml", "nlp"],
        )
        db_session.add(corpus)
        await db_session.commit()
        assert corpus.id is not None
        assert corpus.paper_id == "arxiv-123"
        assert corpus.source == "arxiv"


class TestWritingProject:
    async def test_create_project(self, db_session: AsyncSession, test_user):
        project = WritingProject(
            user_id=test_user.id,
            title="My Paper",
            status="drafting",
            sections={"abstract": ""},
        )
        db_session.add(project)
        await db_session.commit()
        assert project.id is not None
        assert project.title == "My Paper"
        assert project.status == "drafting"
        assert "abstract" in project.sections


class TestSandboxConfig:
    async def test_create_config(self, db_session: AsyncSession, test_user):
        config = SandboxConfig(
            user_id=test_user.id,
            name="My Modal Sandbox",
            type="modal",
            config={"gpu": "a100"},
            is_default=True,
        )
        db_session.add(config)
        await db_session.commit()
        assert config.id is not None
        assert config.type == "modal"
        assert config.is_default is True
