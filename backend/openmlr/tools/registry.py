"""ToolRouter — registers, dispatches, and manages all agent tools."""

import inspect
import logging

from ..agent.types import ToolSpec

logger = logging.getLogger("openmlr.tools.registry")

# Define which tools are allowed in each mode
# Tools not listed are allowed in all modes
MODE_TOOL_RESTRICTIONS = {
    "plan": {
        # Plan mode: ask questions, create plans, read context — NO execution tools.
        # Tool names here must EXACTLY match the registered ToolSpec.name values.
        "allowed": {
            "ask_user",
            "plan_tool",
            # Read-only local filesystem access for gathering context
            "read",
            # Web / academic search
            "web_search",
            "papers",
            # GitHub (read-only)
            "github_read_file",
            "github_find_examples",
            "github_search_repos",
            "github_get_readme",
            "github_list_repos",
            # Hugging Face (read-only model/dataset discovery)
            "hf_search_models",
            "hf_model_info",
            "hf_search_datasets",
            "hf_dataset_info",
            "hf_read_file",
            # Compute planning (read-only / advisory)
            "compute_list",
            "compute_plan",
            "compute_probe",
            # Workspace (knowledge graph, notes, search — always accessible)
            "workspace",
        },
        "blocked_message": (
            "Tool '{tool}' is not available in PLAN mode. "
            "Plan mode is for asking questions, planning tasks, and gathering context. "
            "Switch to Execute mode to run tools, write content, or execute code."
        ),
    },
    "execute": {
        # Execute mode: all tools EXCEPT ask_user — just do the work
        "blocked": {"ask_user"},
        "blocked_message": (
            "Tool '{tool}' is not available in EXECUTE mode. "
            "Execute mode is for doing the work — do not ask questions, just execute the plan."
        ),
    },
}


