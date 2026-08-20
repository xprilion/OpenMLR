"""Sweep Engine — Agent-native hyperparameter optimization, search spaces, and trial evaluation."""

from __future__ import annotations

import json
import logging
import math
import secrets
import time
import uuid
from pathlib import Path
from typing import Any

from .sweep_analysis import calculate_sweep_analysis, generate_sweep_markdown_report
from .sweep_types import EarlyStoppingConfig, ParameterSpec, SweepConfig, Trial

log = logging.getLogger(__name__)

# Re-export types for backward compatibility
__all__ = [
    "EarlyStoppingConfig",
    "ParameterSpec",
    "SweepConfig",
    "SweepEngine",
    "Trial",
]


def _safe_uniform(min_v: float, max_v: float) -> float:
    """Generate uniform float in range [min_v, max_v] using secure random bits."""
    scale = secrets.randbits(32) / (1 << 32)
    return min_v + scale * (max_v - min_v)


def _safe_choice(choices: list[Any], default: Any) -> Any:
    """Select a random choice safely."""
    if not choices:
        return default
    idx = secrets.randbelow(len(choices))
    return choices[idx]


def _score_param_match(spec: ParameterSpec, val1: Any, val2: Any) -> float:
    """Score similarity between two parameter values."""
    if val1 is None or val2 is None:
        return 0.0
    if spec.param_type in ("categorical", "choice"):
        return 1.0 if val1 == val2 else 0.0
    norm_range = (spec.max_val or 1.0) - (spec.min_val or 0.0)
    if norm_range <= 0:
        return 1.0
    dist = abs(float(val1) - float(val2)) / norm_range
    return max(0.0, 1.0 - dist)


def _score_candidate(candidate: dict[str, Any], good_trials: list[Trial], parameters: dict[str, ParameterSpec]) -> float:
    """Score candidate similarity against top-performing historical trials."""
    sim_score = 0.0
    total_count = max(1, len(parameters))
    for good_t in good_trials:
        match_count = sum(
            _score_param_match(spec, candidate.get(p_name), good_t.parameters.get(p_name))
            for p_name, spec in parameters.items()
        )
        sim_score += match_count / total_count
    return sim_score


