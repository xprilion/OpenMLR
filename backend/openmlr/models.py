"""Pydantic models for API requests and responses."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

# ---- Auth ----


class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)
    display_name: str | None = None


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserInfo(BaseModel):
    id: int
    username: str
    display_name: str | None
    is_active: bool
    created_at: datetime


# ---- Conversations ----


class ConversationCreate(BaseModel):
    title: str | None = "New conversation"
    model: str | None = None
    mode: str | None = "general"  # "research", "writing", "coding", "general"
    project_uuid: str | None = None  # required — conversations must belong to a project


class ConversationResponse(BaseModel):
    id: int
    uuid: str
    title: str
    model: str | None
    mode: str
    user_message_count: int
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    metadata: dict | None = None
    created_at: datetime


class ConversationDetail(BaseModel):
    conversation: ConversationResponse
    messages: list[MessageResponse]


# ---- Messaging ----


class MessageSend(BaseModel):
    message: str
    mode: Literal["plan", "execute"] | None = (
        None  # per-message mode; only plan or execute accepted
    )
    request_id: str | None = None  # client-generated idempotency key


class ApprovalRequest(BaseModel):
    approvals: dict[str, bool]  # tool_call_id -> approved


# ---- Settings ----


class SettingUpdate(BaseModel):
    value: Any


class ProviderConfig(BaseModel):
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    openrouter_api_key: str | None = None
    brave_api_key: str | None = None
    github_token: str | None = None
    semantic_scholar_api_key: str | None = None
    modal_token_id: str | None = None
    modal_token_secret: str | None = None


# ---- Model Management ----


class ModelSwitch(BaseModel):
    model: str


# ---- Event (SSE) ----


class AgentEvent(BaseModel):
    event_type: str
    data: dict | None = None
