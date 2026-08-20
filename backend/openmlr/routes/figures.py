"""REST API routes for Publication Figure Studio and LaTeX Diagram Generation."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from ..services.figure_generator import FigureGeneratorService
from ..services.figure_types import (
    GenerateFigureRequest,
    MultiPanelLayoutRequest,
)

router = APIRouter(prefix="/api/figures", tags=["figures"])
logger = logging.getLogger("openmlr.routes.figures")

PROJECT_ID_DESC = "Project ID"


@router.get("")
async def list_figures(
    project_id: str = Query("default", description=PROJECT_ID_DESC),
) -> dict[str, Any]:
    """List all figure artifacts for a project."""
    figures = FigureGeneratorService.list_figures(project_id)
    return {
        "figures": [f.to_dict() for f in figures],
        "total_count": len(figures),
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def generate_figure(
    request: GenerateFigureRequest,
    project_id: str = Query("default", description=PROJECT_ID_DESC),
) -> dict[str, Any]:
    """Generate a new publication figure artifact."""
    artifact = FigureGeneratorService.generate_figure(project_id, request)
    return {
        "figure": artifact.to_dict(),
        "message": f"Figure '{artifact.title}' generated successfully.",
    }


@router.get("/{figure_id}")
async def get_figure(
    figure_id: str,
    project_id: str = Query("default", description=PROJECT_ID_DESC),
) -> dict[str, Any]:
    """Get details of a single figure artifact."""
    artifact = FigureGeneratorService.get_figure(project_id, figure_id)
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Figure '{figure_id}' not found.",
        )
    return {"figure": artifact.to_dict()}


@router.delete("/{figure_id}")
async def delete_figure(
    figure_id: str,
    project_id: str = Query("default", description=PROJECT_ID_DESC),
) -> dict[str, Any]:
    """Delete a figure artifact."""
    success = FigureGeneratorService.delete_figure(project_id, figure_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Figure '{figure_id}' not found.",
        )
    return {
        "success": True,
        "message": f"Figure '{figure_id}' deleted successfully.",
    }


@router.post("/multi-panel")
async def create_multipanel_layout(
    request: MultiPanelLayoutRequest,
    project_id: str = Query("default", description=PROJECT_ID_DESC),
) -> dict[str, Any]:
    """Combine multiple figures into a multi-panel LaTeX subfigure layout."""
    result = FigureGeneratorService.create_multipanel_layout(project_id, request)
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"],
        )
    return result
