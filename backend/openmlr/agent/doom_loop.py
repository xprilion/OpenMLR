"""Doom loop detection — identifies repetitive tool call patterns."""

import hashlib
import json

from .types import Message


def _hash_tool_call(name: str, args: dict) -> str:
    """Create a hash of a tool call for comparison."""
    key = json.dumps({"name": name, "args": args}, sort_keys=True)
    return hashlib.md5(key.encode()).hexdigest()


def detect_doom_loop(messages: list[Message], window: int = 30) -> str | None:
    """
    Analyze recent messages for doom loop patterns.

    Returns a corrective prompt string if a loop is detected, None otherwise.

    Detects:
    1. Identical consecutive calls: 3+ calls to the same tool with same args
    2. Repeating sequences: patterns like [A,B,A,B] over sequence lengths 2-5
    """
    # Extract tool calls from recent assistant messages
    recent = messages[-window:]
    call_hashes: list[tuple[str, str]] = []  # (tool_name, args_hash)

    for msg in recent:
        if msg.role == "assistant" and msg.tool_calls:
            for tc in msg.tool_calls:
                h = _hash_tool_call(tc.name, tc.arguments)
                call_hashes.append((tc.name, h))

    if len(call_hashes) < 3:
        return None

    # Pattern 1: Identical consecutive calls (3+)
    consecutive_count = 1
    for i in range(1, len(call_hashes)):
        if call_hashes[i] == call_hashes[i - 1]:
            consecutive_count += 1
            if consecutive_count >= 3:
                tool_name = call_hashes[i][0]
                return (
                    f"[DOOM LOOP DETECTED] You have called `{tool_name}` with "
                    f"identical arguments {consecutive_count} times in a row. "
                    f"This is not making progress. Try a completely different approach:\n"
                    f"- Use a different tool\n"
                    f"- Change the arguments significantly\n"
                    f"- Re-read the error message carefully\n"
                    f"- Ask the user for help if you're stuck"
                )
        else:
            consecutive_count = 1

    # Pattern 2: Repeating sequences (length 2-5, 2+ repetitions)
    for seq_len in range(2, 6):
        if len(call_hashes) < seq_len * 2:
            continue

        for start in range(len(call_hashes) - seq_len * 2 + 1):
            pattern = call_hashes[start : start + seq_len]
            repetitions = 1
            pos = start + seq_len

            while pos + seq_len <= len(call_hashes):
                candidate = call_hashes[pos : pos + seq_len]
                if candidate == pattern:
                    repetitions += 1
                    pos += seq_len
                else:
                    break

            if repetitions >= 2:
                tool_names = [p[0] for p in pattern]
                return (
                    f"[DOOM LOOP DETECTED] You are repeating a cycle of "
                    f"{' -> '.join(tool_names)} (repeated {repetitions} times). "
                    f"Break this cycle by:\n"
                    f"- Reconsidering your approach entirely\n"
                    f"- Reading the output more carefully\n"
                    f"- Trying a fundamentally different strategy\n"
                    f"- Asking the user for guidance"
                )

    return None
