"""Sweep data types and configuration models."""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ParameterSpec:
    """Specification of a hyperparameter search space dimension."""

    name: str
    param_type: str  # "categorical", "uniform", "loguniform", "int_uniform", "choice"
    min_val: float | None = None
    max_val: float | None = None
    step: float | None = None
    choices: list[Any] = field(default_factory=list)
    default: Any | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ParameterSpec:
        return cls(
            name=data.get("name", "param"),
            param_type=data.get("param_type", "uniform"),
            min_val=data.get("min_val"),
            max_val=data.get("max_val"),
            step=data.get("step"),
            choices=data.get("choices", []) or [],
            default=data.get("default"),
        )


@dataclass
class EarlyStoppingConfig:
    """Configuration for trial early stopping and pruning (e.g. ASHA / Hyperband)."""

    enabled: bool = False
    min_steps: int = 5
    reduction_factor: float = 3.0
    metric_threshold: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EarlyStoppingConfig:
        return cls(
            enabled=data.get("enabled", False),
            min_steps=int(data.get("min_steps", 5)),
            reduction_factor=float(data.get("reduction_factor", 3.0)),
            metric_threshold=data.get("metric_threshold"),
        )


@dataclass
class Trial:
    """A single hyperparameter trial run."""

    trial_id: str
    sweep_id: str
    trial_number: int
    parameters: dict[str, Any]
    status: str = "pending"  # "pending", "running", "completed", "failed", "pruned"
    metrics: dict[str, Any] = field(default_factory=dict)
    objective_value: float | None = None
    step_history: list[dict[str, Any]] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    error_message: str | None = None
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Trial:
        return cls(
            trial_id=data.get("trial_id", str(uuid.uuid4())[:8]),
            sweep_id=data.get("sweep_id", ""),
            trial_number=int(data.get("trial_number", 1)),
            parameters=data.get("parameters", {}),
            status=data.get("status", "pending"),
            metrics=data.get("metrics", {}),
            objective_value=data.get("objective_value"),
            step_history=data.get("step_history", []),
            started_at=data.get("started_at", time.time()),
            completed_at=data.get("completed_at"),
            error_message=data.get("error_message"),
            duration_seconds=data.get("duration_seconds", 0.0),
        )


@dataclass
class SweepConfig:
    """Complete specification of a hyperparameter sweep."""

    sweep_id: str
    project_id: str
    name: str
    description: str
    method: str  # "grid", "random", "bayesian", "hyperband"
    objective_metric: str
    goal: str  # "minimize", "maximize"
    max_trials: int
    parameters: dict[str, ParameterSpec]
    early_stopping: EarlyStoppingConfig = field(default_factory=EarlyStoppingConfig)
    trials: list[Trial] = field(default_factory=list)
    status: str = "active"  # "active", "completed", "archived"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["parameters"] = {k: v.to_dict() for k, v in self.parameters.items()}
        d["early_stopping"] = self.early_stopping.to_dict()
        d["trials"] = [t.to_dict() for t in self.trials]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SweepConfig:
        raw_params = data.get("parameters", {})
        params = {
            k: ParameterSpec.from_dict(v) if isinstance(v, dict) else v
            for k, v in raw_params.items()
        }
        early_stopping = EarlyStoppingConfig.from_dict(data.get("early_stopping", {}))
        raw_trials = data.get("trials", [])
        trials = [
            Trial.from_dict(t) if isinstance(t, dict) else t
            for t in raw_trials
        ]
        return cls(
            sweep_id=data.get("sweep_id", str(uuid.uuid4())[:8]),
            project_id=data.get("project_id", "default"),
            name=data.get("name", "Sweep"),
            description=data.get("description", ""),
            method=data.get("method", "random"),
            objective_metric=data.get("objective_metric", "val_loss"),
            goal=data.get("goal", "minimize"),
            max_trials=int(data.get("max_trials", 10)),
            parameters=params,
            early_stopping=early_stopping,
            trials=trials,
            status=data.get("status", "active"),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )
