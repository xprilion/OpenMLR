"""Service for tracking machine learning experiment runs, metric curves, hyperparameters, and checkpoints."""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..services.event_bus import EventBus

log = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    step: int
    epoch: int
    timestamp: float
    value: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CheckpointData:
    id: str
    name: str
    step: int
    epoch: int
    timestamp: float
    path: str
    file_size_mb: float
    metrics: dict[str, float]
    download_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExperimentRunData:
    id: str
    name: str
    description: str = ""
    status: str = "running"  # running, completed, failed, paused, idle
    started_at: str = field(default_factory=lambda: datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"))
    ended_at: str | None = None
    duration_seconds: int = 0
    compute_target: str = "Local GPU"
    tags: list[str] = field(default_factory=list)
    hyperparameters: dict[str, Any] = field(default_factory=dict)
    current_step: int = 0
    total_steps: int = 100
    current_epoch: int = 1
    total_epochs: int = 1
    best_val_loss: float | None = None
    metrics: dict[str, list[MetricPoint]] = field(default_factory=lambda: {
        "train_loss": [],
        "val_loss": [],
        "learning_rate": [],
        "gpu_utilization": [],
        "memory_used": [],
        "throughput": [],
    })
    checkpoints: list[CheckpointData] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)
    project_uuid: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_seconds": self.duration_seconds,
            "compute_target": self.compute_target,
            "tags": list(self.tags),
            "hyperparameters": dict(self.hyperparameters),
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "current_epoch": self.current_epoch,
            "total_epochs": self.total_epochs,
            "best_val_loss": self.best_val_loss,
            "metrics": {
                k: [pt.to_dict() for pt in v] for k, v in self.metrics.items()
            },
            "checkpoints": [cp.to_dict() for cp in self.checkpoints],
            "logs": list(self.logs),
            "project_uuid": self.project_uuid,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExperimentRunData:
        metrics_raw = data.get("metrics", {})
        metrics: dict[str, list[MetricPoint]] = {}
        for key, pts in metrics_raw.items():
            metrics[key] = [
                MetricPoint(**pt) if isinstance(pt, dict) else pt for pt in pts
            ]

        checkpoints_raw = data.get("checkpoints", [])
        checkpoints = [
            CheckpointData(**cp) if isinstance(cp, dict) else cp
            for cp in checkpoints_raw
        ]

        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            status=data.get("status", "running"),
            started_at=data.get("started_at", datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")),
            ended_at=data.get("ended_at"),
            duration_seconds=data.get("duration_seconds", 0),
            compute_target=data.get("compute_target", "Local GPU"),
            tags=data.get("tags", []),
            hyperparameters=data.get("hyperparameters", {}),
            current_step=data.get("current_step", 0),
            total_steps=data.get("total_steps", 100),
            current_epoch=data.get("current_epoch", 1),
            total_epochs=data.get("total_epochs", 1),
            best_val_loss=data.get("best_val_loss"),
            metrics=metrics,
            checkpoints=checkpoints,
            logs=data.get("logs", []),
            project_uuid=data.get("project_uuid"),
        )