class ToolRouter:
    """Central tool registry and dispatcher."""

    def __init__(self):
        self.tools: dict[str, ToolSpec] = {}
        self._mcp_client = None
        self._blocklist: set[str] = set()
        self._current_mode: str = "general"
        self._user_id: int | None = None
        self._db = None

    def set_context(self, user_id: int | None = None, db=None) -> None:
        """Set per-request context (user_id, db) for tools that need them."""
        self._user_id = user_id
        self._db = db

    def register(self, spec: ToolSpec) -> None:
        """Register a tool."""
        if spec.name in self._blocklist:
            return
        self.tools[spec.name] = spec

    def register_many(self, specs: list[ToolSpec]) -> None:
        """Register multiple tools."""
        for spec in specs:
            self.register(spec)

    def set_mode(self, mode: str) -> None:
        """Set the current operating mode for tool filtering."""
        self._current_mode = mode

    def get_mode(self) -> str:
        """Get the current operating mode."""
        return self._current_mode

    def is_tool_allowed(self, name: str) -> tuple[bool, str]:
        """Check if a tool is allowed in the current mode.

        Returns (allowed, error_message).
        Supports both 'allowed' (whitelist) and 'blocked' (blacklist) sets.
        """
        if self._current_mode not in MODE_TOOL_RESTRICTIONS:
            return True, ""

        restrictions = MODE_TOOL_RESTRICTIONS[self._current_mode]

        # Blacklist mode: specific tools are blocked
        blocked_tools = restrictions.get("blocked", set())
        if blocked_tools:
            if name in blocked_tools:
                error_msg = restrictions.get(
                    "blocked_message", "Tool '{tool}' not allowed in this mode."
                )
                return False, error_msg.format(tool=name, mode=self._current_mode)
            return True, ""

        # Whitelist mode: only specific tools allowed
        allowed_tools = restrictions.get("allowed", set())
        if name in allowed_tools:
            return True, ""

        error_msg = restrictions.get("blocked_message", "Tool '{tool}' not allowed in this mode.")
        return False, error_msg.format(tool=name, mode=self._current_mode)

    async def _check_task_enforcement(self, tool_name: str, session) -> str | None:
        """Check if a work tool can run — requires an in_progress task when a plan exists.

        Returns an error message string if blocked, or None if allowed.
        """
        # plan_tool is always allowed (it's how you update task status)
        plan_allowed = MODE_TOOL_RESTRICTIONS.get("plan", {}).get("allowed", set())
        if tool_name in plan_allowed:
            return None

        # Lazy-load plan state from DB if not yet loaded this session
        if not getattr(session, "_plan_loaded", False):
            try:
                plan_tasks = await self._load_plan_from_db(session)
                session.plan_tasks = plan_tasks
                session._plan_loaded = True
            except Exception as e:
                logger.warning(f"Failed to load plan state for enforcement: {e}")
                # Don't block on DB errors — allow the tool call
                return None

        plan_tasks = getattr(session, "plan_tasks", None)
        if not plan_tasks:
            # No plan exists — no enforcement needed
            return None

        # Check if any task is in_progress
        in_progress = any(t.get("status") == "in_progress" for t in plan_tasks)
        if in_progress:
            return None

        # Check if all tasks are completed/cancelled (work is done)
        all_done = all(t.get("status") in ("completed", "cancelled") for t in plan_tasks)
        if all_done:
            return None

        return (
            f"TASK ENFORCEMENT: Cannot use '{tool_name}' without an active task.\n\n"
            f"A task plan exists but no task is marked as in_progress. "
            f"You must mark a task as in_progress before doing any work.\n\n"
            f"Steps:\n"
            f"1. Call plan_tool(operation='get') to review the current plan\n"
            f"2. Call plan_tool(operation='update', task_index=N, status='in_progress') "
            f"to start working on a task\n"
            f"3. Then you can use work tools like '{tool_name}'\n\n"
            f"After finishing work, mark the task completed with a summary before starting the next one."
        )

    async def _load_plan_from_db(self, session) -> list[dict] | None:
        """Load plan tasks from DB for a session. Used for lazy enforcement init."""
        conv_id = getattr(session, "conversation_id", None)
        if not conv_id:
            return None

        from ..db import operations as ops
        from .plan import _get_session_factory

        session_factory = _get_session_factory()
        async with session_factory() as db:
            tasks = await ops.get_conversation_tasks(db, conv_id)
            if not tasks:
                return None
            return [{"title": t.title, "status": t.status, "priority": t.priority} for t in tasks]

    def get_tool(self, name: str) -> ToolSpec | None:
        """Look up a tool by name."""
        return self.tools.get(name)

    def get_tool_specs_for_llm(self, filter_by_mode: bool = True) -> list[dict]:
        """Convert registered tools to OpenAI function-calling format.

        If filter_by_mode is True, only returns tools allowed in the current mode.
        """
        specs = []
        for tool in self.tools.values():
            # Check if tool is allowed in current mode
            if filter_by_mode:
                allowed, _ = self.is_tool_allowed(tool.name)
                if not allowed:
                    continue

            specs.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                }
            )
        return specs

    def get_raw_specs(self) -> list[ToolSpec]:
        """Return raw ToolSpec list."""
        return list(self.tools.values())

    async def call_tool(
        self,
        name: str,
        arguments: dict,
        session=None,
        enforce_mode: bool = True,
    ) -> tuple[str, bool]:
        """Execute a tool call, dispatching to handler or MCP.

        If enforce_mode is True, checks if the tool is allowed in the current mode.
        """
        # Check mode restrictions first
        if enforce_mode:
            allowed, error_msg = self.is_tool_allowed(name)
            if not allowed:
                warning = (
                    f"MODE VIOLATION: {error_msg}\n\n"
                    f"Current mode: {self._current_mode.upper()}\n"
                    f"To use this tool, ask the user to switch modes using ask_user with suggest_mode parameter."
                )
                return warning, False

        # ENFORCEMENT: In execute mode, work tools require an in_progress task.
        # "Work tools" = anything NOT in the plan-mode allowed set (read-only tools).
        if enforce_mode and session and self._current_mode == "execute":
            violation = await self._check_task_enforcement(name, session)
            if violation:
                return violation, False

        tool = self.tools.get(name)
        if not tool:
            return f"Unknown tool: {name}", False

        # Built-in handler
        if tool.handler:
            # Check if handler accepts 'session' parameter
            sig = inspect.signature(tool.handler)
            kwargs = dict(arguments)
            if "session" in sig.parameters:
                kwargs["session"] = session
            # Also pass tool_call_id if the handler accepts it
            if "tool_call_id" in sig.parameters and "tool_call_id" not in kwargs:
                kwargs["tool_call_id"] = kwargs.pop("id", "")
            # Inject user_id and db for tools that need them (compute tools)
            if "user_id" in sig.parameters and "user_id" not in kwargs:
                kwargs["user_id"] = self._user_id
            if "db" in sig.parameters and "db" not in kwargs:
                kwargs["db"] = self._db
            try:
                return await tool.handler(**kwargs) if kwargs else await tool.handler(**arguments)
            except TypeError as e:
                # Handle argument mismatches (model sending wrong param names)
                return (
                    f"Tool argument error: {e}. Expected parameters: {list(sig.parameters.keys())}",
                    False,
                )

        # MCP tool (no handler — dispatch to MCP client)
        if self._mcp_client:
            try:
                result = await self._mcp_client.call_tool(name, arguments)
                return _convert_mcp_content(result), True
            except Exception as e:
                return f"MCP tool error: {str(e)}", False

        return f"Tool '{name}' has no handler and no MCP client configured.", False

    async def register_mcp_tools(self, mcp_client, blocklist: set[str] | None = None) -> int:
        """Register tools from an MCP client. Returns count of tools registered."""
        self._mcp_client = mcp_client
        self._blocklist = blocklist or set()
        count = 0

        try:
            tools = await mcp_client.list_tools()
            for tool in tools:
                if tool.name in self._blocklist or tool.name in self.tools:
                    continue
                spec = ToolSpec(
                    name=tool.name,
                    description=tool.description or "",
                    parameters=tool.input_schema or {"type": "object", "properties": {}},
                    handler=None,  # MCP tools dispatched via call_tool
                )
                self.tools[spec.name] = spec
                count += 1
        except Exception:
            pass

        return count


