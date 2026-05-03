"""ContextManager — message history, compaction, undo, token tracking."""

import logging
from dataclasses import dataclass, field

from ..config import AgentConfig, get_model_max_tokens
from .types import Message, ToolCall

_logger = logging.getLogger(__name__)

# Cache tiktoken encoder at module level for performance
_tiktoken_encoder = None
_tiktoken_available = False


def _get_tiktoken_encoder():
    """Lazily load tiktoken encoder. Returns None if tiktoken not available."""
    global _tiktoken_encoder, _tiktoken_available
    if _tiktoken_available:
        return _tiktoken_encoder  # Already attempted (may be None if import failed)
    _tiktoken_available = True  # Mark as attempted regardless of outcome
    try:
        import tiktoken

        _tiktoken_encoder = tiktoken.get_encoding("cl100k_base")  # Works for GPT-4, Claude
        return _tiktoken_encoder
    except Exception:
        return None


def estimate_tokens(text: str) -> int:
    """Estimate token count. Uses tiktoken if available, falls back to len//4."""
    if not text:
        return 1
    encoder = _get_tiktoken_encoder()
    if encoder:
        try:
            return len(encoder.encode(text))
        except Exception:
            pass
    return max(1, len(text) // 4)


@dataclass
class ContextManager:
    config: AgentConfig
    messages: list[Message] = field(default_factory=list)
    system_prompt: str = ""
    running_token_count: int = 0
    _previous_summary: str = ""

    def add_message(self, msg: Message | dict) -> None:
        if isinstance(msg, dict):
            tool_calls = None
            if msg.get("tool_calls"):
                tool_calls = [
                    ToolCall(
                        id=tc.get("id", tc.get("tool_call_id", "")),
                        name=tc.get("name", tc.get("function", {}).get("name", "")),
                        arguments=tc.get("arguments", tc.get("function", {}).get("arguments", {})),
                    )
                    for tc in msg["tool_calls"]
                ]
            msg = Message(
                role=msg.get("role", "user"),
                content=msg.get("content", ""),
                tool_calls=tool_calls,
                tool_call_id=msg.get("tool_call_id"),
                name=msg.get("name"),
            )
        self.messages.append(msg)
        # Proactively track token growth
        self.running_token_count += estimate_tokens(msg.content or "")

    def get_messages(self, include_system: bool = True) -> list[dict]:
        result = []
        if include_system and self.system_prompt:
            result.append({"role": "system", "content": self.system_prompt})

        for msg in self.messages:
            entry: dict = {"role": msg.role, "content": msg.content}
            if msg.tool_calls:
                entry["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": tc.arguments},
                    }
                    for tc in msg.tool_calls
                ]
            if msg.tool_call_id:
                entry["tool_call_id"] = msg.tool_call_id
            if msg.name:
                entry["name"] = msg.name
            result.append(entry)
        return result

    def get_token_usage(self) -> dict:
        """Return current token usage stats for the UI."""
        model_max = get_model_max_tokens(self.config.model_name)
        used = self.running_token_count
        ratio = used / model_max if model_max > 0 else 0
        return {"used": used, "max": model_max, "ratio": round(ratio, 3)}

    def needs_compaction(self) -> bool:
        model_max = get_model_max_tokens(self.config.model_name)
        threshold = int(model_max * self.config.compact_threshold_ratio)
        return self.running_token_count > threshold

    def undo_last_turn(self) -> int:
        removed = 0
        while self.messages and self.messages[-1].role != "user":
            msg = self.messages.pop()
            self.running_token_count -= estimate_tokens(msg.content or "")
            removed += 1
        if self.messages and self.messages[-1].role == "user":
            msg = self.messages.pop()
            self.running_token_count -= estimate_tokens(msg.content or "")
            removed += 1
        self.running_token_count = max(0, self.running_token_count)
        return removed

    def _prune_old_tool_outputs(self, protected_tail_count: int) -> int:
        """Phase 1: Replace old verbose tool outputs with stubs.

        Only prunes tool messages outside the protected tail.
        Returns count of messages pruned.
        """
        pruned = 0
        cutoff = len(self.messages) - protected_tail_count
        for i, msg in enumerate(self.messages):
            if i >= cutoff:
                break
            if msg.role == "tool" and msg.content and len(msg.content) > 200:
                old_tokens = estimate_tokens(msg.content)
                msg.content = (
                    "[Old tool output cleared to save context — use read to re-fetch if needed]"
                )
                new_tokens = estimate_tokens(msg.content)
                self.running_token_count -= old_tokens - new_tokens
                pruned += 1
        return pruned

    def _find_tail_boundary(self) -> int:
        """Phase 2: Find the boundary index for the protected tail.

        Walks backward from the end, accumulating tokens until budget is exhausted.
        Aligns to avoid splitting tool_call/tool_result pairs.
        Falls back to self.config.untouched_messages if budget protects fewer.
        """
        model_max = get_model_max_tokens(self.config.model_name)
        # Protect ~20% of the threshold budget as tail
        tail_budget = int(model_max * self.config.compact_threshold_ratio * 0.20)

        accumulated = 0
        boundary = len(self.messages)
        for i in range(len(self.messages) - 1, -1, -1):
            tokens = estimate_tokens(self.messages[i].content or "")
            if accumulated + tokens > tail_budget:
                break
            accumulated += tokens
            boundary = i

        # Don't protect fewer than untouched_messages
        min_boundary = max(0, len(self.messages) - self.config.untouched_messages)
        boundary = min(boundary, min_boundary)

        # Align boundary backward to avoid splitting tool_call/tool_result pairs
        while boundary > 0 and boundary < len(self.messages):
            msg = self.messages[boundary]
            # If we're landing on a tool result, walk back to include the assistant+tool_calls
            if msg.role == "tool":
                boundary -= 1
            else:
                break

        return max(self.config.untouched_messages, boundary)

    def _patch_dangling_tool_calls(self) -> None:
        i = 0
        while i < len(self.messages):
            msg = self.messages[i]
            if msg.role == "assistant" and msg.tool_calls:
                for tc in msg.tool_calls:
                    has_result = any(
                        m.role == "tool" and m.tool_call_id == tc.id for m in self.messages[i + 1 :]
                    )
                    if not has_result:
                        stub = Message(
                            role="tool",
                            content="[Tool not executed — conversation was compacted]",
                            tool_call_id=tc.id,
                            name=tc.name,
                        )
                        self.messages.append(stub)
            i += 1

    async def compact(self, llm_call) -> str | None:
        """Structured 4-phase context compression.

        Phase 1: Prune old tool outputs (cheap, no LLM)
        Phase 2: Determine boundaries (token-budget tail protection)
        Phase 3: Generate structured summary (research-adapted template)
        Phase 4: Assemble compressed messages
        """
        if len(self.messages) <= self.config.untouched_messages + 3:
            return None

        # Phase 1: Prune old tool outputs
        tail_boundary = self._find_tail_boundary()
        pruned = self._prune_old_tool_outputs(tail_boundary - self.config.untouched_messages)

        # Check if pruning alone was enough
        if not self.needs_compaction() and pruned > 0:
            return f"Pruned {pruned} old tool outputs (no summary needed)."

        # Phase 2: Determine boundaries
        head_count = min(self.config.untouched_messages, len(self.messages))
        middle = self.messages[head_count:tail_boundary]
        if not middle:
            return None

        # Phase 3: Generate structured summary
        summary_prompt = _build_research_summary_prompt(self._previous_summary)
        summary_messages = [
            {"role": "system", "content": summary_prompt},
        ]
        for msg in middle:
            # Normalize roles for the summary LLM call — "tool" and "system"
            # are not valid standalone roles for all providers (esp. Anthropic)
            role = "user" if msg.role in ("user", "tool", "system") else "assistant"
            summary_messages.append({"role": role, "content": msg.content or ""})
        summary_messages.append(
            {
                "role": "user",
                "content": (
                    "Produce a structured summary of the conversation above. "
                    "If a previous summary is included, UPDATE it — move items from "
                    "'In Progress' to 'Done', add new progress, remove obsolete info."
                ),
            }
        )

        summary = await llm_call(summary_messages, self.config)
        if not summary:
            return None

        # Store for iterative re-compression
        self._previous_summary = summary

        # Phase 4: Assemble compressed messages
        # Add compaction note to first message on first compression
        head = self.messages[:head_count]
        tail = self.messages[tail_boundary:]

        self.messages = (
            head + [Message(role="system", content=f"## Conversation Summary\n\n{summary}")] + tail
        )
        self._patch_dangling_tool_calls()

        # Recalculate token count
        self.running_token_count = sum(estimate_tokens(m.content or "") for m in self.messages)
        self.running_token_count += estimate_tokens(self.system_prompt)
        return summary

    def clear(self) -> None:
        self.messages.clear()
        self.running_token_count = 0
        self._previous_summary = ""


def _build_research_summary_prompt(previous_summary: str = "") -> str:
    """Build a structured summary prompt for research conversations."""
    base = (
        "You are summarizing an ML research conversation. Produce a structured "
        "summary using EXACTLY this format:\n\n"
        "## Research Goal\n"
        "[What the user is investigating]\n\n"
        "## Papers & Sources\n"
        "[Papers found/read/cited — include IDs and key findings]\n\n"
        "## Methodology Decisions\n"
        "[Research approach, methods chosen, frameworks selected]\n\n"
        "## Progress\n"
        "### Done\n[Completed work — specific files, commands, results]\n"
        "### In Progress\n[Work currently underway]\n"
        "### Blocked\n[Any blockers or issues]\n\n"
        "## Code & Experiments\n"
        "[Scripts written, experiments run, results observed]\n\n"
        "## Key Findings\n"
        "[Important results, discoveries, insights]\n\n"
        "## Next Steps\n"
        "[What needs to happen next]\n\n"
        "Be concise but preserve specific details (file paths, paper IDs, "
        "exact error messages, numeric results)."
    )
    if previous_summary:
        base += (
            f"\n\n--- PREVIOUS SUMMARY (update this, don't start from scratch) ---\n"
            f"{previous_summary}"
        )
    return base
