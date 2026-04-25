"""Database CRUD operations for conversations and messages."""

from datetime import datetime, timezone
from sqlalchemy import select, delete, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from .models import Conversation, Message, ResearchCorpus, WritingProject, SandboxConfig


# ---- Conversations ----

async def create_conversation(
    db: AsyncSession,
    user_id: int,
    title: str = "New conversation",
    model: str | None = None,
    mode: str = "general",
) -> Conversation:
    conv = Conversation(
        user_id=user_id,
        title=title,
        model=model,
        mode=mode,
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


async def get_conversations(db: AsyncSession, user_id: int) -> list[Conversation]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
    )
    return list(result.scalars().all())


async def get_conversation_by_id(db: AsyncSession, conv_id: int) -> Conversation | None:
    result = await db.execute(select(Conversation).where(Conversation.id == conv_id))
    return result.scalar_one_or_none()


async def get_conversation_by_uuid(db: AsyncSession, uuid: str) -> Conversation | None:
    result = await db.execute(select(Conversation).where(Conversation.uuid == uuid))
    return result.scalar_one_or_none()


async def delete_conversation(db: AsyncSession, conv_id: int) -> bool:
    conv = await get_conversation_by_id(db, conv_id)
    if conv:
        await db.delete(conv)
        await db.commit()
        return True
    return False


async def update_conversation_title(db: AsyncSession, conv_id: int, title: str):
    await db.execute(
        update(Conversation).where(Conversation.id == conv_id).values(title=title)
    )
    await db.commit()


async def update_conversation_model(db: AsyncSession, conv_id: int, model: str):
    await db.execute(
        update(Conversation).where(Conversation.id == conv_id).values(model=model)
    )
    await db.commit()


async def increment_user_message_count(db: AsyncSession, conv_id: int):
    await db.execute(
        update(Conversation)
        .where(Conversation.id == conv_id)
        .values(user_message_count=Conversation.user_message_count + 1)
    )
    await db.commit()


# ---- Messages ----

async def get_messages(db: AsyncSession, conv_id: int) -> list[Message]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv_id)
        .order_by(Message.created_at.asc())
    )
    return list(result.scalars().all())


async def add_message(
    db: AsyncSession,
    conv_id: int,
    role: str,
    content: str,
    metadata: dict | None = None,
) -> Message:
    msg = Message(
        conversation_id=conv_id,
        role=role,
        content=content,
        meta=metadata,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def clear_messages(db: AsyncSession, conv_id: int):
    await db.execute(
        delete(Message).where(Message.conversation_id == conv_id)
    )
    await db.commit()


# ---- Settings ----

async def get_user_setting(
    db: AsyncSession, user_id: int, category: str, key: str
) -> dict | None:
    from .models import UserSetting
    result = await db.execute(
        select(UserSetting)
        .where(
            UserSetting.user_id == user_id,
            UserSetting.category == category,
            UserSetting.key == key,
        )
    )
    setting = result.scalar_one_or_none()
    return setting.value if setting else None


async def set_user_setting(
    db: AsyncSession, user_id: int, category: str, key: str, value: dict | list | str | int | float | bool
):
    from .models import UserSetting
    result = await db.execute(
        select(UserSetting)
        .where(
            UserSetting.user_id == user_id,
            UserSetting.category == category,
            UserSetting.key == key,
        )
    )
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = value
    else:
        setting = UserSetting(
            user_id=user_id,
            category=category,
            key=key,
            value=value,
        )
        db.add(setting)
    await db.commit()


async def get_all_settings(db: AsyncSession, user_id: int, category: str | None = None) -> dict:
    from .models import UserSetting
    query = select(UserSetting).where(UserSetting.user_id == user_id)
    if category:
        query = query.where(UserSetting.category == category)
    result = await db.execute(query)
    settings = result.scalars().all()

    grouped: dict[str, dict] = {}
    for s in settings:
        if s.category not in grouped:
            grouped[s.category] = {}
        grouped[s.category][s.key] = s.value
    return grouped


async def delete_user_setting(db: AsyncSession, user_id: int, category: str, key: str):
    from .models import UserSetting
    await db.execute(
        delete(UserSetting).where(
            UserSetting.user_id == user_id,
            UserSetting.category == category,
            UserSetting.key == key,
        )
    )
    await db.commit()