def _convert_mcp_content(result) -> str:
    """Convert MCP content blocks to a string."""
    if isinstance(result, str):
        return result
    parts = []
    if hasattr(result, "content"):
        for block in result.content:
            if hasattr(block, "text"):
                parts.append(block.text)
            elif hasattr(block, "data"):
                parts.append(f"[Binary content: {block.mime_type}]")
            else:
                parts.append(str(block))
    return "\n".join(parts) if parts else str(result)


def create_tool_router(sandbox_manager=None) -> ToolRouter:
    """Create a ToolRouter with all built-in tools registered."""
    router = ToolRouter()

    # Import and register all built-in tools
    from .ask_user import create_ask_user_tool
    from .github import create_github_tools
    from .huggingface import create_huggingface_tools
    from .local import create_local_tools
    from .papers import create_papers_tool
    from .plan import create_plan_tool
    from .research import create_research_tool
    from .search import create_search_tools
    from .writing import create_writing_tool

    router.register_many(create_local_tools())
    router.register_many(create_github_tools())
    router.register_many(create_huggingface_tools())
    router.register_many(create_search_tools())
    router.register(create_research_tool())
    router.register(create_plan_tool())
    router.register(create_papers_tool())
    router.register(create_writing_tool())
    router.register(create_ask_user_tool())

    # Register compute tools
    from .compute_tools import create_compute_tools

    router.register_many(create_compute_tools())

    # Register workspace tools
    from .workspace_tools import create_workspace_tools

    router.register_many(create_workspace_tools())

    # Register sandbox tools if manager provided
    if sandbox_manager:
        from .sandbox_tools import create_sandbox_tools

        router.register_many(create_sandbox_tools(sandbox_manager))

    return router
