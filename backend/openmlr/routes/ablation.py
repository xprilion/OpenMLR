"""REST API routes for Ablation Studies, Statistical Significance Testing, and LaTeX Tables."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from ..services.ablation_engine import ablation_engine
from ..services.ablation_types import (
    AnalyzeStudyRequest,
    CreateStudyRequest,
    LatexTableRequest,
    RecordRunsRequest,
)

router = APIRouter(prefix="/api/ablation", tags=["ablation"])
logger = logging.getLogger("openmlr.routes.ablation")

PROJECT_ID_DESC = "Optional project ID filter"


@router.get("", response_model=dict[str, Any])
async def list_studies(
    project_id: str | None = Query(None, description=PROJECT_ID_DESC),
) -> dict[str, Any]:
    """List all ablation studies for a project."""
    studies = ablation_engine.list_studies(project_id)
    return {
        "studies": [s.model_dump() for s in studies],
        "total_count": len(studies),
    }


@router.post("", status_code=status.HTTP_201_CREATED, response_model=dict[str, Any])
async def create_study(
    request: CreateStudyRequest,
) -> dict[str, Any]:
    """Create a new ablation study initialized with a baseline variant."""
    study = ablation_engine.create_study(
        study_id=request.id,
        title=request.title,
        description=request.description,
        project_id=request.project_id,
        primary_metric=request.primary_metric,
        higher_is_better=request.higher_is_better,
        baseline_variant_name=request.baseline_variant_name,
        baseline_description=request.baseline_description,
    )
    return {
        "study": study.model_dump(),
        "message": f"Ablation study '{study.title}' created successfully.",
    }


@router.get("/{study_id}", response_model=dict[str, Any])
async def get_study(
    study_id: str,
) -> dict[str, Any]:
    """Get complete details and statistical comparisons for an ablation study."""
    study = ablation_engine.get_study(study_id)
    if not study:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ablation study '{study_id}' not found.",
        )
    return {"study": study.model_dump()}


@router.delete("/{study_id}", response_model=dict[str, Any])
async def delete_study(
    study_id: str,
) -> dict[str, Any]:
    """Delete an ablation study."""
    success = ablation_engine.delete_study(study_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ablation study '{study_id}' not found.",
        )
    return {
        "success": True,
        "message": f"Ablation study '{study_id}' deleted successfully.",
    }


@router.post("/{study_id}/runs", response_model=dict[str, Any])
async def record_variant_runs(
    study_id: str,
    request: RecordRunsRequest,
) -> dict[str, Any]:
    """Record multi-seed evaluation runs for an ablation variant or baseline."""
    study = ablation_engine.get_study(study_id)
    if not study:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ablation study '{study_id}' not found.",
        )

    variant = ablation_engine.record_variant_runs(
        study_id=study_id,
        variant_name=request.variant_name,
        metrics=request.metrics,
        variant_type=request.variant_type,
        description=request.description,
        removed_components=request.removed_components,
        added_components=request.added_components,
        run_ids=request.run_ids,
    )
    # Refresh updated study
    updated_study = ablation_engine.get_study(study_id)
    return {
        "variant": variant.model_dump(),
        "study": updated_study.model_dump() if updated_study else None,
        "message": f"Recorded runs for variant '{request.variant_name}'.",
    }


@router.post("/{study_id}/analyze", response_model=dict[str, Any])
async def analyze_study(
    study_id: str,
    request: AnalyzeStudyRequest,
) -> dict[str, Any]:
    """Trigger statistical hypothesis testing and multiple testing correction."""
    study = ablation_engine.get_study(study_id)
    if not study:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ablation study '{study_id}' not found.",
        )

    updated_study = ablation_engine.analyze_study(
        study_id=study_id,
        correction_method=request.correction_method,
        test_type=request.test_type,
    )
    return {
        "study": updated_study.model_dump(),
        "message": "Statistical significance analysis completed.",
    }


@router.post("/{study_id}/latex", response_model=dict[str, Any])
async def generate_latex_table(
    study_id: str,
    request: LatexTableRequest,
) -> dict[str, Any]:
    """Generate camera-ready LaTeX booktabs ablation table."""
    study = ablation_engine.get_study(study_id)
    if not study:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ablation study '{study_id}' not found.",
        )

    latex_code = ablation_engine.generate_latex_table(
        study_id=study_id,
        metrics=request.metrics,
        include_significance_stars=request.include_significance_stars,
        caption=request.caption,
        label=request.label,
    )
    return {
        "latex_table": latex_code,
        "study_id": study_id,
    }
