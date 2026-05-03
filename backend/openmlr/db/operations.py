"""Database CRUD operations for conversations and messages."""

from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    AgentJob,
    ComputeNode,
    Conversation,
    ConversationResource,
    ConversationTask,
    Message,
    Project,
    SSHKey,
    UserSetting,
)

# ---- Projects ----


async def create_project(
    db: AsyncSession,
    user_id: int,
    name: str,
    slug: str,
    description: str | None = None,
    workspace_path: str | None = None,
    settings: dict | None = None,
) -> Project:
    project = Project(
        user_id=user_id,
        name=name,
        slug=slug,
        description=description,
        workspace_path=workspace_path,
        settings=settings,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def get_user_projects(
    db: AsyncSession,
    user_id: int,
    include_archived: bool = False,
) -> list[Project]:
    query = select(Project).where(Project.user_id == user_id)
    if not include_archived:
        query = query.where(Project.status == "active")
    query = query.order_by(Project.updated_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_project_by_id(
    db: AsyncSession, project_id: int, user_id: int | None = None
) -> Project | None:
    query = select(Project).where(Project.id == project_id)
    if user_id is not None:
        query = query.where(Project.user_id == user_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_project_by_uuid(
    db: AsyncSession, uuid: str, user_id: int | None = None
) -> Project | None:
    query = select(Project).where(Project.uuid == uuid)
    if user_id is not None:
        query = query.where(Project.user_id == user_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_project_by_slug(db: AsyncSession, user_id: int, slug: str) -> Project | None:
    result = await db.execute(
        select(Project).where(Project.user_id == user_id, Project.slug == slug)
    )
    return result.scalar_one_or_none()


# Explicit allowlist of fields that can be updated via update_project.
# Prevents injection of workspace_path, user_id, id, uuid, etc.
_PROJECT_UPDATABLE_FIELDS = {"name", "slug", "description", "settings", "status"}


async def update_project(
    db: AsyncSession,
    project_id: int,
    user_id: int,
    **kwargs,
) -> Project | None:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        return None
    for key, value in kwargs.items():
        if key in _PROJECT_UPDATABLE_FIELDS:
            setattr(project, key, value)
    await db.commit()
    await db.refresh(project)
    return project


async def archive_project(db: AsyncSession, project_id: int, user_id: int) -> Project | None:
    return await update_project(db, project_id, user_id, status="archived")


async def get_project_conversations(db: AsyncSession, project_id: int) -> list[Conversation]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.project_id == project_id)
        .order_by(Conversation.updated_at.desc())
    )
    return list(result.scalars().all())


async def attach_conversation_to_project(
    db: AsyncSession,
    conversation_id: int,
    project_id: int | None,
    user_id: int | None = None,
) -> bool:
    """Attach or detach a conversation from a project.

    When user_id is provided, verifies ownership of both conversation and project.
    """
    conv = await get_conversation_by_id(db, conversation_id)
    if not conv:
        return False
    # Verify conversation ownership when user_id is provided
    if user_id is not None and conv.user_id != user_id:
        return False
    # Verify project ownership when attaching (not detaching)
    if project_id is not None and user_id is not None:
        project = await get_project_by_id(db, project_id, user_id)
        if not project:
            return False
    conv.project_id = project_id
    await db.commit()
    return True


# ---- Conversations ----


async def create_conversation(
    db: AsyncSession,
    user_id: int,
    title: str = "New conversation",
    model: str | None = None,
    mode: str = "general",
    project_id: int | None = None,
) -> Conversation:
    conv = Conversation(
        user_id=user_id,
        title=title,
        model=model,
        mode=mode,
        project_id=project_id,
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


async def get_conversations(db: AsyncSession, user_id: int) -> list[Conversation]:
    """Return all conversations for a user that belong to a project."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id, Conversation.project_id.isnot(None))
        .order_by(Conversation.updated_at.desc())
    )
    return list(result.scalars().all())


async def delete_orphan_conversations(db: AsyncSession, user_id: int) -> int:
    """Delete conversations with no project (project_id IS NULL).

    Returns the count of deleted conversations. Messages, tasks, resources,
    and jobs cascade-delete via the FK constraints.
    """
    result = await db.execute(
        select(Conversation).where(
            Conversation.user_id == user_id, Conversation.project_id.is_(None)
        )
    )
    orphans = list(result.scalars().all())
    count = len(orphans)
    for conv in orphans:
        await db.delete(conv)
    if count > 0:
        await db.commit()
    return count


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
    await db.execute(update(Conversation).where(Conversation.id == conv_id).values(title=title))
    await db.commit()


async def update_conversation_model(db: AsyncSession, conv_id: int, model: str):
    await db.execute(update(Conversation).where(Conversation.id == conv_id).values(model=model))
    await db.commit()


async def update_conversation_extra(db: AsyncSession, conv_id: int, extra: dict):
    await db.execute(update(Conversation).where(Conversation.id == conv_id).values(extra=extra))
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
        select(Message).where(Message.conversation_id == conv_id).order_by(Message.created_at.asc())
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
    await db.execute(delete(Message).where(Message.conversation_id == conv_id))
    await db.commit()


# ---- Settings ----


async def get_user_setting(db: AsyncSession, user_id: int, category: str, key: str) -> dict | None:
    from .models import UserSetting

    result = await db.execute(
        select(UserSetting).where(
            UserSetting.user_id == user_id,
            UserSetting.category == category,
            UserSetting.key == key,
        )
    )
    setting = result.scalar_one_or_none()
    return setting.value if setting else None


async def set_user_setting(
    db: AsyncSession,
    user_id: int,
    category: str,
    key: str,
    value: dict | list | str | int | float | bool,
):
    from .models import UserSetting

    result = await db.execute(
        select(UserSetting).where(
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


def _clean_json_value(val: object) -> object:
    """Strip surrounding JSON quotes from string values stored in JSON columns."""
    if isinstance(val, str):
        val = val.strip('"')
    return val


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
        grouped[s.category][s.key] = _clean_json_value(s.value)
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


# ---- Conversation Tasks ----


async def get_conversation_tasks(db: AsyncSession, conv_id: int) -> list[ConversationTask]:
    result = await db.execute(
        select(ConversationTask)
        .where(ConversationTask.conversation_id == conv_id)
        .order_by(ConversationTask.order_index.asc(), ConversationTask.created_at.asc())
    )
    return list(result.scalars().all())


async def upsert_conversation_tasks(
    db: AsyncSession,
    conv_id: int,
    tasks: list[dict],
) -> list[ConversationTask]:
    """Replace all tasks for a conversation with the new list."""
    # Delete existing tasks
    await db.execute(delete(ConversationTask).where(ConversationTask.conversation_id == conv_id))

    # Insert new tasks
    new_tasks = []
    for idx, task_data in enumerate(tasks):
        task = ConversationTask(
            conversation_id=conv_id,
            title=task_data.get("title", ""),
            status=task_data.get("status", "pending"),
            priority=task_data.get("priority"),
            order_index=idx,
        )
        db.add(task)
        new_tasks.append(task)

    await db.commit()
    return new_tasks


async def update_task_status(
    db: AsyncSession,
    conv_id: int,
    task_index: int,
    status: str,
) -> bool:
    """Update status of a specific task by index."""
    tasks = await get_conversation_tasks(db, conv_id)
    if 0 <= task_index < len(tasks):
        tasks[task_index].status = status
        await db.commit()
        return True
    return False


# ---- Workspace Path Helpers ----


async def get_project_workspace_for_conversation(db: AsyncSession, conv_id: int) -> str | None:
    """Resolve the project workspace path for a conversation (conv -> project -> workspace_path)."""
    conv = await get_conversation_by_id(db, conv_id)
    if not conv or not conv.project_id:
        return None
    project = await get_project_by_id(db, conv.project_id)
    if not project:
        return None
    return project.workspace_path


# ---- Conversation Resources ----


async def get_conversation_resources(db: AsyncSession, conv_id: int) -> list[ConversationResource]:
    result = await db.execute(
        select(ConversationResource)
        .where(ConversationResource.conversation_id == conv_id)
        .order_by(ConversationResource.created_at.asc())
    )
    return list(result.scalars().all())


async def add_conversation_resource(
    db: AsyncSession,
    conv_id: int,
    title: str,
    resource_type: str,
    url: str | None = None,
    content: str | None = None,
    resource_id: str | None = None,
) -> ConversationResource:
    import uuid as uuid_mod

    resource = ConversationResource(
        conversation_id=conv_id,
        resource_id=resource_id or str(uuid_mod.uuid4())[:8],
        title=title,
        type=resource_type,
        url=url,
        content=content,
    )
    db.add(resource)
    await db.commit()
    await db.refresh(resource)
    return resource


async def get_resource_by_id(db: AsyncSession, resource_id: str) -> ConversationResource | None:
    result = await db.execute(
        select(ConversationResource).where(ConversationResource.resource_id == resource_id)
    )
    return result.scalar_one_or_none()


async def upsert_conversation_resources(
    db: AsyncSession,
    conv_id: int,
    resources: list[dict],
) -> list[ConversationResource]:
    """Replace all resources for a conversation with the new list."""
    import uuid as uuid_mod

    # Delete existing resources
    await db.execute(
        delete(ConversationResource).where(ConversationResource.conversation_id == conv_id)
    )

    # Insert new resources
    new_resources = []
    for res_data in resources:
        resource = ConversationResource(
            conversation_id=conv_id,
            resource_id=res_data.get("id") or str(uuid_mod.uuid4())[:8],
            title=res_data.get("title", ""),
            type=res_data.get("type", "doc"),
            url=res_data.get("url"),
            content=res_data.get("content"),
        )
        db.add(resource)
        new_resources.append(resource)

    await db.commit()
    return new_resources


PLAN_RESOURCE_ID = "plan-md"


async def upsert_plan_resource(
    db: AsyncSession, conv_id: int, content: str
) -> ConversationResource:
    """Create or update the pinned PLAN.md resource for a conversation."""
    existing = await get_resource_by_id(db, f"{PLAN_RESOURCE_ID}-{conv_id}")
    if existing:
        existing.content = content
        await db.commit()
        await db.refresh(existing)
        return existing
    return await add_conversation_resource(
        db,
        conv_id,
        title="PLAN.md",
        resource_type="plan",
        content=content,
        resource_id=f"{PLAN_RESOURCE_ID}-{conv_id}",
    )


PAPER_RESOURCE_ID = "paper"


async def upsert_paper_resource(
    db: AsyncSession,
    conv_id: int,
    title: str,
    content: str,
) -> ConversationResource:
    """Create or update the paper draft resource for a conversation."""
    rid = f"{PAPER_RESOURCE_ID}-{conv_id}"
    existing = await get_resource_by_id(db, rid)
    if existing:
        existing.title = title
        existing.content = content
        await db.commit()
        await db.refresh(existing)
        return existing
    return await add_conversation_resource(
        db,
        conv_id,
        title=title,
        resource_type="paper",
        content=content,
        resource_id=rid,
    )


async def upsert_resource(
    db: AsyncSession,
    conv_id: int,
    resource_id: str,
    title: str,
    resource_type: str,
    content: str | None = None,
    url: str | None = None,
) -> ConversationResource:
    """Create or update a resource by resource_id."""
    existing = await get_resource_by_id(db, resource_id)
    if existing:
        existing.title = title
        existing.content = content
        if url:
            existing.url = url
        await db.commit()
        await db.refresh(existing)
        return existing
    return await add_conversation_resource(
        db,
        conv_id,
        title=title,
        resource_type=resource_type,
        content=content,
        url=url,
        resource_id=resource_id,
    )


# ---- Agent Jobs ----


async def create_agent_job(
    db: AsyncSession,
    conv_id: int,
    user_id: int,
    message: str,
    mode: str | None = None,
) -> AgentJob:
    import uuid as uuid_mod

    job = AgentJob(
        job_id=str(uuid_mod.uuid4()),
        conversation_id=conv_id,
        user_id=user_id,
        message=message,
        mode=mode,
        status="queued",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def get_agent_job(db: AsyncSession, job_id: str) -> AgentJob | None:
    result = await db.execute(select(AgentJob).where(AgentJob.job_id == job_id))
    return result.scalar_one_or_none()


async def get_active_jobs_for_conversation(db: AsyncSession, conv_id: int) -> list[AgentJob]:
    result = await db.execute(
        select(AgentJob)
        .where(
            AgentJob.conversation_id == conv_id,
            AgentJob.status.in_(["queued", "running"]),
        )
        .order_by(AgentJob.created_at.desc())
    )
    return list(result.scalars().all())


async def update_job_status(
    db: AsyncSession,
    job_id: str,
    status: str,
    error: str | None = None,
    worker_id: str | None = None,
) -> bool:
    job = await get_agent_job(db, job_id)
    if not job:
        return False

    job.status = status
    if error:
        job.error = error
    if worker_id:
        job.worker_id = worker_id

    if status == "running" and not job.started_at:
        job.started_at = datetime.now(UTC)
    elif status in ("completed", "failed", "cancelled"):
        job.completed_at = datetime.now(UTC)

    await db.commit()
    return True


# ---- User Settings ----


async def get_user_settings(db: AsyncSession, user_id: int, category: str | None = None) -> dict:
    """Get user settings as a dict. Optionally filter by category."""
    query = select(UserSetting).where(UserSetting.user_id == user_id)
    if category:
        query = query.where(UserSetting.category == category)
    result = await db.execute(query)
    settings = {}
    for s in result.scalars().all():
        if s.category not in settings:
            settings[s.category] = {}
        settings[s.category][s.key] = s.value
    return settings


async def get_user_agent_settings(db: AsyncSession, user_id: int) -> dict:
    """Get user's agent settings (default_model, research_model, yolo_mode)."""
    result = await db.execute(
        select(UserSetting).where(UserSetting.user_id == user_id, UserSetting.category == "agent")
    )
    settings = {}
    for s in result.scalars().all():
        settings[s.key] = _clean_json_value(s.value)
    return settings


# ---- Conversation Search (Full-Text) ----


async def search_conversations(
    db: AsyncSession,
    user_id: int,
    query: str,
    project_id: int | None = None,
    limit: int = 20,
) -> list[dict]:
    """Search conversation messages using PostgreSQL full-text search.

    Returns matching conversations with highlighted snippets.
    Uses plainto_tsquery for natural language queries.
    """
    from sqlalchemy import func, text

    # Build the search query using PostgreSQL FTS functions
    ts_query = func.plainto_tsquery("english", query)
    ts_vector = func.to_tsvector("english", Message.content)

    # Build base query joining messages to conversations
    stmt = (
        select(
            Conversation.id.label("conversation_id"),
            Conversation.uuid.label("conversation_uuid"),
            Conversation.title,
            Conversation.created_at,
            func.ts_headline(
                "english",
                Message.content,
                ts_query,
                text("'MaxWords=40, MinWords=20, StartSel=**, StopSel=**'"),
            ).label("snippet"),
            func.ts_rank(ts_vector, ts_query).label("rank"),
        )
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Conversation.user_id == user_id,
            Message.role.in_(["user", "assistant"]),
            ts_vector.op("@@")(ts_query),
        )
    )

    if project_id is not None:
        stmt = stmt.where(Conversation.project_id == project_id)

    # Group by conversation and take the best-matching snippet
    stmt = stmt.order_by(text("rank DESC")).limit(limit * 3)  # Over-fetch for dedup

    result = await db.execute(stmt)
    rows = result.all()

    # Deduplicate by conversation (keep highest-ranked snippet per conversation)
    seen_convs = set()
    results = []
    for row in rows:
        if row.conversation_id in seen_convs:
            continue
        seen_convs.add(row.conversation_id)
        results.append(
            {
                "conversation_id": row.conversation_id,
                "conversation_uuid": row.conversation_uuid,
                "title": row.title,
                "snippet": row.snippet,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
        )
        if len(results) >= limit:
            break

    return results


# ---- SSH Keys ----


async def create_ssh_key(
    db: AsyncSession,
    user_id: int,
    filename: str,
    fingerprint: str,
    algorithm: str,
    public_key: str,
    comment: str | None = None,
) -> SSHKey:
    key = SSHKey(
        user_id=user_id,
        filename=filename,
        fingerprint=fingerprint,
        algorithm=algorithm,
        public_key=public_key,
        comment=comment,
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)
    return key


async def get_ssh_keys(db: AsyncSession, user_id: int) -> list[SSHKey]:
    result = await db.execute(
        select(SSHKey).where(SSHKey.user_id == user_id).order_by(SSHKey.created_at.desc())
    )
    return list(result.scalars().all())


async def get_ssh_key_by_filename(db: AsyncSession, user_id: int, filename: str) -> SSHKey | None:
    result = await db.execute(
        select(SSHKey).where(SSHKey.user_id == user_id, SSHKey.filename == filename)
    )
    return result.scalar_one_or_none()


async def delete_ssh_key(db: AsyncSession, user_id: int, filename: str) -> bool:
    result = await db.execute(
        select(SSHKey).where(SSHKey.user_id == user_id, SSHKey.filename == filename)
    )
    key = result.scalar_one_or_none()
    if not key:
        return False
    await db.delete(key)
    await db.commit()
    return True


# ---- Compute Nodes ----


async def create_compute_node(
    db: AsyncSession,
    user_id: int,
    name: str,
    node_type: str,
    config: dict,
    is_default: bool = False,
    priority: int = 0,
) -> ComputeNode:
    node = ComputeNode(
        user_id=user_id,
        name=name,
        type=node_type,
        config=config,
        is_default=is_default,
        priority=priority,
    )
    db.add(node)
    await db.commit()
    await db.refresh(node)
    return node


async def get_compute_nodes(db: AsyncSession, user_id: int) -> list[ComputeNode]:
    result = await db.execute(
        select(ComputeNode)
        .where(ComputeNode.user_id == user_id)
        .order_by(ComputeNode.priority.desc(), ComputeNode.created_at.desc())
    )
    return list(result.scalars().all())


async def get_compute_node_by_id(
    db: AsyncSession, node_id: int, user_id: int | None = None
) -> ComputeNode | None:
    query = select(ComputeNode).where(ComputeNode.id == node_id)
    if user_id is not None:
        query = query.where(ComputeNode.user_id == user_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_compute_node_by_name(db: AsyncSession, user_id: int, name: str) -> ComputeNode | None:
    result = await db.execute(
        select(ComputeNode).where(ComputeNode.user_id == user_id, ComputeNode.name == name)
    )
    return result.scalar_one_or_none()


async def update_compute_node(
    db: AsyncSession,
    node_id: int,
    user_id: int,
    **kwargs,
) -> ComputeNode | None:
    result = await db.execute(
        select(ComputeNode).where(ComputeNode.id == node_id, ComputeNode.user_id == user_id)
    )
    node = result.scalar_one_or_none()
    if not node:
        return None
    for key, value in kwargs.items():
        if hasattr(node, key):
            setattr(node, key, value)
    await db.commit()
    await db.refresh(node)
    return node


async def delete_compute_node(db: AsyncSession, node_id: int, user_id: int) -> bool:
    result = await db.execute(
        select(ComputeNode).where(ComputeNode.id == node_id, ComputeNode.user_id == user_id)
    )
    node = result.scalar_one_or_none()
    if not node:
        return False
    await db.delete(node)
    await db.commit()
    return True


async def set_default_compute_node(db: AsyncSession, user_id: int, node_id: int | None) -> None:
    # Clear existing default
    await db.execute(
        update(ComputeNode)
        .where(ComputeNode.user_id == user_id, ComputeNode.is_default.is_(True))
        .values(is_default=False)
    )
    # Set new default
    if node_id is not None:
        await db.execute(
            update(ComputeNode)
            .where(ComputeNode.id == node_id, ComputeNode.user_id == user_id)
            .values(is_default=True)
        )
    await db.commit()


async def get_default_compute_node(db: AsyncSession, user_id: int) -> ComputeNode | None:
    result = await db.execute(
        select(ComputeNode).where(
            ComputeNode.user_id == user_id,
            ComputeNode.is_default.is_(True),
        )
    )
    return result.scalar_one_or_none()


# ---- Background Processes ----


async def create_background_process(
    db: AsyncSession,
    conversation_id: int,
    user_id: int,
    command: str,
    pid: int | None = None,
    host: str = "local",
    project_id: int | None = None,
    output_path: str | None = None,
):
    from .models import BackgroundProcess

    proc = BackgroundProcess(
        conversation_id=conversation_id,
        user_id=user_id,
        command=command,
        pid=pid,
        host=host,
        project_id=project_id,
        output_path=output_path,
    )
    db.add(proc)
    await db.commit()
    await db.refresh(proc)
    return proc


async def get_background_processes(
    db: AsyncSession,
    user_id: int,
    conversation_id: int | None = None,
    status: str | None = None,
) -> list:
    from .models import BackgroundProcess

    query = select(BackgroundProcess).where(BackgroundProcess.user_id == user_id)
    if conversation_id is not None:
        query = query.where(BackgroundProcess.conversation_id == conversation_id)
    if status is not None:
        query = query.where(BackgroundProcess.status == status)
    query = query.order_by(BackgroundProcess.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_background_process_by_uuid(db: AsyncSession, uuid: str):
    from .models import BackgroundProcess

    result = await db.execute(select(BackgroundProcess).where(BackgroundProcess.uuid == uuid))
    return result.scalar_one_or_none()


async def update_background_process(
    db: AsyncSession,
    uuid: str,
    **kwargs,
) -> bool:

    proc = await get_background_process_by_uuid(db, uuid)
    if not proc:
        return False
    for key, value in kwargs.items():
        if hasattr(proc, key):
            setattr(proc, key, value)
    await db.commit()
    return True
