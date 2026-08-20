"""Doom loop and repetitive ML failure detection — identifies repetitive tool call patterns and recurring ML errors."""

import hashlib
import json

from .ml_debugger import diagnose_ml_error
from .types import Message


def _hash_tool_call(name: str, args: dict) -> str:
    """Create a non-cryptographic fingerprint of a tool call for loop comparison."""
    key = json.dumps({"name": name, "args": args}, sort_keys=True)
    return hashlib.sha256(key.encode(), usedforsecurity=False).hexdigest()


def detect_ml_failure_loop(messages: list[Message], window: int = 15) -> str | None:
    """
    Analyze recent tool outputs for recurring ML failure modes (OOM, NaN, shape mismatch).

    Returns a specialized self-healing corrective prompt if a recurring ML failure is detected.
    """
    recent = messages[-window:]
    ml_errors = []

    for msg in recent:
        if msg.role == "tool" and msg.content:
            diag = diagnose_ml_error(msg.content)
            if diag is not None:
                ml_errors.append(diag)

    if not ml_errors:
        return None

    # Check if the same ML error category occurred at least twice
    category_counts: dict[str, int] = {}
    for err in ml_errors:
        category_counts[err.category.value] = category_counts.get(err.category.value, 0) + 1

    for _cat_name, count in category_counts.items():
        if count >= 2:
            latest_err = ml_errors[-1]
            return (
                f"[REPETITIVE ML FAILURE DETECTED]\n"
                f"You have encountered {latest_err.category.value} {count} times in recent steps.\n"
                f"{latest_err.remedy_prompt}"
            )

    return None


def detect_doom_loop(messages: list[Message], window: int = 30) -> str | None:
    """
    Analyze recent messages for doom loop patterns and repetitive ML failures.

    Returns a corrective prompt string if a loop is detected, None otherwise.

    Detects:
    1. Recurring ML execution failures (OOM, NaN, Shape, Missing Package)
    2. Identical consecutive calls: 3+ calls to the same tool with same args
    3. Repeating sequences: patterns like [A,B,A,B] over sequence lengths 2-5
    """
    # Check for recurring ML error loop first
    ml_loop = detect_ml_failure_loop(messages, window=min(window, 15))
    if ml_loop:
        return ml_loop

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
