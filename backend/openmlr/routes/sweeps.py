"""Hyperparameter Sweep and HPO REST API routes.

Provides endpoints for creating sweeps, suggesting trial parameters (Grid, Random, Bayesian, Hyperband),
early-stopping checks, recording trial outcomes, parameter sensitivity analysis, and exporting reports.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..db.models import User
from ..dependencies import get_current_user_optional
from ..services.sweep_engine import SweepEngine
from .projects import WORKSPACES_ROOT

router = APIRouter(tags=["sweeps"])
logger = logging.getLogger(__name__)

_global_engine = SweepEngine()


def _get_engine(project_uuid: str | None = None) -> SweepEngine:
    """Get the active SweepEngine with project workspace isolation."""
    if project_uuid:
        base_dir = WORKSPACES_ROOT / project_uuid / ".project-meta" / "sweeps"
        return SweepEngine(base_dir=base_dir)
    return _global_engine


class CreateSweepRequest(BaseModel):
    """Payload for creating a new hyperparameter sweep."""

    name: str = Field(..., min_length=1, max_length=255, description="Name of the sweep")
    description: str = Field(default="", description="Description or research objective")
    method: str = Field(default="random", description="Search algorithm: grid, random, bayesian, hyperband")
    objective_metric: str = Field(default="val_loss", description="Target metric name")
    goal: str = Field(default="minimize", description="Optimization goal: minimize or maximize")
    parameters: dict[str, Any] = Field(..., description="Parameter space search specifications")
    max_trials: int = Field(default=10, ge=1, le=500, description="Max trials to sample")
    early_stopping: dict[str, Any] = Field(default_factory=dict, description="Early stopping / pruning configuration")
    project_uuid: str | None = Field(default=None, description="Associated project UUID")


class RecordTrialRequest(BaseModel):
    """Payload for logging trial evaluation results."""

    metrics: dict[str, Any] = Field(..., description="Evaluation metrics dictionary")
    status: str = Field(default="completed", description="Status: completed, failed, pruned")
    step_history: list[dict[str, Any]] = Field(default_factory=list, description="Per-step metric trajectories")
    error_message: str | None = Field(default=None, description="Optional error message")


class PruneCheckRequest(BaseModel):
    """Payload for early-stopping evaluate check."""

    current_step: int = Field(..., ge=1, description="Current training step or epoch")
    current_metric_val: float = Field(..., description="Current value of the objective metric")


@router.post("/api/sweeps", status_code=status.HTTP_201_CREATED)
@router.post("/api/projects/{project_uuid}/sweeps", status_code=status.HTTP_201_CREATED)
async def create_sweep(
    payload: CreateSweepRequest,
    project_uuid: str | None = None,
    current_user: User | None = Depends(get_current_user_optional),
):
    """Create and initialize a new hyperparameter sweep."""
    proj = project_uuid or payload.project_uuid or "default"
    engine = _get_engine(proj)

    try:
        sweep = engine.create_sweep(
            project_id=proj,
            name=payload.name,
            method=payload.method,
            objective_metric=payload.objective_metric,
            goal=payload.goal,
            parameters=payload.parameters,
            max_trials=payload.max_trials,
            description=payload.description,
            early_stopping=payload.early_stopping,
        )
        return {"sweep": sweep.to_dict()}
    except Exception as e:
        logger.exception("Failed to create sweep: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create sweep: {e}",
        )


@router.get("/api/sweeps")
@router.get("/api/projects/{project_uuid}/sweeps")
async def list_sweeps(
    project_uuid: str | None = None,
    project_id: str | None = Query(default=None),
    current_user: User | None = Depends(get_current_user_optional),
):
    """List all hyperparameter sweeps in a project."""
    proj = project_uuid or project_id or "default"
    engine = _get_engine(proj)
    sweeps = engine.list_sweeps(proj)
    return {
        "project_id": proj,
        "total": len(sweeps),
        "sweeps": [s.to_dict() for s in sweeps],
    }


@router.get("/api/sweeps/{sweep_id}")
@router.get("/api/projects/{project_uuid}/sweeps/{sweep_id}")
async def get_sweep_details(
    sweep_id: str,
    project_uuid: str | None = None,
    project_id: str | None = Query(default=None),
    current_user: User | None = Depends(get_current_user_optional),
):
    """Get full sweep configuration, trial list, and current status."""
    proj = project_uuid or project_id or "default"
    engine = _get_engine(proj)
    sweep = engine.get_sweep(proj, sweep_id)
    if not sweep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sweep '{sweep_id}' not found in project '{proj}'",
        )
    return {"sweep": sweep.to_dict()}


@router.post("/api/sweeps/{sweep_id}/suggest")
@router.post("/api/projects/{project_uuid}/sweeps/{sweep_id}/suggest")
async def suggest_next_trial(
    sweep_id: str,
    project_uuid: str | None = None,
    project_id: str | None = Query(default=None),
    current_user: User | None = Depends(get_current_user_optional),
):
    """Generate the next parameter candidate proposal for the sweep."""
    proj = project_uuid or project_id or "default"
    engine = _get_engine(proj)
    try:
        trial = engine.suggest_trial(proj, sweep_id)
        if not trial:
            return {"trial": None, "message": "Sweep max trials reached or completed"}
        return {"trial": trial.to_dict()}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.exception("Failed to suggest trial: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/api/sweeps/{sweep_id}/trials/{trial_id}/record")
@router.post("/api/projects/{project_uuid}/sweeps/{sweep_id}/trials/{trial_id}/record")
async def record_trial_outcome(
    sweep_id: str,
    trial_id: str,
    payload: RecordTrialRequest,
    project_uuid: str | None = None,
    project_id: str | None = Query(default=None),
    current_user: User | None = Depends(get_current_user_optional),
):
    """Record metrics, completion status, or failure for a trial."""
    proj = project_uuid or project_id or "default"
    engine = _get_engine(proj)
    try:
        trial = engine.record_trial_result(
            project_id=proj,
            sweep_id=sweep_id,
            trial_id=trial_id,
            metrics=payload.metrics,
            status=payload.status,
            step_history=payload.step_history,
            error_message=payload.error_message,
        )
        return {"trial": trial.to_dict()}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.exception("Failed to record trial: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/api/sweeps/{sweep_id}/trials/{trial_id}/prune-check")
@router.post("/api/projects/{project_uuid}/sweeps/{sweep_id}/trials/{trial_id}/prune-check")
async def check_trial_pruning(
    sweep_id: str,
    trial_id: str,
    payload: PruneCheckRequest,
    project_uuid: str | None = None,
    project_id: str | None = Query(default=None),
    current_user: User | None = Depends(get_current_user_optional),
):
    """Evaluate whether the trial should be early stopped."""
    proj = project_uuid or project_id or "default"
    engine = _get_engine(proj)
    should_prune = engine.should_prune_trial(
        project_id=proj,
        sweep_id=sweep_id,
        trial_id=trial_id,
        current_step=payload.current_step,
        current_metric_val=payload.current_metric_val,
    )
    return {"trial_id": trial_id, "should_prune": should_prune}


@router.get("/api/sweeps/{sweep_id}/analysis")
@router.get("/api/projects/{project_uuid}/sweeps/{sweep_id}/analysis")
async def get_sweep_analysis(
    sweep_id: str,
    project_uuid: str | None = None,
    project_id: str | None = Query(default=None),
    current_user: User | None = Depends(get_current_user_optional),
):
    """Calculate parameter sensitivities, correlation matrix, optimal trial, and Pareto frontier."""
    proj = project_uuid or project_id or "default"
    engine = _get_engine(proj)
    try:
        analysis = engine.analyze_sweep(proj, sweep_id)
        return {"analysis": analysis}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.exception("Failed to analyze sweep: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/api/sweeps/{sweep_id}/export")
@router.post("/api/projects/{project_uuid}/sweeps/{sweep_id}/export")
async def export_sweep_report(
    sweep_id: str,
    project_uuid: str | None = None,
    project_id: str | None = Query(default=None),
    current_user: User | None = Depends(get_current_user_optional),
):
    """Export markdown report for research papers and ablation sections."""
    proj = project_uuid or project_id or "default"
    engine = _get_engine(proj)
    report = engine.export_sweep_markdown(proj, sweep_id)
    return {"report": report}


@router.delete("/api/sweeps/{sweep_id}")
@router.delete("/api/projects/{project_uuid}/sweeps/{sweep_id}")
async def delete_sweep(
    sweep_id: str,
    project_uuid: str | None = None,
    project_id: str | None = Query(default=None),
    current_user: User | None = Depends(get_current_user_optional),
):
    """Delete a sweep and all trial records."""
    proj = project_uuid or project_id or "default"
    engine = _get_engine(proj)
    deleted = engine.delete_sweep(proj, sweep_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sweep '{sweep_id}' not found",
        )
    return {"deleted": True, "sweep_id": sweep_id}
