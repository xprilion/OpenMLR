"""Research sub-agent — spawns independent context for deep research."""

import asyncio
import json
import time
from ..agent.types import ToolSpec, Message, AgentEvent, ToolCall
from ..agent.llm import LLMProvider
from ..agent.doom_loop import detect_doom_loop
from ..config import AgentConfig


MAX_RESEARCH_ITERATIONS = 60
TOKEN_WARN_THRESHOLD = 170000
TOKEN_FORCE_STOP = 190000

RESEARCH_SYSTEM_PROMPT = """You are a research sub-agent for OpenMLR. Your job is to thoroughly
research a topic using the tools available to you. You have independent context
that won't affect the main conversation.

## Research Protocol

1. Start broad: search for papers, docs, and code examples
2. Go deep: read key papers section by section, crawl citation graphs
3. Cross-reference: compare methodologies across papers
4. Synthesize: create structured summaries with recipe tables

## Output Format

When done, provide a structured summary:
- Key findings (bulleted list)
- Recipe table if applicable:
  | Paper | Result | Dataset | Method | Key Insight |
- Recommended approach with citations
- Links to relevant code/repos

Be thorough but concise. Focus on actionable information."""


def create_research_tool() -> ToolSpec:
    return ToolSpec(
        name="research",
        description=(
            "Spawn an independent research sub-agent that searches docs, papers, "
            "and code without affecting the main conversation context. "
            "Use for deep dives into topics, literature surveys, "
            "finding implementations, etc. Returns structured findings."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Research question or topic to investigate deeply",
                },
                "focus": {
                    "type": "string",
                    "description": "Focus area: 'papers', 'code', 'docs', 'general' (default: general)",
                    "enum": ["papers", "code", "docs", "general"],
                },
            },
            "required": ["query"],
        },
        handler=_handle_research,
    )


async def _handle_research(query: str, focus: str = "general", session=None, **kwargs) -> tuple[str, bool]:
    """Execute research sub-agent with independent context."""

    # Get read-only tool subset for the sub-agent
    research_tools = _get_research_tool_specs()

    # Use a cheaper model
    config = AgentConfig(
        model_name=session.config.research_model if session else "openrouter/openai/gpt-4o-mini",
        stream=False,
        max_iterations=MAX_RESEARCH_ITERATIONS,
    )

    # Independent context
    messages = [
        {"role": "system", "content": RESEARCH_SYSTEM_PROMPT},
        {"role": "user", "content": f"Research the following topic thoroughly:\n\n{query}\n\nFocus: {focus}"},
    ]

    # Generate a parent ID for grouping sub-agent events
    parent_tc_id = kwargs.get("tool_call_id", f"research-{int(time.time())}")
    start_time = time.time()
    tool_count = 0

    # Emit sub-agent start
    if session:
        await session.emit(AgentEvent(
            event_type="sub_agent_start",
            data={
                "agent_type": "research",
                "description": f"Research: {query[:100]}",
                "parent_tool_call_id": parent_tc_id,
                "focus": focus,
            },
        ))

    accumulated_content = ""

    try:
        for iteration in range(MAX_RESEARCH_ITERATIONS):
            # Make LLM call
            result = await LLMProvider.generate(messages, config, research_tools)

            # Check for doom loop
            doom_messages = [Message(role=m["role"], content=m.get("content", "")) for m in messages]
            doom_msg = detect_doom_loop(doom_messages)
            if doom_msg:
                messages.append({"role": "system", "content": doom_msg})
                continue

            # No tool calls = research complete
            if not result.tool_calls:
                accumulated_content = result.content
                break

            # Add assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": result.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": tc.arguments},
                    }
                    for tc in result.tool_calls
                ],
            })

            # Execute tools and emit granular events
            for tc in result.tool_calls:
                tool_count += 1
                
                # Emit sub-agent tool call
                if session:
                    await session.emit(AgentEvent(
                        event_type="sub_agent_tool_call",
                        data={
                            "parent_tool_call_id": parent_tc_id,
                            "tool": tc.name,
                            "tool_call_id": tc.id,
                            "args": json.dumps(tc.arguments)[:200] if isinstance(tc.arguments, dict) else str(tc.arguments)[:200],
                        },
                    ))

                output, success = await _execute_research_tool(tc)
                messages.append({
                    "role": "tool",
                    "content": output[:10000],
                    "tool_call_id": tc.id,
                })

                # Emit sub-agent tool output
                if session:
                    await session.emit(AgentEvent(
                        event_type="sub_agent_tool_output",
                        data={
                            "parent_tool_call_id": parent_tc_id,
                            "tool_call_id": tc.id,
                            "tool": tc.name,
                            "output": output[:500],
                            "success": success,
                        },
                    ))

    except Exception as e:
        duration = time.time() - start_time
        if session:
            await session.emit(AgentEvent(
                event_type="sub_agent_end",
                data={
                    "parent_tool_call_id": parent_tc_id,
                    "tool_count": tool_count,
                    "duration_seconds": round(duration, 1),
                    "summary": f"Error: {str(e)}",
                    "success": False,
                },
            ))
        return f"Research sub-agent error: {str(e)}", False

    if not accumulated_content:
        accumulated_content = "Research completed but no summary was generated."

    duration = time.time() - start_time

    # Emit sub-agent end with stats
    if session:
        await session.emit(AgentEvent(
            event_type="sub_agent_end",
            data={
                "parent_tool_call_id": parent_tc_id,
                "tool_count": tool_count,
                "duration_seconds": round(duration, 1),
                "summary": accumulated_content[:500],
                "success": True,
            },
        ))

    return accumulated_content, True


def _get_research_tool_specs() -> list[dict]:
    """Get the read-only tool subset for research."""
    from .search import create_search_tools
    from .papers import create_papers_tool
    from .github import create_github_tools

    tools = []
    for spec in create_search_tools():
        tools.append({
            "type": "function",
            "function": {
                "name": spec.name,
                "description": spec.description,
                "parameters": spec.parameters,
            },
        })

    papers = create_papers_tool()
    tools.append({
        "type": "function",
        "function": {
            "name": papers.name,
            "description": papers.description,
            "parameters": papers.parameters,
        },
    })

    for spec in create_github_tools():
        if spec.name in ("github_read_file", "github_find_examples"):
            tools.append({
                "type": "function",
                "function": {
                    "name": spec.name,
                    "description": spec.description,
                    "parameters": spec.parameters,
                },
            })

    return tools


async def _execute_research_tool(tc: ToolCall) -> tuple[str, bool]:
    """Execute a tool call for the research sub-agent."""
    from .search import _handle_web_search
    from .papers import _handle_papers
    from .github import _handle_read_file, _handle_find_examples

    handlers = {
        "web_search": _handle_web_search,
        "papers": _handle_papers,
        "github_read_file": _handle_read_file,
        "github_find_examples": _handle_find_examples,
    }

    handler = handlers.get(tc.name)
    if not handler:
        return f"Tool {tc.name} not available in research mode.", False

    try:
        return await handler(**tc.arguments)
    except Exception as e:
        return f"Tool error: {str(e)}", False
