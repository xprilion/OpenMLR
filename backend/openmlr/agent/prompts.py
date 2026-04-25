"""System prompt builder — loads Jinja2 YAML template and renders."""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml
from jinja2 import Template

from .types import ToolSpec
from ..config import AgentConfig


PROMPT_DIR = Path(__file__).parent.parent.parent / "configs" / "prompts"
COMPACT_PROMPT = (
    "Provide a concise summary of the conversation above, focusing on "
    "key decisions, the 'why' behind decisions, problems solved, and "
    "important context needed for continuing this work. "
    "Your summary will be given to someone who has never worked on this "
    "project before."
)


def build_system_prompt(
    tool_specs: list[ToolSpec],
    mode: str = "general",
    username: str = "user",
    sandbox_info: str = "none",
    config: Optional[AgentConfig] = None,
) -> str:
    """Build the full system prompt from YAML template."""
    template_path = PROMPT_DIR / "system_prompt.yaml"

    if template_path.exists():
        with open(template_path) as f:
            data = yaml.safe_load(f)
            template_str = data.get("prompt", "")
    else:
        # Fallback: inline prompt
        template_str = _fallback_prompt()

    cwd = os.getcwd()
    now = datetime.now(timezone.utc)

    template = Template(template_str)
    prompt = template.render(
        mode=mode,
        tool_specs=[
            {
                "name": ts.name,
                "description": ts.description,
                "parameters": ts.parameters,
            }
            for ts in tool_specs
        ],
        cwd=cwd,
        date=now.strftime("%Y-%m-%d"),
        time=now.strftime("%H:%M:%S UTC"),
        timezone="UTC",
        username=username,
        sandbox_info=sandbox_info,
    )

    return prompt


def _fallback_prompt() -> str:
    """Fallback system prompt if YAML template is missing."""
    return """You are OpenMLR, a skilled AI research intern specializing in machine learning.
You help users research, write, and ship ML-related work — from reading papers
to training models to writing full-length academic papers.

# Research-First Workflow
For any implementation task:
1. Search documentation and examples first
2. Formulate a plan using plan_tool
3. Implement using researched approaches

# Communication
- Be concise and direct
- Explain non-trivial operations
- Don't flatter or use excessive emojis
- Always do what the user tells you to

## Available Tools
{% for spec in tool_specs %}
### {{ spec.name }}
{{ spec.description }}
{% endfor %}

[Session context: Date={{ date }}, Time={{ time }}, User={{ username }}, CWD={{ cwd }}]
"""
