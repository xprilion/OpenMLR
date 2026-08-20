"""Sweep analysis — parameter sensitivity, rank correlation, Pareto frontiers, and markdown reports."""

from __future__ import annotations

import math
from typing import Any

from .sweep_types import ParameterSpec, SweepConfig, Trial


def _compute_single_param_correlation(
    completed: list[Trial],
    p_name: str,
    spec: ParameterSpec,
) -> tuple[float, float]:
    """Compute Spearman/Pearson correlation and importance for a single parameter."""
    x_vals: list[float] = []
    valid_y: list[float] = []

    for t in completed:
        val = t.parameters.get(p_name)
        if val is None or t.objective_value is None:
            continue
        if spec.param_type in ("categorical", "choice"):
            x_vals.append(float(hash(str(val)) % 1000))
        else:
            try:
                x_vals.append(float(val))
            except (ValueError, TypeError):
                continue
        valid_y.append(t.objective_value)

    if len(x_vals) < 3 or len(set(x_vals)) <= 1:
        return 0.0, 0.1

    mean_x = sum(x_vals) / len(x_vals)
    mean_y = sum(valid_y) / len(valid_y)
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_vals, valid_y, strict=False))
    var_x = sum((x - mean_x) ** 2 for x in x_vals)
    var_y = sum((y - mean_y) ** 2 for y in valid_y)

    if var_x > 1e-9 and var_y > 1e-9:
        r = cov / (math.sqrt(var_x) * math.sqrt(var_y))
        return round(r, 3), round(abs(r), 3)

    return 0.0, 0.0


def _compute_parameter_sensitivities(
    completed: list[Trial],
    parameters: dict[str, ParameterSpec],
) -> tuple[dict[str, float], dict[str, float]]:
    """Compute normalized parameter importance and correlations."""
    importance: dict[str, float] = {}
    correlations: dict[str, float] = {}

    for p_name, spec in parameters.items():
        corr, imp = _compute_single_param_correlation(completed, p_name, spec)
        correlations[p_name] = corr
        importance[p_name] = imp

    total_imp = sum(importance.values())
    if total_imp > 0:
        importance = {k: round(v / total_imp, 3) for k, v in importance.items()}

    return importance, correlations


def _is_better_or_equal(val: float, baseline: float, goal: str) -> bool:
    return val <= baseline if goal == "minimize" else val >= baseline


def _is_strictly_better(val: float, baseline: float, goal: str) -> bool:
    return val < baseline if goal == "minimize" else val > baseline


def _is_dominated(candidate: Trial, others: list[Trial], goal: str) -> bool:
    """Check if candidate trial is dominated on both objective metric and duration."""
    c_obj = candidate.objective_value or 0.0
    c_dur = candidate.duration_seconds

    for other in others:
        if other.trial_id == candidate.trial_id:
            continue
        o_obj = other.objective_value or 0.0
        o_dur = other.duration_seconds

        if _is_better_or_equal(o_obj, c_obj, goal) and o_dur <= c_dur:
            if _is_strictly_better(o_obj, c_obj, goal) or o_dur < c_dur:
                return True
    return False


def _compute_pareto_frontier(completed: list[Trial], goal: str) -> list[dict[str, Any]]:
    """Find all non-dominated trials in the multi-objective space."""
    pareto: list[dict[str, Any]] = []
    for t in completed:
        if not _is_dominated(t, completed, goal):
            pareto.append(t.to_dict())
    return pareto


def calculate_sweep_analysis(sweep: SweepConfig) -> dict[str, Any]:
    """Perform statistical analysis, parameter importance, and Pareto frontier evaluation."""
    completed = [t for t in sweep.trials if t.status == "completed" and t.objective_value is not None]
    if not completed:
        return {
            "sweep_id": sweep.sweep_id,
            "status": sweep.status,
            "total_trials": len(sweep.trials),
            "completed_trials": 0,
            "best_trial": None,
            "parameter_importance": {},
            "correlations": {},
            "pareto_frontier": [],
        }

    reverse_sort = sweep.goal == "maximize"
    sorted_trials = sorted(completed, key=lambda t: t.objective_value or 0.0, reverse=reverse_sort)
    best_trial = sorted_trials[0]

    importance, correlations = _compute_parameter_sensitivities(completed, sweep.parameters)
    pareto = _compute_pareto_frontier(completed, sweep.goal)

    return {
        "sweep_id": sweep.sweep_id,
        "status": sweep.status,
        "total_trials": len(sweep.trials),
        "completed_trials": len(completed),
        "best_trial": best_trial.to_dict(),
        "best_parameters": best_trial.parameters,
        "best_metric_value": best_trial.objective_value,
        "parameter_importance": importance,
        "correlations": correlations,
        "pareto_frontier": pareto,
    }


def generate_sweep_markdown_report(sweep: SweepConfig) -> str:
    """Export comprehensive sweep findings as a formatted markdown report."""
    analysis = calculate_sweep_analysis(sweep)
    lines = [
        f"# Hyperparameter Optimization Report: {sweep.name}",
        f"- **Sweep ID**: `{sweep.sweep_id}`",
        f"- **Search Method**: `{sweep.method.upper()}`",
        f"- **Objective**: `{sweep.objective_metric}` ({sweep.goal})",
        f"- **Trials Completed**: {analysis['completed_trials']}/{len(sweep.trials)} (Max: {sweep.max_trials})",
        f"- **Status**: `{sweep.status.upper()}`",
        "",
    ]

    if analysis.get("best_trial"):
        bt = analysis["best_trial"]
        lines.extend([
            "### 🏆 Optimal Configuration",
            f"- **Trial ID**: `{bt['trial_id']}`",
            f"- **Best {sweep.objective_metric}**: `{analysis['best_metric_value']}`",
            "- **Parameters**:",
        ])
        for k, v in bt["parameters"].items():
            lines.append(f"  - `{k}`: `{v}`")
        lines.append("")

    if analysis.get("parameter_importance"):
        lines.extend([
            "### 📊 Parameter Sensitivity & Importance",
            "| Hyperparameter | Importance | Correlation |",
            "| :--- | :--- | :--- |",
        ])
        for p, imp in analysis["parameter_importance"].items():
            corr = analysis["correlations"].get(p, 0.0)
            lines.append(f"| `{p}` | {imp * 100:.1f}% | {corr:+.3f} |")
        lines.append("")

    lines.extend([
        "### 🧪 Trial History",
        f"| Trial | Status | {sweep.objective_metric} | Parameters | Runtime |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ])
    for t in sweep.trials:
        param_str = ", ".join(f"{k}={v}" for k, v in list(t.parameters.items())[:3])
        val_str = f"{t.objective_value:.4f}" if t.objective_value is not None else "-"
        lines.append(f"| `{t.trial_id}` | `{t.status}` | {val_str} | {param_str} | {t.duration_seconds:.1f}s |")

    return "\n".join(lines)
