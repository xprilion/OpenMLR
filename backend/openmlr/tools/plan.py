"""Plan tool — task tracking with completion reports and plan change approval.

Tasks and resources are persisted to the database per conversation.
"""

import logging
from datetime import UTC, datetime

from ..agent.types import AgentEvent, ToolSpec
from ..db import operations as ops

logger = logging.getLogger("openmlr.tools.plan")


def _get_session_factory():
    """Get the correct async session factory for the current context (web or worker)."""
    from ..db.engine import _worker_engine, async_session
    # If we're in a Celery worker context, use the worker engine
    eng = _worker_engine.get(None)
    if eng is not None:
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
        return async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    # Otherwise use the main web engine
    return async_session


def create_plan_tool() -> ToolSpec:
    return ToolSpec(
        name="plan_tool",
        description=(
            "Manage the task plan. Emits live updates to the UI panel.\n"
            "Operations:\n"
            "  'create' — create a new task list (propose to user for approval)\n"
            "  'update' — change task status (when marking completed, provide a summary)\n"
            "  'get' — show current plan\n"
            "  'add' — add a task (propose to user for approval)\n"
            "  'add_resource' — track a paper/URL/code/report the agent has read\n"
            "When marking a task completed, include a 'summary' with key findings "
            "and a 'next_hints' with recommendations for upcoming tasks. "
            "The tool auto-generates a completion report stored as a resource."
        ),
        parameters={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["create", "update", "get", "add", "add_resource"],
                    "description": "What to do",
                },
                "tasks": {
                    "type": "array",
                    "description": "For 'create': list of task objects",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "status": {"type": "string", "enum": ["pending", "in_progress", "completed", "cancelled"]},
                        },
                        "required": ["title"],
                    },
                },
                "task_index": {"type": "integer", "description": "For 'update': 0-based index"},
                "status": {"type": "string", "enum": ["pending", "in_progress", "completed", "cancelled"]},
                "title": {"type": "string", "description": "For 'add'/'add_resource': title"},
                "summary": {"type": "string", "description": "For 'update' to completed: summary of what was done"},
                "next_hints": {"type": "string", "description": "For 'update' to completed: hints for next tasks"},
                "url": {"type": "string", "description": "For 'add_resource': URL"},
                "resource_type": {"type": "string", "enum": ["paper", "code", "dataset", "doc", "report"]},
                "content": {"type": "string", "description": "For 'add_resource' type=report: markdown report content"},
            },
            "required": ["operation"],
        },
        handler=_handle_plan,
    )


async def _handle_plan(
    operation: str,
    tasks: list[dict] = None,
    task_index: int = None,
    status: str = None,
    title: str = None,
    summary: str = None,
    next_hints: str = None,
    url: str = None,
    resource_type: str = "doc",
    content: str = None,
    session=None,
    **kwargs,
) -> tuple[str, bool]:
    # Get conversation_id from session
    conv_id = session.conversation_id if session else None
    if not conv_id:
        logger.warning("No conversation_id in session, plan tool cannot persist")
        return "Error: No active conversation.", False

    session_factory = _get_session_factory()
    async with session_factory() as db:
        if operation == "create":
            if not tasks:
                return "Provide 'tasks' array.", False

            task_list = [{"title": t.get("title", ""), "status": t.get("status", "pending")} for t in tasks]
            await ops.upsert_conversation_tasks(db, conv_id, task_list)
            await _emit_plan(session, conv_id, db)

            # Auto-save plan as PLAN.md resource (pinned)
            plan_md = _generate_plan_md(task_list)
            await ops.upsert_plan_resource(db, conv_id, plan_md)
            await _emit_resources(session, conv_id, db)

            return await _format_plan(db, conv_id), True

        elif operation == "add":
            if not title:
                return "Provide 'title'.", False

            # Get existing tasks and append
            existing = await ops.get_conversation_tasks(db, conv_id)
            task_list = [{"title": t.title, "status": t.status, "priority": t.priority} for t in existing]
            task_list.append({"title": title, "status": "pending"})
            await ops.upsert_conversation_tasks(db, conv_id, task_list)
            await _emit_plan(session, conv_id, db)

            # Update PLAN.md
            await ops.upsert_plan_resource(db, conv_id, _generate_plan_md(task_list))
            await _emit_resources(session, conv_id, db)

            return await _format_plan(db, conv_id), True

        elif operation == "update":
            existing = await ops.get_conversation_tasks(db, conv_id)
            if not existing:
                return "No plan exists.", False
            if task_index is None or status is None:
                return "Provide 'task_index' and 'status'.", False
            if task_index < 0 or task_index >= len(existing):
                return f"Invalid index {task_index}.", False

            task = existing[task_index]
            old_status = task.status

            # ENFORCEMENT: When starting a new task (in_progress), check if previous in_progress task has a report
            if status == "in_progress" and old_status != "in_progress":
                in_progress_tasks = [i for i, t in enumerate(existing) if t.status == "in_progress"]
                if in_progress_tasks:
                    prev_idx = in_progress_tasks[0]
                    prev_task = existing[prev_idx]
                    # Check if there's a completion report for the in-progress task
                    resources = await ops.get_conversation_resources(db, conv_id)
                    has_report = any(
                        r.type == "report" and prev_task.title in r.title
                        for r in resources
                    )
                    if not has_report:
                        return (
                            f"⚠️ WORKFLOW VIOLATION: Cannot start task {task_index} while task {prev_idx} "
                            f"('{prev_task.title}') is still in progress.\n\n"
                            f"You must either:\n"
                            f"1. Complete task {prev_idx} first with status='completed', summary, and next_hints\n"
                            f"2. Cancel task {prev_idx} if it's no longer needed\n\n"
                            f"This ensures a completion report is generated before moving on."
                        ), False

            # Update status
            task_list = [{"title": t.title, "status": t.status, "priority": t.priority} for t in existing]
            task_list[task_index]["status"] = status
            await ops.upsert_conversation_tasks(db, conv_id, task_list)
            await _emit_plan(session, conv_id, db)

            # ENFORCEMENT: Completing a task requires a summary
            if status == "completed" and old_status != "completed":
                if not summary:
                    return (
                        f"⚠️ COMPLETION REQUIRES SUMMARY: To mark task {task_index} as completed, "
                        f"you must provide a 'summary' of what was accomplished.\n\n"
                        f"Example:\n"
                        f"plan_tool(operation='update', task_index={task_index}, status='completed', "
                        f"summary='Found 5 relevant papers on X technique...', "
                        f"next_hints='Review paper Y for implementation details')"
                    ), False

                report = _generate_completion_report(task.title, summary, next_hints)
                report_id = f"report-{task_index}-{len(existing)}"

                await ops.add_conversation_resource(
                    db, conv_id,
                    title=f"Report: {task.title}",
                    resource_type="report",
                    content=report,
                    resource_id=report_id,
                )
                await _emit_resources(session, conv_id, db)

                result = await _format_plan(db, conv_id)
                result += f"\n\nCompletion report generated for: {task.title}"
                if next_hints:
                    result += f"\nHints for next tasks: {next_hints}"
                return result, True

            return await _format_plan(db, conv_id), True

        elif operation == "get":
            result = await _format_plan(db, conv_id)
            # Include any next_hints from recent reports for context
            resources = await ops.get_conversation_resources(db, conv_id)
            report_resources = [r for r in resources if r.type == "report"]
            if report_resources:
                last_report = report_resources[-1]
                content_text = last_report.content or ""
                # Extract hints section
                if "## Next Steps" in content_text:
                    hints = content_text.split("## Next Steps")[1].strip()
                    result += f"\n\nFrom latest report — next steps:\n{hints}"
            return result, True

        elif operation == "add_resource":
            if not title:
                return "Provide 'title'.", False

            resource_id = None
            resource_content = None
            if resource_type == "report" and content:
                import uuid
                resource_id = f"report-manual-{str(uuid.uuid4())[:8]}"
                resource_content = content

            await ops.add_conversation_resource(
                db, conv_id,
                title=title,
                resource_type=resource_type,
                url=url,
                content=resource_content,
                resource_id=resource_id,
            )
            await _emit_resources(session, conv_id, db)
            return f"Added resource: {title}", True

    return f"Unknown operation: {operation}", False


