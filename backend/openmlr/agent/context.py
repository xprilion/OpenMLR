"""ContextManager — message history, compaction, undo, token tracking."""

from dataclasses import dataclass, field

from ..config import AgentConfig, get_model_max_tokens
from .types import Message, ToolCall


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English text."""
    return max(1, len(text) // 4)


@dataclass
class ContextManager:
    config: AgentConfig
    messages: list[Message] = field(default_factory=list)
    system_prompt: str = ""
    running_token_count: int = 0

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
        if len(self.messages) <= self.config.untouched_messages + 3:
            return None

        middle = self.messages[self.config.untouched_messages : -self.config.untouched_messages]
        if not middle:
            return None

        summary_messages = [
            {"role": "system", "content": "Summarize the following conversation concisely."},
        ]
        for msg in middle:
            summary_messages.append({"role": msg.role, "content": msg.content})
        summary_messages.append(
            {
                "role": "user",
                "content": (
                    "Provide a concise summary focusing on: key decisions, problems solved, "
                    "current task progress, files/resources created, and what to do next."
                ),
            }
        )

        summary = await llm_call(summary_messages, self.config)
        if summary:
            self.messages = (
                self.messages[: self.config.untouched_messages]
                + [Message(role="system", content=f"## Conversation Summary\n\n{summary}")]
                + self.messages[-self.config.untouched_messages :]
            )
            self._patch_dangling_tool_calls()
            # Recalculate token count after compaction
            self.running_token_count = sum(estimate_tokens(m.content or "") for m in self.messages)
            self.running_token_count += estimate_tokens(self.system_prompt)
            return summary
        return None

    def clear(self) -> None:
        self.messages.clear()
        self.running_token_count = 0
