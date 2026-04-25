"""SQLAlchemy ORM models for all tables."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey,
    JSON, Float,
)
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.dialects.postgresql import ARRAY


class Base(DeclarativeBase):
    pass


def _utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), nullable=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    settings = relationship("UserSetting", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    sandbox_configs = relationship("SandboxConfig", back_populates="user", cascade="all, delete-orphan")
    research_corpus = relationship("ResearchCorpus", back_populates="user", cascade="all, delete-orphan")
    writing_projects = relationship("WritingProject", back_populates="user", cascade="all, delete-orphan")


class UserSetting(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category = Column(String(50), nullable=False)
    key = Column(String(100), nullable=False)
    value = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    user = relationship("User", back_populates="settings")
    __table_args__ = (
        # Unique constraint on (user_id, category, key) defined in migration
        {},
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), default="New conversation", nullable=False)
    model = Column(String(100), nullable=True)
    mode = Column(String(20), default="general", nullable=False)  # research, writing, coding, general
    user_message_count = Column(Integer, default=0, nullable=False)
    extra = Column("extra", JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    corpus = relationship("ResearchCorpus", back_populates="conversation")
    writing_project = relationship("WritingProject", back_populates="conversation")
    tasks = relationship("ConversationTask", back_populates="conversation", cascade="all, delete-orphan")
    resources = relationship("ConversationResource", back_populates="conversation", cascade="all, delete-orphan")
    jobs = relationship("AgentJob", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # system, user, assistant, tool
    content = Column(Text, nullable=False)
    meta = Column("meta", JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")


class SandboxConfig(Base):
    __tablename__ = "sandbox_configs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False)  # local, ssh, modal
    config = Column(JSON, nullable=False)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    user = relationship("User", back_populates="sandbox_configs")


class ResearchCorpus(Base):
    __tablename__ = "research_corpus"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    paper_id = Column(String(100), nullable=True)  # arxiv ID or DOI
    title = Column(String(500), nullable=False)
    authors = Column(Text, nullable=True)
    abstract = Column(Text, nullable=True)
    source = Column(String(50), nullable=False)  # arxiv, semantic_scholar, openalex, manual
    sections = Column(JSON, nullable=True)  # parsed sections if read
    notes = Column(Text, nullable=True)
    tags = Column(ARRAY(String), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    user = relationship("User", back_populates="research_corpus")
    conversation = relationship("Conversation", back_populates="corpus")


class WritingProject(Base):
    __tablename__ = "writing_projects"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(500), nullable=False)
    outline = Column(JSON, nullable=True)  # section structure
    sections = Column(JSON, default=dict, nullable=False)  # section_id -> markdown content
    bibliography = Column(JSON, default=list)  # list of BibTeX entries
    extra = Column("extra", JSON, nullable=True)  # style, template, etc.
    status = Column(String(20), default="draft")  # draft, writing, revising, complete
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    user = relationship("User", back_populates="writing_projects")
    conversation = relationship("Conversation", back_populates="writing_project")


class ConversationTask(Base):
    """Persisted tasks (todo items) for a conversation."""
    __tablename__ = "conversation_tasks"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500), nullable=False)
    status = Column(String(20), default="pending", nullable=False)  # pending, in_progress, completed, cancelled
    priority = Column(String(20), default="medium", nullable=True)  # high, medium, low
    order_index = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    conversation = relationship("Conversation", back_populates="tasks")


class ConversationResource(Base):
    """Persisted resources (papers, code, datasets, reports) for a conversation."""
    __tablename__ = "conversation_resources"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    resource_id = Column(String(100), unique=True, nullable=False, default=lambda: str(uuid.uuid4())[:8])
    title = Column(String(500), nullable=False)
    url = Column(String(2000), nullable=True)
    type = Column(String(20), default="doc", nullable=False)  # paper, code, dataset, doc, report
    content = Column(Text, nullable=True)  # For reports, store markdown content
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    conversation = relationship("Conversation", back_populates="resources")


class AgentJob(Base):
    """Background job tracking for agent execution."""
    __tablename__ = "agent_jobs"

    id = Column(Integer, primary_key=True)
    job_id = Column(String(100), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), default="queued", nullable=False)  # queued, running, completed, failed, cancelled
    message = Column(Text, nullable=True)  # The user message that triggered this job
    mode = Column(String(20), nullable=True)  # research, writing, coding, general
    error = Column(Text, nullable=True)  # Error message if failed
    worker_id = Column(String(100), nullable=True)  # Which worker is processing this
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    conversation = relationship("Conversation", back_populates="jobs")
    user = relationship("User")
