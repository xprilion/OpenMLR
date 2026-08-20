"""REST API routes for Reproducibility Studio and Artifact Verification."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from ..services.reproducibility_auditor import ReproducibilityAuditorService
from ..services.reproducibility_types import (
    AuditCodebaseRequest,
    FixDeterminismRequest,
    GenerateAppendixRequest,
    GenerateDockerfileRequest,
    ReproducibilityAuditReport,
)

logger = logging.getLogger("openmlr.routes.reproducibility")
router = APIRouter(prefix="/api/reproducibility", tags=["reproducibility"])


@router.get("/reports", response_model=list[ReproducibilityAuditReport])
async def list_reports(
    project_id: str | None = Query(None, description="Filter reports by project ID"),
) -> Any:
    """List all reproducibility audit reports for a project."""
    return ReproducibilityAuditorService.list_reports(project_id)


@router.get("/reports/{report_id}", response_model=ReproducibilityAuditReport)
async def get_report(
    report_id: str,
    project_id: str | None = Query(None, description="Project ID"),
) -> Any:
    """Retrieve a specific reproducibility audit report."""
    report = ReproducibilityAuditorService.get_report(report_id, project_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report '{report_id}' not found.",
        )
    return report


@router.delete("/reports/{report_id}")
async def delete_report(
    report_id: str,
    project_id: str | None = Query(None, description="Project ID"),
) -> dict[str, str]:
    """Delete a reproducibility audit report."""
    success = ReproducibilityAuditorService.delete_report(report_id, project_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report '{report_id}' not found.",
        )
    return {"status": "deleted", "report_id": report_id}


@router.post("/audit", response_model=ReproducibilityAuditReport)
async def audit_codebase(
    request: AuditCodebaseRequest,
    project_id: str | None = Query(None, description="Project ID"),
) -> Any:
    """Run an automated reproducibility audit on codebase or provided snippets."""
    try:
        return ReproducibilityAuditorService.audit_codebase(request, project_id)
    except Exception as e:
        logger.exception("Failed to run reproducibility audit: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audit failed: {e}",
        ) from e


@router.post("/dockerfile")
async def generate_dockerfile(
    request: GenerateDockerfileRequest,
) -> dict[str, str]:
    """Generate a reproducible Dockerfile."""
    dockerfile = ReproducibilityAuditorService.generate_dockerfile(request)
    return {"dockerfile": dockerfile}


@router.post("/appendix")
async def generate_appendix(
    request: GenerateAppendixRequest,
    project_id: str | None = Query(None, description="Project ID"),
) -> dict[str, str]:
    """Generate a LaTeX Reproducibility Statement appendix."""
    report = None
    if request.report_id:
        report = ReproducibilityAuditorService.get_report(request.report_id, project_id)
    appendix = ReproducibilityAuditorService.generate_latex_appendix(request, report)
    return {"latex_appendix": appendix}


@router.post("/fix-determinism")
async def fix_determinism(
    request: FixDeterminismRequest,
) -> dict[str, str]:
    """Generate boilerplate determinism code."""
    snippet = ReproducibilityAuditorService.generate_determinism_snippet(
        framework=request.framework,
        seed=request.seed,
        strict_mode=request.strict_mode,
    )
    return {"determinism_snippet": snippet}