class SweepEngine:
    """Service to create sweeps, suggest next trials, prune underperforming runs, and evaluate results."""

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or Path(".openmlr/sweeps")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _sweep_file(self, project_id: str, sweep_id: str) -> Path:
        p_dir = self.base_dir / project_id
        p_dir.mkdir(parents=True, exist_ok=True)
        return p_dir / f"{sweep_id}.json"

    def save_sweep(self, sweep: SweepConfig) -> None:
        """Persist sweep state to disk."""
        sweep.updated_at = time.time()
        file_path = self._sweep_file(sweep.project_id, sweep.sweep_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(sweep.to_dict(), f, indent=2)

    def get_sweep(self, project_id: str, sweep_id: str) -> SweepConfig | None:
        """Load sweep by ID from disk."""
        file_path = self._sweep_file(project_id, sweep_id)
        if not file_path.exists():
            return None
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            return SweepConfig.from_dict(data)
        except Exception:
            log.exception("Failed to load sweep %s/%s", project_id, sweep_id)
            return None

    def list_sweeps(self, project_id: str) -> list[SweepConfig]:
        """List all sweeps for a given project."""
        p_dir = self.base_dir / project_id
        if not p_dir.exists():
            return []
        sweeps = []
        for p in p_dir.glob("*.json"):
            try:
                with open(p, encoding="utf-8") as f:
                    data = json.load(f)
                sweeps.append(SweepConfig.from_dict(data))
            except Exception as e:
                log.warning("Skipping corrupted sweep file %s: %s", p, e)
        sweeps.sort(key=lambda s: s.created_at, reverse=True)
        return sweeps

    def delete_sweep(self, project_id: str, sweep_id: str) -> bool:
        """Delete a sweep file."""
        file_path = self._sweep_file(project_id, sweep_id)
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def create_sweep(
        self,
        project_id: str,
        name: str,
        method: str,
        objective_metric: str,
        goal: str,
        parameters: dict[str, Any],
        max_trials: int = 10,
        description: str = "",
        early_stopping: EarlyStoppingConfig | dict[str, Any] | None = None,
    ) -> SweepConfig:
        """Create and initialize a new hyperparameter sweep."""
        sweep_id = f"swp_{str(uuid.uuid4())[:8]}"
        param_specs: dict[str, ParameterSpec] = {}
        for k, v in parameters.items():
            if isinstance(v, ParameterSpec):
                param_specs[k] = v
            else:
                v_dict = dict(v)
                v_dict["name"] = k
                param_specs[k] = ParameterSpec.from_dict(v_dict)

        es_conf = (
            early_stopping
            if isinstance(early_stopping, EarlyStoppingConfig)
            else EarlyStoppingConfig.from_dict(early_stopping or {})
        )

        sweep = SweepConfig(
            sweep_id=sweep_id,
            project_id=project_id,
            name=name,
            description=description,
            method=method.lower(),
            objective_metric=objective_metric,
            goal=goal.lower(),
            max_trials=max_trials,
            parameters=param_specs,
            early_stopping=es_conf,
            trials=[],
            status="active",
        )
        self.save_sweep(sweep)
        return sweep

    def suggest_trial(self, project_id: str, sweep_id: str) -> Trial | None:
        """Generate the next parameter proposal for the sweep."""
        sweep = self.get_sweep(project_id, sweep_id)
        if not sweep:
            raise ValueError(f"Sweep '{sweep_id}' not found in project '{project_id}'")

        if len(sweep.trials) >= sweep.max_trials:
            sweep.status = "completed"
            self.save_sweep(sweep)
            return None

        trial_num = len(sweep.trials) + 1
        trial_id = f"tr_{sweep_id[-4:]}_{trial_num:03d}"

        if sweep.method == "grid":
            params = self._suggest_grid(sweep, trial_num)
        elif sweep.method in ("bayesian", "bayes"):
            params = self._suggest_bayesian(sweep)
        else:
            params = self._suggest_random(sweep)

        trial = Trial(
            trial_id=trial_id,
            sweep_id=sweep_id,
            trial_number=trial_num,
            parameters=params,
            status="running",
            started_at=time.time(),
        )
        sweep.trials.append(trial)
        self.save_sweep(sweep)
        return trial

    def _sample_single_param(self, spec: ParameterSpec) -> Any:
        """Sample a single parameter randomly within its spec."""
        if spec.param_type in ("categorical", "choice"):
            return _safe_choice(spec.choices, spec.default)
        if spec.param_type == "int_uniform":
            min_v = int(spec.min_val or 0)
            max_v = int(spec.max_val or 10)
            step = max(1, int(spec.step or 1))
            count = max(1, ((max_v - min_v) // step) + 1)
            return min_v + secrets.randbelow(count) * step
        if spec.param_type == "loguniform":
            min_v = max(1e-7, spec.min_val or 1e-4)
            max_v = spec.max_val or 1.0
            log_min, log_max = math.log(min_v), math.log(max_v)
            val = math.exp(_safe_uniform(log_min, log_max))
            return round(val, 6)
        min_v = spec.min_val or 0.0
        max_v = spec.max_val or 1.0
        val = _safe_uniform(min_v, max_v)
        if spec.step:
            val = round(round((val - min_v) / spec.step) * spec.step + min_v, 4)
        else:
            val = round(val, 4)
        return val

    def _suggest_random(self, sweep: SweepConfig) -> dict[str, Any]:
        """Generate a random parameter sample across all dimensions."""
        return {name: self._sample_single_param(spec) for name, spec in sweep.parameters.items()}

    def _suggest_grid(self, sweep: SweepConfig, trial_num: int) -> dict[str, Any]:
        """Generate parameter combination using deterministic Cartesian product indexing."""
        grids: list[tuple[str, list[Any]]] = []
        for name, spec in sweep.parameters.items():
            if spec.choices:
                values = list(spec.choices)
            elif spec.param_type == "int_uniform":
                min_v = int(spec.min_val or 0)
                max_v = int(spec.max_val or 10)
                step = int(spec.step or 1)
                values = list(range(min_v, max_v + 1, step))
            else:
                min_v = spec.min_val or 0.0
                max_v = spec.max_val or 1.0
                step = spec.step or ((max_v - min_v) / 4)
                steps = max(2, int(round((max_v - min_v) / step)) + 1)
                values = [round(min_v + i * step, 4) for i in range(steps)]
            grids.append((name, values))

        idx = trial_num - 1
        params = {}
        for name, values in reversed(grids):
            chosen = values[idx % len(values)]
            params[name] = chosen
            idx //= len(values)
        return params

    def _suggest_bayesian(self, sweep: SweepConfig) -> dict[str, Any]:
        """Generate suggestion using Parzen density estimation & expected improvement surrogate."""
        completed_trials = [
            t for t in sweep.trials if t.status == "completed" and t.objective_value is not None
        ]
        if len(completed_trials) < 3:
            return self._suggest_random(sweep)

        reverse_sort = sweep.goal == "maximize"
        sorted_trials = sorted(
            completed_trials, key=lambda t: t.objective_value or 0.0, reverse=reverse_sort
        )

        split_idx = max(1, len(sorted_trials) // 4)
        good_trials = sorted_trials[:split_idx]

        candidates = [self._suggest_random(sweep) for _ in range(25)]
        best_candidate = candidates[0]
        best_score = -1.0

        for cand in candidates:
            score = _score_candidate(cand, good_trials, sweep.parameters)
            if score > best_score:
                best_score = score
                best_candidate = cand

        return best_candidate

    def record_trial_result(
        self,
        project_id: str,
        sweep_id: str,
        trial_id: str,
        metrics: dict[str, Any],
        status: str = "completed",
        step_history: list[dict[str, Any]] | None = None,
        error_message: str | None = None,
    ) -> Trial:
        """Record the evaluation metrics and completion status of a trial."""
        sweep = self.get_sweep(project_id, sweep_id)
        if not sweep:
            raise ValueError(f"Sweep '{sweep_id}' not found")

        trial = next((t for t in sweep.trials if t.trial_id == trial_id), None)
        if not trial:
            raise ValueError(f"Trial '{trial_id}' not found in sweep '{sweep_id}'")

        trial.metrics = metrics
        trial.status = status
        trial.completed_at = time.time()
        trial.duration_seconds = round(trial.completed_at - trial.started_at, 2)
        if step_history:
            trial.step_history = step_history
        if error_message:
            trial.error_message = error_message

        obj_val = metrics.get(sweep.objective_metric)
        if obj_val is not None:
            try:
                trial.objective_value = float(obj_val)
            except (ValueError, TypeError):
                trial.objective_value = None

        completed_count = len([t for t in sweep.trials if t.status in ("completed", "failed", "pruned")])
        if completed_count >= sweep.max_trials:
            sweep.status = "completed"

        self.save_sweep(sweep)
        return trial

    def should_prune_trial(
        self,
        project_id: str,
        sweep_id: str,
        trial_id: str,
        current_step: int,
        current_metric_val: float,
    ) -> bool:
        """Evaluate whether a running trial should be early-stopped based on ASHA/Hyperband percentiles."""
        sweep = self.get_sweep(project_id, sweep_id)
        if not sweep or not sweep.early_stopping.enabled:
            return False

        es = sweep.early_stopping
        if current_step < es.min_steps:
            return False

        if es.metric_threshold is not None:
            if sweep.goal == "minimize" and current_metric_val > es.metric_threshold:
                return True
            if sweep.goal == "maximize" and current_metric_val < es.metric_threshold:
                return True

        past_metrics = [
            float(entry[sweep.objective_metric])
            for t in sweep.trials
            if t.trial_id != trial_id
            for entry in t.step_history
            if entry.get("step") == current_step and sweep.objective_metric in entry
        ]

        if len(past_metrics) < 2:
            return False

        past_metrics.sort(reverse=(sweep.goal == "maximize"))
        top_k = max(1, int(len(past_metrics) / es.reduction_factor))
        cutoff = past_metrics[top_k - 1]

        if sweep.goal == "minimize":
            return current_metric_val > cutoff * 1.15
        return current_metric_val < cutoff * 0.85

    def analyze_sweep(self, project_id: str, sweep_id: str) -> dict[str, Any]:
        """Calculate parameter sensitivities, correlation matrix, optimal trial, and Pareto frontier."""
        sweep = self.get_sweep(project_id, sweep_id)
        if not sweep:
            raise ValueError(f"Sweep '{sweep_id}' not found")
        return calculate_sweep_analysis(sweep)

    def export_sweep_markdown(self, project_id: str, sweep_id: str) -> str:
        """Export comprehensive sweep findings as a formatted markdown report."""
        sweep = self.get_sweep(project_id, sweep_id)
        if not sweep:
            return f"Sweep {sweep_id} not found."
        return generate_sweep_markdown_report(sweep)
