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

ERR_SWEEP_ID_REQUIRED = "Error: `sweep_id` is required."


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


def _handle_create_sweep(engine: SweepEngine, proj: str, kwargs: dict[str, Any]) -> tuple[str, bool]:
    name = kwargs.get("name")
    if not name:
        return "Error: `name` is required when creating a sweep.", False
    param_dict = _parse_dict(kwargs.get("parameters"))
    if not param_dict:
        return "Error: `parameters` search space dictionary is required.", False

    sweep = engine.create_sweep(
        project_id=proj,
        name=name,
        method=kwargs.get("method", "random"),
        objective_metric=kwargs.get("objective_metric", "val_loss"),
        goal=kwargs.get("goal", "minimize"),
        parameters=param_dict,
        max_trials=int(kwargs.get("max_trials", 10)),
        description=kwargs.get("description", ""),
        early_stopping=_parse_dict(kwargs.get("early_stopping")),
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


def _handle_list_sweeps(engine: SweepEngine, proj: str) -> tuple[str, bool]:
    sweeps = engine.list_sweeps(proj)
    if not sweeps:
        return f"No hyperparameter sweeps found for project `{proj}`.", True
    lines = [f"### Hyperparameter Sweeps for `{proj}` ({len(sweeps)})", ""]
    for s in sweeps:
        completed = len([t for t in s.trials if t.status == "completed"])
        lines.append(
            f"- **{s.name}** (`{s.sweep_id}`): {s.method.upper()}, "
            f"Target: `{s.objective_metric}` ({s.goal}), "
            f"Trials: {completed}/{len(s.trials)} (Max: {s.max_trials}), "
            f"Status: `{s.status}`"
        )
    return "\n".join(lines), True


def _handle_suggest_trial(engine: SweepEngine, proj: str, sweep_id: str | None) -> tuple[str, bool]:
    if not sweep_id:
        return ERR_SWEEP_ID_REQUIRED, False
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


def _handle_record_trial(engine: SweepEngine, proj: str, kwargs: dict[str, Any]) -> tuple[str, bool]:
    sweep_id = kwargs.get("sweep_id")
    trial_id = kwargs.get("trial_id")
    if not sweep_id or not trial_id:
        return "Error: Both `sweep_id` and `trial_id` are required.", False

    trial = engine.record_trial_result(
        project_id=proj,
        sweep_id=sweep_id,
        trial_id=trial_id,
        metrics=_parse_dict(kwargs.get("metrics")),
        status=kwargs.get("status", "completed"),
    )
    msg = (
        f"✅ Trial `{trial.trial_id}` recorded with status `{trial.status}`.\n"
        f"- Objective Value: `{trial.objective_value}`\n"
        f"- Runtime: {trial.duration_seconds}s\n"
        f"- Metrics: {json.dumps(trial.metrics)}"
    )
    return msg, True


def _handle_prune_check(engine: SweepEngine, proj: str, kwargs: dict[str, Any]) -> tuple[str, bool]:
    sweep_id = kwargs.get("sweep_id")
    trial_id = kwargs.get("trial_id")
    if not sweep_id or not trial_id:
        return "Error: Both `sweep_id` and `trial_id` are required.", False

    step = int(kwargs.get("current_step", 1))
    val = float(kwargs.get("current_metric_val", 0.0))
    should_stop = engine.should_prune_trial(
        project_id=proj,
        sweep_id=sweep_id,
        trial_id=trial_id,
        current_step=step,
        current_metric_val=val,
    )
    verdict = "PRUNE / STOP EARLY" if should_stop else "CONTINUE"
    return f"Prune evaluation for trial `{trial_id}` at step {step} (value={val}): **{verdict}**", True


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

    async def _execute(action: str = "list_sweeps", **kwargs: Any) -> tuple[str, bool]:
        proj = _resolve_project(kwargs.get("project_id"))
        act = (action or "list_sweeps").lower().strip()
        sweep_id = kwargs.get("sweep_id")

        try:
            if act in ("create", "create_sweep"):
                return _handle_create_sweep(engine, proj, kwargs)
            if act in ("list", "list_sweeps"):
                return _handle_list_sweeps(engine, proj)
            if act in ("get", "get_sweep"):
                if not sweep_id:
                    return ERR_SWEEP_ID_REQUIRED, False
                sweep = engine.get_sweep(proj, sweep_id)
                if not sweep:
                    return f"Error: Sweep `{sweep_id}` not found.", False
                return json.dumps(sweep.to_dict(), indent=2), True
            if act in ("suggest", "suggest_trial", "next_trial"):
                return _handle_suggest_trial(engine, proj, sweep_id)
            if act in ("record", "record_trial", "log_trial"):
                return _handle_record_trial(engine, proj, kwargs)
            if act in ("prune_check", "should_prune"):
                return _handle_prune_check(engine, proj, kwargs)
            if act in ("analyze", "analyze_sweep"):
                if not sweep_id:
                    return ERR_SWEEP_ID_REQUIRED, False
                return json.dumps(engine.analyze_sweep(proj, sweep_id), indent=2), True
            if act in ("export", "export_report"):
                if not sweep_id:
                    return ERR_SWEEP_ID_REQUIRED, False
                return engine.export_sweep_markdown(proj, sweep_id), True

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