class ExperimentTracker:
    """In-memory and file-backed experiment registry and metrics aggregator."""

    def __init__(self, event_bus: EventBus | None = None, storage_dir: Path | None = None):
        self.event_bus = event_bus
        self.storage_dir = storage_dir
        self._runs: dict[str, ExperimentRunData] = {}
        if self.storage_dir:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            self._load_stored_runs()

    def _load_stored_runs(self) -> None:
        if not self.storage_dir or not self.storage_dir.exists():
            return
        for file in self.storage_dir.glob("run_*.json"):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                run = ExperimentRunData.from_dict(data)
                self._runs[run.id] = run
            except Exception as e:
                log.warning("Failed to load run from %s: %s", file, e)

    def _persist_run(self, run: ExperimentRunData) -> None:
        if not self.storage_dir:
            return
        file = self.storage_dir / f"run_{run.id}.json"
        try:
            file.write_text(json.dumps(run.to_dict(), indent=2), encoding="utf-8")
        except Exception as e:
            log.warning("Failed to persist run %s: %s", run.id, e)

    async def _emit_event(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.event_bus:
            try:
                await self.event_bus.broadcast({
                    "type": event_type,
                    "channel": "experiments",
                    "data": payload,
                })
            except Exception as e:
                log.warning("Failed to emit experiment event %s: %s", event_type, e)

    def create_run(
        self,
        name: str,
        description: str = "",
        hyperparameters: dict[str, Any] | None = None,
        compute_target: str = "Local GPU",
        tags: list[str] | None = None,
        total_steps: int = 100,
        total_epochs: int = 1,
        project_uuid: str | None = None,
    ) -> ExperimentRunData:
        """Create and register a new experiment run."""
        run_id = f"run-{uuid.uuid4().hex[:8]}"
        run = ExperimentRunData(
            id=run_id,
            name=name,
            description=description,
            status="running",
            compute_target=compute_target,
            tags=tags or [],
            hyperparameters=hyperparameters or {},
            total_steps=total_steps,
            total_epochs=total_epochs,
            project_uuid=project_uuid,
        )
        self._runs[run_id] = run
        self._persist_run(run)
        return run

    def get_run(self, run_id: str) -> ExperimentRunData | None:
        """Retrieve run by ID."""
        return self._runs.get(run_id)

    def list_runs(
        self,
        project_uuid: str | None = None,
        status: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ExperimentRunData], int]:
        """List runs matching filter criteria with pagination."""
        items = list(self._runs.values())

        if project_uuid:
            items = [r for r in items if r.project_uuid == project_uuid]

        if status and status != "all":
            items = [r for r in items if r.status == status]

        if search:
            q = search.lower()
            items = [
                r for r in items
                if q in r.name.lower() or q in r.description.lower() or any(q in t.lower() for t in r.tags)
            ]

        # Sort newest first
        items.sort(key=lambda r: r.started_at, reverse=True)
        total = len(items)
        paginated = items[offset : offset + limit]
        return paginated, total

    def log_metrics(
        self,
        run_id: str,
        step: int,
        epoch: int = 1,
        metrics: dict[str, float] | None = None,
        timestamp: float | None = None,
    ) -> ExperimentRunData:
        """Append metric values to a run and update progress."""
        run = self.get_run(run_id)
        if not run:
            raise KeyError(f"Run '{run_id}' not found")

        ts = timestamp or (time.time() * 1000.0)
        run.current_step = max(run.current_step, step)
        run.current_epoch = max(run.current_epoch, epoch)

        if metrics:
            for metric_name, val in metrics.items():
                if metric_name not in run.metrics:
                    run.metrics[metric_name] = []

                point = MetricPoint(step=step, epoch=epoch, timestamp=ts, value=float(val))
                run.metrics[metric_name].append(point)

                if metric_name in ("val_loss", "eval_loss"):
                    if run.best_val_loss is None or float(val) < run.best_val_loss:
                        run.best_val_loss = float(val)

        self._persist_run(run)
        return run

    def update_status(
        self,
        run_id: str,
        status: str,
        reason: str | None = None,
    ) -> ExperimentRunData:
        """Update run execution status."""
        run = self.get_run(run_id)
        if not run:
            raise KeyError(f"Run '{run_id}' not found")

        valid_statuses = ("running", "completed", "failed", "paused", "idle")
        if status not in valid_statuses:
            raise ValueError(f"Invalid status '{status}'. Must be one of {valid_statuses}")

        run.status = status
        if status in ("completed", "failed"):
            run.ended_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
            if reason:
                run.logs.append(f"[{datetime.now(UTC).strftime('%H:%M:%S')}] Run {status}: {reason}")
        elif status == "running" and not run.started_at:
            run.started_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")

        self._persist_run(run)
        return run

    def append_logs(self, run_id: str, lines: list[str]) -> list[str]:
        """Append log lines to an experiment run."""
        run = self.get_run(run_id)
        if not run:
            raise KeyError(f"Run '{run_id}' not found")

        run.logs.extend(lines)
        # Cap log history to last 2000 lines
        if len(run.logs) > 2000:
            run.logs = run.logs[-2000:]

        self._persist_run(run)
        return run.logs

    def register_checkpoint(
        self,
        run_id: str,
        name: str,
        step: int,
        epoch: int,
        path: str = "",
        file_size_mb: float = 0.0,
        metrics: dict[str, float] | None = None,
        download_url: str = "",
    ) -> CheckpointData:
        """Register a model checkpoint saved during the experiment."""
        run = self.get_run(run_id)
        if not run:
            raise KeyError(f"Run '{run_id}' not found")

        cp_id = f"ckpt-{uuid.uuid4().hex[:8]}"
        cp = CheckpointData(
            id=cp_id,
            name=name,
            step=step,
            epoch=epoch,
            timestamp=time.time() * 1000.0,
            path=path,
            file_size_mb=file_size_mb,
            metrics=metrics or {},
            download_url=download_url,
        )
        run.checkpoints.append(cp)
        self._persist_run(run)
        return cp

    def compare_runs(self, run_ids: list[str]) -> dict[str, Any]:
        """Perform side-by-side comparison across multiple experiment runs."""
        selected_runs: list[ExperimentRunData] = [
            r for rid in run_ids if (r := self.get_run(rid)) is not None
        ]
        if not selected_runs:
            return {"runs": [], "metrics_summary": {}, "hyperparameters_comparison": {}}

        # Collect all unique hyperparameter keys
        all_hp_keys: set[str] = set()
        for r in selected_runs:
            all_hp_keys.update(r.hyperparameters.keys())

        hyperparameter_table: dict[str, dict[str, Any]] = {}
        for k in sorted(all_hp_keys):
            hyperparameter_table[k] = {
                r.id: r.hyperparameters.get(k, None) for r in selected_runs
            }

        # Compare best val losses and final train losses
        metrics_summary: dict[str, dict[str, Any]] = {}
        for r in selected_runs:
            train_losses = [p.value for p in r.metrics.get("train_loss", [])]
            val_losses = [p.value for p in r.metrics.get("val_loss", [])]
            final_train_loss = train_losses[-1] if train_losses else None
            min_train_loss = min(train_losses) if train_losses else None
            min_val_loss = min(val_losses) if val_losses else r.best_val_loss

            metrics_summary[r.id] = {
                "name": r.name,
                "status": r.status,
                "current_step": r.current_step,
                "total_steps": r.total_steps,
                "best_val_loss": min_val_loss,
                "final_train_loss": final_train_loss,
                "min_train_loss": min_train_loss,
                "total_checkpoints": len(r.checkpoints),
            }

        return {
            "runs": [r.to_dict() for r in selected_runs],
            "metrics_summary": metrics_summary,
            "hyperparameters_comparison": hyperparameter_table,
        }

    def delete_run(self, run_id: str) -> bool:
        """Delete an experiment run."""
        if run_id in self._runs:
            del self._runs[run_id]
            if self.storage_dir:
                file = self.storage_dir / f"run_{run_id}.json"
                if file.exists():
                    file.unlink()
            return True
        return False
