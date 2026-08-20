"""Machine Learning Experiments and Run Tracking API routes.

Provides endpoints for creating, monitoring, updating, and comparing ML experiment runs,
metric trajectories (train/val loss, throughput, GPU stats), checkpoints, and terminal logs.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from ..db.models import User
from ..dependencies import get_current_user_optional
from ..services.experiment_tracker import ExperimentTracker
from .projects import WORKSPACES_ROOT

router = APIRouter(tags=["experiments"])
logger = logging.getLogger(__name__)

# Fallback in-memory tracker
_global_tracker = ExperimentTracker()


def _get_tracker(request: Request, project_uuid: str | None = None) -> ExperimentTracker:
    """Get the active ExperimentTracker, with workspace storage if available."""
    if hasattr(request.app.state, "experiment_tracker") and request.app.state.experiment_tracker:
        return request.app.state.experiment_tracker

    if project_uuid:
        storage_dir = WORKSPACES_ROOT / project_uuid / ".project-meta" / "experiments"
        event_bus = getattr(request.app.state, "event_bus", None)
        return ExperimentTracker(event_bus=event_bus, storage_dir=storage_dir)

    return _global_tracker


class CreateRunRequest(BaseModel):
    """Payload for initiating a new experiment run."""

    name: str = Field(..., min_length=1, max_length=255, description="Descriptive name of the run")
    description: str = Field(default="", description="Hypothesis or goal of this experiment run")
    hyperparameters: dict[str, Any] = Field(default_factory=dict, description="Model and training hyperparameters")
    compute_target: str = Field(default="Local GPU", description="Target hardware (e.g. Local H100, Modal A100)")
    tags: list[str] = Field(default_factory=list, description="Categorization tags")
    total_steps: int = Field(default=100, ge=1, description="Expected total optimization steps")
    total_epochs: int = Field(default=1, ge=1, description="Expected total epochs")
    project_uuid: str | None = Field(default=None, description="Associated project UUID")


class UpdateRunStatusRequest(BaseModel):
    """Payload for updating experiment run status."""

    status: str = Field(..., description="New status: running, paused, completed, failed, idle")
    reason: str | None = Field(default=None, description="Optional explanation or failure error message")


class LogMetricsRequest(BaseModel):
    """Payload for logging metric points during training."""

    step: int = Field(..., ge=0, description="Global training step")
    epoch: int = Field(default=1, ge=1, description="Current epoch")
    metrics: dict[str, float] = Field(..., description="Key-value metrics (e.g. train_loss, val_loss, lr)")
    timestamp: float | None = Field(default=None, description="Optional epoch millisecond timestamp")


class LogEntriesRequest(BaseModel):
    """Payload for appending stdout/stderr log lines."""

    lines: list[str] = Field(..., description="Array of log lines")


class RegisterCheckpointRequest(BaseModel):
    """Payload for saving an experiment checkpoint."""

    name: str = Field(..., description="Checkpoint name (e.g. step_500_best.pt)")
    step: int = Field(..., ge=0, description="Step at which checkpoint was saved")
    epoch: int = Field(default=1, ge=1, description="Epoch at which checkpoint was saved")
    path: str = Field(default="", description="Relative or absolute file path to checkpoint")
    file_size_mb: float = Field(default=0.0, ge=0, description="Checkpoint size in megabytes")
    metrics: dict[str, float] = Field(default_factory=dict, description="Metric snapshot at checkpoint")
    download_url: str = Field(default="", description="Direct download URL if uploaded to object store")


@router.get("/api/experiments/runs")
async def list_experiment_runs(
    request: Request,
    project_uuid: str | None = Query(None, description="Filter by project UUID"),
    status: str | None = Query(None, description="Filter by status (running, completed, failed, paused, all)"),
    search: str | None = Query(None, description="Search term across name, description, tags"),
    limit: int = Query(50, ge=1, le=200, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
    user: User | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    """List all tracked experiment runs with summary metrics and pagination."""
    tracker = _get_tracker(request, project_uuid)
    runs, total = tracker.list_runs(
        project_uuid=project_uuid,
        status=status,
        search=search,
        limit=limit,
        offset=offset,
    )
    return {
        "runs": [r.to_dict() for r in runs],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/api/experiments/runs", status_code=status.HTTP_201_CREATED)
async def create_experiment_run(
    req: CreateRunRequest,
    request: Request,
    user: User | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    """Start and register a new experiment run."""
    tracker = _get_tracker(request, req.project_uuid)
    run = tracker.create_run(
        name=req.name,
        description=req.description,
        hyperparameters=req.hyperparameters,
        compute_target=req.compute_target,
        tags=req.tags,
        total_steps=req.total_steps,
        total_epochs=req.total_epochs,
        project_uuid=req.project_uuid,
    )

    event_bus = getattr(request.app.state, "event_bus", None)
    if event_bus:
        try:
            await event_bus.broadcast({
                "type": "experiment_run_created",
                "run_id": run.id,
                "name": run.name,
                "project_uuid": req.project_uuid,
            })
        except Exception as ex:
            logger.warning("Failed to broadcast experiment run created event: %s", ex)

    return {"status": "created", "run": run.to_dict()}


@router.get("/api/experiments/runs/{run_id}")
async def get_experiment_run(
    run_id: str,
    request: Request,
    project_uuid: str | None = Query(None),
    user: User | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    """Retrieve detailed metrics, parameters, checkpoints, and logs for a specific run."""
    tracker = _get_tracker(request, project_uuid)
    run = tracker.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Experiment run '{run_id}' not found")
    return {"run": run.to_dict()}


@router.post("/api/experiments/runs/{run_id}/metrics")
async def log_run_metrics(
    run_id: str,
    req: LogMetricsRequest,
    request: Request,
    project_uuid: str | None = Query(None),
    user: User | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    """Log one or more training/evaluation metric points for a run."""
    tracker = _get_tracker(request, project_uuid)
    try:
        run = tracker.log_metrics(
            run_id=run_id,
            step=req.step,
            epoch=req.epoch,
            metrics=req.metrics,
            timestamp=req.timestamp,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Experiment run '{run_id}' not found")

    event_bus = getattr(request.app.state, "event_bus", None)
    if event_bus:
        try:
            await event_bus.broadcast({
                "type": "experiment_metric_logged",
                "run_id": run_id,
                "step": req.step,
                "epoch": req.epoch,
                "metrics": req.metrics,
            })
        except Exception as ex:
            logger.warning("Failed to broadcast metric event: %s", ex)

    return {
        "status": "success",
        "run_id": run.id,
        "current_step": run.current_step,
        "best_val_loss": run.best_val_loss,
    }


@router.post("/api/experiments/runs/{run_id}/status")
async def update_run_status(
    run_id: str,
    req: UpdateRunStatusRequest,
    request: Request,
    project_uuid: str | None = Query(None),
    user: User | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    """Update execution status of an experiment run (running, paused, completed, failed)."""
    tracker = _get_tracker(request, project_uuid)
    try:
        run = tracker.update_status(run_id=run_id, status=req.status, reason=req.reason)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Experiment run '{run_id}' not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    event_bus = getattr(request.app.state, "event_bus", None)
    if event_bus:
        try:
            await event_bus.broadcast({
                "type": "experiment_status_changed",
                "run_id": run_id,
                "status": req.status,
                "reason": req.reason,
            })
        except Exception as ex:
            logger.warning("Failed to broadcast status event: %s", ex)

    return {"status": "success", "run": run.to_dict()}


@router.post("/api/experiments/runs/{run_id}/logs")
async def append_run_logs(
    run_id: str,
    req: LogEntriesRequest,
    request: Request,
    project_uuid: str | None = Query(None),
    user: User | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    """Append stdout/stderr lines to the experiment run log buffer."""
    tracker = _get_tracker(request, project_uuid)
    try:
        logs = tracker.append_logs(run_id=run_id, lines=req.lines)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Experiment run '{run_id}' not found")
    return {"status": "success", "total_lines": len(logs)}


@router.get("/api/experiments/runs/{run_id}/logs")
async def get_run_logs(
    run_id: str,
    request: Request,
    limit: int = Query(200, ge=1, le=2000),
    project_uuid: str | None = Query(None),
    user: User | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    """Retrieve the recent stdout/stderr log buffer for a run."""
    tracker = _get_tracker(request, project_uuid)
    run = tracker.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Experiment run '{run_id}' not found")
    return {"run_id": run_id, "logs": run.logs[-limit:]}


@router.post("/api/experiments/runs/{run_id}/checkpoints")
async def register_run_checkpoint(
    run_id: str,
    req: RegisterCheckpointRequest,
    request: Request,
    project_uuid: str | None = Query(None),
    user: User | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    """Register a trained model checkpoint for an experiment run."""
    tracker = _get_tracker(request, project_uuid)
    try:
        cp = tracker.register_checkpoint(
            run_id=run_id,
            name=req.name,
            step=req.step,
            epoch=req.epoch,
            path=req.path,
            file_size_mb=req.file_size_mb,
            metrics=req.metrics,
            download_url=req.download_url,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Experiment run '{run_id}' not found")
    return {"status": "registered", "checkpoint": cp.to_dict()}


@router.get("/api/experiments/compare")
async def compare_experiment_runs(
    request: Request,
    run_ids: str = Query(..., description="Comma-separated run IDs to compare"),
    project_uuid: str | None = Query(None),
    user: User | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    """Compare metrics trajectories, hyperparameters, and best losses across runs."""
    ids = [rid.strip() for rid in run_ids.split(",") if rid.strip()]
    if not ids:
        raise HTTPException(status_code=400, detail="At least one run_id must be provided")

    tracker = _get_tracker(request, project_uuid)
    comparison = tracker.compare_runs(ids)
    return comparison


@router.delete("/api/experiments/runs/{run_id}")
async def delete_experiment_run(
    run_id: str,
    request: Request,
    project_uuid: str | None = Query(None),
    user: User | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    """Delete an experiment run from storage."""
    tracker = _get_tracker(request, project_uuid)
    deleted = tracker.delete_run(run_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Experiment run '{run_id}' not found")
    return {"status": "deleted", "run_id": run_id}
