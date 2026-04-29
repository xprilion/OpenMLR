"""Tests for Pydantic API models — validation, defaults, serialization."""

from datetime import UTC

import pytest
from pydantic import ValidationError

from openmlr.models import (
    AgentEvent,
    ApprovalRequest,
    ConversationCreate,
    ConversationDetail,
    ConversationResponse,
    MessageResponse,
    MessageSend,
    ModelSwitch,
    ProviderConfig,
    SettingUpdate,
    TokenResponse,
    UserLogin,
    UserRegister,
)


class TestUserRegister:
    def test_valid(self):
        u = UserRegister(username="testuser", password="testpassword123")
        assert u.username == "testuser"
        assert u.password == "testpassword123"
        assert u.display_name is None

    def test_with_display_name(self):
        u = UserRegister(username="tester", password="pass123", display_name="Test User")
        assert u.display_name == "Test User"

    def test_username_too_short(self):
        with pytest.raises(ValidationError):
            UserRegister(username="ab", password="password123")

    def test_username_too_long(self):
        with pytest.raises(ValidationError):
            UserRegister(username="a" * 51, password="password123")

    def test_password_too_short(self):
        with pytest.raises(ValidationError):
            UserRegister(username="testuser", password="12345")

    def test_username_exactly_min(self):
        u = UserRegister(username="abc", password="123456")
        assert u.username == "abc"


class TestUserLogin:
    def test_valid(self):
        u = UserLogin(username="testuser", password="secret")
        assert u.username == "testuser"
        assert u.password == "secret"


class TestTokenResponse:
    def test_defaults(self):
        t = TokenResponse(access_token="abc123", user={"id": 1, "username": "test"})
        assert t.access_token == "abc123"
        assert t.token_type == "bearer"
        assert t.user == {"id": 1, "username": "test"}


class TestConversationCreate:
    def test_defaults(self):
        c = ConversationCreate()
        assert c.title == "New conversation"
        assert c.model is None
        assert c.mode == "general"
        assert c.project_uuid is None

    def test_custom(self):
        c = ConversationCreate(title="Research Q1", model="gpt-4o", mode="research")
        assert c.title == "Research Q1"
        assert c.model == "gpt-4o"
        assert c.mode == "research"

    def test_with_project_uuid(self):
        c = ConversationCreate(title="Test", project_uuid="abc-123-def")
        assert c.project_uuid == "abc-123-def"

    def test_project_uuid_defaults_to_none(self):
        c = ConversationCreate()
        assert c.project_uuid is None


class TestConversationResponse:
    def test_creation(self):
        from datetime import datetime

        now = datetime.now(UTC)
        c = ConversationResponse(
            id=1,
            uuid="abc-def",
            title="Test Conv",
            model="gpt-4o",
            mode="general",
            user_message_count=5,
            created_at=now,
            updated_at=now,
        )
        assert c.id == 1
        assert c.uuid == "abc-def"
        assert c.user_message_count == 5


class TestMessageResponse:
    def test_creation(self):
        from datetime import datetime

        now = datetime.now(UTC)
        m = MessageResponse(id=1, role="user", content="Hello", metadata=None, created_at=now)
        assert m.id == 1
        assert m.role == "user"
        assert m.content == "Hello"

    def test_with_metadata(self):
        from datetime import datetime

        now = datetime.now(UTC)
        m = MessageResponse(
            id=2, role="assistant", content="Hi", metadata={"tool": "search"}, created_at=now
        )
        assert m.metadata == {"tool": "search"}


class TestConversationDetail:
    def test_creation(self):
        from datetime import datetime

        now = datetime.now(UTC)
        conv = ConversationResponse(
            id=1,
            uuid="x",
            title="C",
            model=None,
            mode="general",
            user_message_count=0,
            created_at=now,
            updated_at=now,
        )
        msgs = [MessageResponse(id=1, role="user", content="Hi", metadata=None, created_at=now)]
        cd = ConversationDetail(conversation=conv, messages=msgs)
        assert len(cd.messages) == 1
        assert cd.conversation.id == 1


class TestMessageSend:
    def test_basic(self):
        m = MessageSend(message="Hello world")
        assert m.message == "Hello world"
        assert m.mode is None

    def test_with_plan_mode(self):
        m = MessageSend(message="Plan this", mode="plan")
        assert m.mode == "plan"

    def test_with_execute_mode(self):
        m = MessageSend(message="Do this", mode="execute")
        assert m.mode == "execute"

    def test_rejects_invalid_mode(self):
        with pytest.raises(ValidationError):
            MessageSend(message="test", mode="research")

    def test_rejects_arbitrary_mode(self):
        with pytest.raises(ValidationError):
            MessageSend(message="test", mode="anything_else")

    def test_allows_null_mode(self):
        m = MessageSend(message="test", mode=None)
        assert m.mode is None


class TestApprovalRequest:
    def test_valid(self):
        a = ApprovalRequest(approvals={"call_1": True, "call_2": False})
        assert a.approvals == {"call_1": True, "call_2": False}

    def test_empty(self):
        a = ApprovalRequest(approvals={})
        assert a.approvals == {}


class TestSettingUpdate:
    def test_str_value(self):
        s = SettingUpdate(value="hello")
        assert s.value == "hello"

    def test_int_value(self):
        s = SettingUpdate(value=42)
        assert s.value == 42

    def test_bool_value(self):
        s = SettingUpdate(value=True)
        assert s.value is True

    def test_dict_value(self):
        s = SettingUpdate(value={"key": "val"})
        assert s.value == {"key": "val"}


class TestProviderConfig:
    def test_empty(self):
        p = ProviderConfig()
        assert p.openai_api_key is None
        assert p.anthropic_api_key is None

    def test_with_keys(self):
        p = ProviderConfig(openai_api_key="sk-123", brave_api_key="bsk-456")
        assert p.openai_api_key == "sk-123"
        assert p.brave_api_key == "bsk-456"

    def test_modal_config(self):
        p = ProviderConfig(modal_token_id="tid", modal_token_secret="tsec")
        assert p.modal_token_id == "tid"
        assert p.modal_token_secret == "tsec"


class TestModelSwitch:
    def test_valid(self):
        m = ModelSwitch(model="gpt-4o")
        assert m.model == "gpt-4o"


class TestAgentEventPydantic:
    def test_valid(self):
        e = AgentEvent(event_type="status", data={"key": "val"})
        assert e.event_type == "status"
        assert e.data == {"key": "val"}

    def test_no_data(self):
        e = AgentEvent(event_type="ping")
        assert e.event_type == "ping"
        assert e.data is None
