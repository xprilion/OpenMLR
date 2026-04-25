"""ask_user tool — structured questions with options for the user.

The agent calls this to pause and ask the user questions.
Each question has 2-4 options. The tool emits a 'questions' SSE event,
then blocks until the user answers. Answers come back via POST /api/answers.
"""

import asyncio
from ..agent.types import ToolSpec, AgentEvent


def create_ask_user_tool() -> ToolSpec:
    return ToolSpec(
        name="ask_user",
        description=(
            "Ask the user structured questions before proceeding. Each question "
            "must have 2-4 options to pick from. If you need more than 4 options, "
            "split into multiple questions. The user's answers are returned as a "
            "formatted summary. Use this in Plan mode to clarify scope, preferences, "
            "and constraints before doing work."
        ),
        parameters={
            "type": "object",
            "properties": {
                "questions": {
                    "type": "array",
                    "description": "List of questions to ask",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "Unique question ID (e.g. q1, q2)"},
                            "question": {"type": "string", "description": "The question text"},
                            "allow_text": {"type": "boolean", "description": "Allow typing a custom answer (default true)"},
                            "options": {
                                "type": "array",
                                "description": "2-4 options to choose from",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "label": {"type": "string", "description": "Short option label"},
                                        "description": {"type": "string", "description": "Explanation of this option"},
                                    },
                                    "required": ["label"],
                                },
                            },
                        },
                        "required": ["id", "question", "options"],
                    },
                },
                "context": {
                    "type": "string",
                    "description": "Brief context about why you're asking these questions",
                },
                "suggest_mode": {
                    "type": "string",
                    "description": "If confident, suggest the user switch to this mode after answering (e.g. 'research', 'write')",
                    "enum": ["research", "write"],
                },
            },
            "required": ["questions"],
        },
        handler=_handle_ask_user,
    )


async def _handle_ask_user(
    questions: list[dict],
    context: str = "",
    suggest_mode: str = None,
    session=None,
    **kwargs,
) -> tuple[str, bool]:
    """Emit questions to the UI and wait for answers."""
    if not session:
        return "Cannot ask user: no session available.", False

    if not questions:
        return "No questions provided.", False

    # Validate: each question needs 2-4 options
    for q in questions:
        opts = q.get("options", [])
        if len(opts) < 2:
            return f"Question '{q.get('id', '?')}' needs at least 2 options.", False
        if len(opts) > 4:
            return f"Question '{q.get('id', '?')}' has {len(opts)} options. Max is 4 — split into multiple questions.", False

    # Emit the questions event
    await session.emit(AgentEvent(
        event_type="questions",
        data={
            "questions": questions,
            "context": context,
            "suggest_mode": suggest_mode,
        },
    ))

    # Store the pending questions on the session and wait for answers
    answer_future = asyncio.get_event_loop().create_future()
    session.pending_answers = answer_future

    try:
        # Wait up to 5 minutes for user to answer
        answers = await asyncio.wait_for(answer_future, timeout=300)
    except asyncio.TimeoutError:
        session.pending_answers = None
        return "User did not answer within 5 minutes.", False

    session.pending_answers = None

    # Format answers as a readable summary
    lines = ["User's answers:"]
    for q in questions:
        qid = q.get("id", "")
        answer = answers.get(qid, "No answer")
        lines.append(f"- {q.get('question', '')}: **{answer}**")

    return "\n".join(lines), True
