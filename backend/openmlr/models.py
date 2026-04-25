"""Pydantic models for API requests and responses."""

from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


# ---- Auth ----

class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)
    display_name: Optional[str] = None

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
    display_name: Optional[str]
    is_active: bool
    created_at: datetime

# ---- Conversations ----

class ConversationCreate(BaseModel):
    title: Optional[str] = "New conversation"
    model: Optional[str] = None
    mode: Optional[str] = "general"  # "research", "writing", "coding", "general"

class ConversationResponse(BaseModel):
    id: int
    uuid: str
    title: str
    model: Optional[str]
    mode: str
    user_message_count: int
    created_at: datetime
    updated_at: datetime

class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    metadata: Optional[dict] = None
    created_at: datetime

class ConversationDetail(BaseModel):
    conversation: ConversationResponse
    messages: list[MessageResponse]

# ---- Messaging ----

class MessageSend(BaseModel):
    message: str
    mode: Optional[str] = None  # plan, research, write — per-message mode override

class ApprovalRequest(BaseModel):
    approvals: dict[str, bool]  # tool_call_id -> approved

# ---- Settings ----

class SettingUpdate(BaseModel):
    value: Any

class ProviderConfig(BaseModel):
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    brave_api_key: Optional[str] = None
    github_token: Optional[str] = None
    semantic_scholar_api_key: Optional[str] = None
    modal_token_id: Optional[str] = None
    modal_token_secret: Optional[str] = None

# ---- Model Management ----

class ModelSwitch(BaseModel):
    model: str

# ---- Event (SSE) ----

class AgentEvent(BaseModel):
    event_type: str
    data: Optional[dict] = None
