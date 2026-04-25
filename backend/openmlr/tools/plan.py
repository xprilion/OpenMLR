"""Plan tool — task tracking with completion reports and plan change approval."""

import json
from datetime import datetime, timezone
from ..agent.types import ToolSpec, AgentEvent

_plans: dict[str, list[dict]] = {}
_resources: dict[str, list[dict]] = {}
_reports: dict[str, dict] = {}  # resource_id -> markdown content


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
    plan_key = "default"

    if operation == "create":
        if not tasks:
            return "Provide 'tasks' array.", False
        _plans[plan_key] = [{"title": t.get("title", ""), "status": t.get("status", "pending")} for t in tasks]
        await _emit_plan(session, plan_key)
        return _format_plan(plan_key), True

    elif operation == "add":
        if not title:
            return "Provide 'title'.", False
        if plan_key not in _plans:
            _plans[plan_key] = []
        _plans[plan_key].append({"title": title, "status": "pending"})
        await _emit_plan(session, plan_key)
        return _format_plan(plan_key), True

    elif operation == "update":
        if plan_key not in _plans:
            return "No plan exists.", False
        if task_index is None or status is None:
            return "Provide 'task_index' and 'status'.", False
        if task_index < 0 or task_index >= len(_plans[plan_key]):
            return f"Invalid index {task_index}.", False

        task = _plans[plan_key][task_index]
        old_status = task["status"]
        task["status"] = status
        await _emit_plan(session, plan_key)

        # Auto-generate completion report when task marked completed
        if status == "completed" and old_status != "completed":
            report = _generate_completion_report(task["title"], summary, next_hints)
            report_id = f"report-{task_index}-{len(_resources.get(plan_key, []))}"
            _reports[report_id] = report

            if plan_key not in _resources:
                _resources[plan_key] = []
            _resources[plan_key].append({
                "title": f"Report: {task['title']}",
                "url": "",
                "type": "report",
                "id": report_id,
                "content": report,
            })
            await _emit_resources(session, plan_key)

            result = _format_plan(plan_key)
            result += f"\n\nCompletion report generated for: {task['title']}"
            if next_hints:
                result += f"\nHints for next tasks: {next_hints}"
            return result, True

        return _format_plan(plan_key), True

    elif operation == "get":
        result = _format_plan(plan_key)
        # Include any next_hints from recent reports for context
        recent_reports = _resources.get(plan_key, [])
        report_resources = [r for r in recent_reports if r.get("type") == "report"]
        if report_resources:
            last_report = report_resources[-1]
            content = last_report.get("content", "")
            # Extract hints section
            if "## Next Steps" in content:
                hints = content.split("## Next Steps")[1].strip()
                result += f"\n\nFrom latest report — next steps:\n{hints}"
        return result, True

    elif operation == "add_resource":
        if not title:
            return "Provide 'title'.", False
        if plan_key not in _resources:
            _resources[plan_key] = []
        resource = {"title": title, "url": url or "", "type": resource_type}
        if resource_type == "report" and content:
            rid = f"report-manual-{len(_resources[plan_key])}"
            resource["id"] = rid
            resource["content"] = content
            _reports[rid] = content
        _resources[plan_key].append(resource)
        await _emit_resources(session, plan_key)
        return f"Added resource: {title}", True

    return f"Unknown operation: {operation}", False


def get_report_content(report_id: str) -> str | None:
    """Retrieve a stored report by ID. Used by the API."""
    return _reports.get(report_id)


def get_all_reports() -> dict:
    """Get all reports for reference."""
    return dict(_reports)


def _generate_completion_report(task_title: str, summary: str = None, next_hints: str = None) -> str:
    """Generate a structured markdown completion report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# Task Completion Report: {task_title}",
        f"",
        f"**Completed**: {now}",
        f"",
        f"## Summary",
        f"",
        summary or "No summary provided.",
        f"",
    ]
    if next_hints:
        lines.extend([
            f"## Next Steps",
            f"",
            next_hints,
            f"",
        ])
    return "\n".join(lines)


async def _emit_plan(session, plan_key: str):
    if session:
        await session.emit(AgentEvent(
            event_type="plan_update",
            data={"tasks": _plans.get(plan_key, [])},
        ))


async def _emit_resources(session, plan_key: str):
    if session:
        await session.emit(AgentEvent(
            event_type="resources_update",
            data={"resources": _resources.get(plan_key, [])},
        ))


def _format_plan(plan_key: str) -> str:
    plan = _plans.get(plan_key, [])
    if not plan:
        return "Plan is empty."
    icons = {"pending": "[ ]", "in_progress": "[*]", "completed": "[x]", "cancelled": "[-]"}
    lines = ["## Current Plan\n"]
    for i, t in enumerate(plan):
        lines.append(f"{i}. {icons.get(t['status'], '[ ]')} {t['title']}")
    done = sum(1 for t in plan if t["status"] == "completed")
    lines.append(f"\nProgress: {done}/{len(plan)}")
    return "\n".join(lines)
