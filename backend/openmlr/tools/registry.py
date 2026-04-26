"""ToolRouter — registers, dispatches, and manages all agent tools."""

import inspect
from typing import Optional
from ..agent.types import ToolSpec, ToolCall


# Define which tools are allowed in each mode
# Tools not listed are allowed in all modes
MODE_TOOL_RESTRICTIONS = {
    "plan": {
        # In plan mode: only planning, asking, and reading tools
        "allowed": {
            "ask_user", "plan_tool",
            # Read-only tools
            "read_file", "list_dir", "glob_files", "grep_search",
        },
        "blocked_message": (
            "Tool '{tool}' is not available in PLAN mode. "
            "Plan mode is for planning and asking questions only. "
            "Suggest switching to research or write mode using ask_user with suggest_mode."
        ),
    },
    "research": {
        # In research mode: search, papers, reading, planning — NO ask_user
        "allowed": {
            "plan_tool",
            "web_search", "papers", "research",
            "read_file", "list_dir", "glob_files", "grep_search",
            "github_search", "github_read_file", "github_read_repo",
        },
        "blocked_message": (
            "Tool '{tool}' is not available in RESEARCH mode. "
            "Research mode is for searching, reading papers, and gathering information. "
            "Do NOT ask the user questions in this mode — just do the research. "
            "If you need clarification, present your findings first."
        ),
    },
    "write": {
        # In write mode: writing, planning, reading, limited search — NO ask_user
        "allowed": {
            "plan_tool", "writing",
            "read_file", "list_dir", "glob_files", "grep_search",
            "web_search", "papers",  # For citations
        },
        "blocked_message": (
            "Tool '{tool}' is not available in WRITE mode. "
            "Write mode is for drafting and editing content. "
            "Do NOT ask the user questions in this mode — just write."
        ),
    },
    # "general" mode has no restrictions
}


class ToolRouter:
    """Central tool registry and dispatcher."""

    def __init__(self):
        self.tools: dict[str, ToolSpec] = {}
        self._mcp_client = None
        self._blocklist: set[str] = set()
        self._current_mode: str = "general"

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
        """
        if self._current_mode not in MODE_TOOL_RESTRICTIONS:
            return True, ""
        
        restrictions = MODE_TOOL_RESTRICTIONS[self._current_mode]
        allowed_tools = restrictions.get("allowed", set())
        
        if name in allowed_tools:
            return True, ""
        
        error_msg = restrictions.get("blocked_message", "Tool '{tool}' not allowed in this mode.")
        return False, error_msg.format(tool=name, mode=self._current_mode)

    def get_tool(self, name: str) -> Optional[ToolSpec]:
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
            
            specs.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            })
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
                    f"⚠️ MODE VIOLATION: {error_msg}\n\n"
                    f"Current mode: {self._current_mode.upper()}\n"
                    f"To use this tool, ask the user to switch modes using ask_user with suggest_mode parameter."
                )
                return warning, False
        
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
            return await tool.handler(**kwargs) if kwargs else await tool.handler(arguments)

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
    from .local import create_local_tools
    from .github import create_github_tools
    from .search import create_search_tools
    from .research import create_research_tool
    from .plan import create_plan_tool
    from .papers import create_papers_tool
    from .writing import create_writing_tool
    from .ask_user import create_ask_user_tool

    router.register_many(create_local_tools())
    router.register_many(create_github_tools())
    router.register_many(create_search_tools())
    router.register(create_research_tool())
    router.register(create_plan_tool())
    router.register(create_papers_tool())
    router.register(create_writing_tool())
    router.register(create_ask_user_tool())

    # Register sandbox tools if manager provided
    if sandbox_manager:
        from .sandbox_tools import create_sandbox_tools
        router.register_many(create_sandbox_tools(sandbox_manager))

    return router
