"""Sweeps tool — Hyperparameter optimization, search spaces, and trial tuning for AI research agents."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..agent.types import ToolSpec
from ..services.sweep_engine import SweepEngine

log = logging.getLogger(__name__)


def _parse_dict(val: Any) -> dict[str, Any]:
    """Parse dict or JSON string into dictionary."""
    if isinstance(val, dict):
        return val
    if isinstance(val, str) and val.strip():
        try:
            parsed = json.loads(val)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    return {}


def create_sweeps_tool(
    get_project_id: Callable[[], str | None] | None = None,
    base_dir: Path | None = None,
) -> ToolSpec:
    """Create the hyperparameter sweep and HPO tool for OpenMLR agent."""
    engine = SweepEngine(base_dir=base_dir)

    def _resolve_project(proj: str | None = None) -> str:
        if proj and proj.strip():
            return proj.strip()
        if get_project_id:
            pid = get_project_id()
            if pid and pid.strip():
                return pid.strip()
        return "default"

    async def _execute(
        action: str = "list_sweeps",
        sweep_id: str | None = None,
        name: str | None = None,
        method: str = "random",
        objective_metric: str = "val_loss",
        goal: str = "minimize",
        parameters: dict[str, Any] | str | None = None,
        max_trials: int = 10,
        description: str = "",
        early_stopping: dict[str, Any] | str | None = None,
        trial_id: str | None = None,
        metrics: dict[str, Any] | str | None = None,
        status: str = "completed",
        current_step: int = 1,
        current_metric_val: float = 0.0,
        project_id: str | None = None,
        **kwargs: Any,
    ) -> tuple[str, bool]:
        proj = _resolve_project(project_id)
        act = (action or "list_sweeps").lower().strip()

        try:
            if act in ("create", "create_sweep"):
                if not name:
                    return "Error: `name` is required when creating a sweep.", False
                param_dict = _parse_dict(parameters)
                if not param_dict:
                    return "Error: `parameters` search space dictionary is required.", False

                es_dict = _parse_dict(early_stopping)
                sweep = engine.create_sweep(
                    project_id=proj,
                    name=name,
                    method=method,
                    objective_metric=objective_metric,
                    goal=goal,
                    parameters=param_dict,
                    max_trials=max_trials,
                    description=description,
                    early_stopping=es_dict,
                )
                msg = (
                    f"✅ Hyperparameter sweep '{sweep.name}' created successfully!\n"
                    f"- Sweep ID: `{sweep.sweep_id}`\n"
                    f"- Method: `{sweep.method}`\n"
                    f"- Objective: `{sweep.objective_metric}` ({sweep.goal})\n"
                    f"- Max Trials: {sweep.max_trials}\n"
                    f"- Search Space: {list(sweep.parameters.keys())}"
                )
                return msg, True

            elif act in ("list", "list_sweeps"):
                sweeps = engine.list_sweeps(proj)
                if not sweeps:
                    return f"No hyperparameter sweeps found for project `{proj}`.", True
                lines = [f"### Hyperparameter Sweeps for `{proj}` ({len(sweeps)})", ""]
                for s in sweeps:
                    completed_trials = len([t for t in s.trials if t.status == "completed"])
                    lines.append(
                        f"- **{s.name}** (`{s.sweep_id}`): {s.method.upper()}, "
                        f"Target: `{s.objective_metric}` ({s.goal}), "
                        f"Trials: {completed_trials}/{len(s.trials)} (Max: {s.max_trials}), "
                        f"Status: `{s.status}`"
                    )
                return "\n".join(lines), True

            elif act in ("get", "get_sweep"):
                if not sweep_id:
                    return "Error: `sweep_id` is required.", False
                sweep = engine.get_sweep(proj, sweep_id)
                if not sweep:
                    return f"Error: Sweep `{sweep_id}` not found.", False
                return json.dumps(sweep.to_dict(), indent=2), True

            elif act in ("suggest", "suggest_trial", "next_trial"):
                if not sweep_id:
                    return "Error: `sweep_id` is required.", False
                trial = engine.suggest_trial(proj, sweep_id)
                if not trial:
                    return f"Sweep `{sweep_id}` has reached its maximum trial limit or is complete.", True
                msg = (
                    f"🎯 Suggested Next Trial: `{trial.trial_id}` (Trial #{trial.trial_number})\n"
                    f"**Hyperparameter Configuration**:\n```json\n"
                    f"{json.dumps(trial.parameters, indent=2)}\n```\n"
                    f"Status: `{trial.status}`"
                )
                return msg, True

            elif act in ("record", "record_trial", "log_trial"):
                if not sweep_id or not trial_id:
                    return "Error: Both `sweep_id` and `trial_id` are required.", False
                metric_dict = _parse_dict(metrics)
                trial = engine.record_trial_result(
                    project_id=proj,
                    sweep_id=sweep_id,
                    trial_id=trial_id,
                    metrics=metric_dict,
                    status=status,
                )
                msg = (
                    f"✅ Trial `{trial.trial_id}` recorded with status `{trial.status}`.\n"
                    f"- Objective Value: `{trial.objective_value}`\n"
                    f"- Runtime: {trial.duration_seconds}s\n"
                    f"- Metrics: {json.dumps(trial.metrics)}"
                )
                return msg, True

            elif act in ("prune_check", "should_prune"):
                if not sweep_id or not trial_id:
                    return "Error: Both `sweep_id` and `trial_id` are required.", False
                should_stop = engine.should_prune_trial(
                    project_id=proj,
                    sweep_id=sweep_id,
                    trial_id=trial_id,
                    current_step=current_step,
                    current_metric_val=current_metric_val,
                )
                msg = (
                    f"Prune evaluation for trial `{trial_id}` at step {current_step} "
                    f"(value={current_metric_val}): **{'PRUNE / STOP EARLY' if should_stop else 'CONTINUE'}**"
                )
                return msg, True

            elif act in ("analyze", "analyze_sweep"):
                if not sweep_id:
                    return "Error: `sweep_id` is required.", False
                analysis = engine.analyze_sweep(proj, sweep_id)
                return json.dumps(analysis, indent=2), True

            elif act in ("export", "export_report"):
                if not sweep_id:
                    return "Error: `sweep_id` is required.", False
                report = engine.export_sweep_markdown(proj, sweep_id)
                return report, True

            else:
                return (
                    f"Unknown action: '{action}'. "
                    "Allowed actions: `create_sweep`, `list_sweeps`, `get_sweep`, "
                    "`suggest_trial`, `record_trial`, `prune_check`, `analyze_sweep`, `export_report`.",
                    False,
                )

        except Exception as e:
            log.exception("Sweeps tool error: %s", e)
            return f"Error executing sweeps action '{action}': {e}", False

    return ToolSpec(
        name="sweeps",
        description=(
            "Hyperparameter Optimization (HPO) and Sweep Manager — create parameter search spaces, "
            "suggest trial configurations (Grid, Random, Bayesian, Hyperband), early-prune unpromising runs, "
            "analyze parameter sensitivity & correlations, and export optimization reports."
        ),
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "create_sweep",
                        "list_sweeps",
                        "get_sweep",
                        "suggest_trial",
                        "record_trial",
                        "prune_check",
                        "analyze_sweep",
                        "export_report",
                    ],
                    "description": "The sweep management action to execute.",
                },
                "sweep_id": {
                    "type": "string",
                    "description": "Identifier of the target sweep.",
                },
                "name": {
                    "type": "string",
                    "description": "Descriptive name for the sweep.",
                },
                "method": {
                    "type": "string",
                    "enum": ["grid", "random", "bayesian", "hyperband"],
                    "description": "Search method algorithm.",
                },
                "objective_metric": {
                    "type": "string",
                    "description": "Metric name to optimize (e.g. 'val_loss', 'accuracy', 'f1').",
                },
                "goal": {
                    "type": "string",
                    "enum": ["minimize", "maximize"],
                    "description": "Whether to minimize or maximize the objective metric.",
                },
                "parameters": {
                    "type": "object",
                    "description": "Dictionary defining parameter spaces (e.g. {'lr': {'param_type': 'loguniform', 'min_val': 1e-5, 'max_val': 1e-2}}).",
                },
                "max_trials": {
                    "type": "integer",
                    "description": "Maximum number of trials to run.",
                },
                "trial_id": {
                    "type": "string",
                    "description": "Trial identifier for record or prune operations.",
                },
                "metrics": {
                    "type": "object",
                    "description": "Dictionary of trial metrics (e.g. {'val_loss': 0.24, 'accuracy': 0.93}).",
                },
                "current_step": {
                    "type": "integer",
                    "description": "Current step or epoch for early pruning checks.",
                },
                "current_metric_val": {
                    "type": "number",
                    "description": "Current metric value for early pruning checks.",
                },
                "project_id": {
                    "type": "string",
                    "description": "Optional project ID override.",
                },
            },
            "required": ["action"],
        },
        handler=_execute,
    )