async def get_report_content(report_id: str) -> str | None:
    """Retrieve a stored report by ID. Used by the API."""
    session_factory = _get_session_factory()
    async with session_factory() as db:
        resource = await ops.get_resource_by_id(db, report_id)
        return resource.content if resource else None


def _generate_plan_md(tasks: list[dict]) -> str:
    """Generate a PLAN.md markdown document from the task list."""
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    icons = {"pending": "- [ ]", "in_progress": "- [~]", "completed": "- [x]", "cancelled": "- [-]"}
    lines = [
        "# Plan",
        "",
        f"*Last updated: {now}*",
        "",
    ]
    for t in tasks:
        status = t.get("status", "pending")
        lines.append(f"{icons.get(status, '- [ ]')} {t.get('title', '')}")
    done = sum(1 for t in tasks if t.get("status") == "completed")
    lines.extend(["", f"**Progress: {done}/{len(tasks)}**"])
    return "\n".join(lines)


def _generate_completion_report(task_title: str, summary: str = None, next_hints: str = None) -> str:
    """Generate a structured markdown completion report."""
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# Task Completion Report: {task_title}",
        "",
        f"**Completed**: {now}",
        "",
        "## Summary",
        "",
        summary or "No summary provided.",
        "",
    ]
    if next_hints:
        lines.extend([
            "## Next Steps",
            "",
            next_hints,
            "",
        ])
    return "\n".join(lines)


async def _emit_plan(session, conv_id: int, db):
    """Emit plan update event to frontend."""
    if session:
        tasks = await ops.get_conversation_tasks(db, conv_id)
        task_list = [{"title": t.title, "status": t.status} for t in tasks]
        await session.emit(AgentEvent(
            event_type="plan_update",
            data={"tasks": task_list},
        ))


async def _emit_resources(session, conv_id: int, db):
    """Emit resources update event to frontend."""
    if session:
        resources = await ops.get_conversation_resources(db, conv_id)
        res_list = [
            {
                "title": r.title,
                "url": r.url or "",
                "type": r.type,
                "id": r.resource_id,
            }
            for r in resources
        ]
        await session.emit(AgentEvent(
            event_type="resources_update",
            data={"resources": res_list},
        ))


async def _format_plan(db, conv_id: int) -> str:
    """Format the plan as a string for LLM context."""
    tasks = await ops.get_conversation_tasks(db, conv_id)
    if not tasks:
        return "Plan is empty."
    icons = {"pending": "[ ]", "in_progress": "[*]", "completed": "[x]", "cancelled": "[-]"}
    lines = ["## Current Plan\n"]
    for i, t in enumerate(tasks):
        lines.append(f"{i}. {icons.get(t.status, '[ ]')} {t.title}")
    done = sum(1 for t in tasks if t.status == "completed")
    lines.append(f"\nProgress: {done}/{len(tasks)}")
    return "\n".join(lines)
