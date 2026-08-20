"""Peer review simulation API routes.

Provides endpoints for evaluating academic submissions, research proposals,
and project manuscripts with multi-agent reviewer committees.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..agent.peer_review import PeerReviewSimulator
from ..agent.review_prompts import (
    CONFERENCE_RUBRICS,
    REVIEWER_PERSONAS,
)
from ..config import AgentConfig
from ..db import operations as ops
from ..db.engine import get_db
from ..db.models import User
from ..dependencies import get_config, get_current_user, get_current_user_optional
from .projects import WORKSPACES_ROOT

router = APIRouter(tags=["review"])
logger = logging.getLogger(__name__)


class ReviewEvaluationRequest(BaseModel):
    """Request payload for arbitrary manuscript or research proposal review."""

    submission_text: str = Field(..., min_length=10, description="Full text, LaTeX, or markdown of the paper/proposal")
    venue: str = Field(default="iclr", description="Target venue: iclr, neurips, icml, cvpr, acl, general")
    title: str = Field(default="", description="Submission title")
    context: dict[str, Any] | None = Field(default=None, description="Optional extra metadata or baseline targets")


class ProjectReviewRequest(BaseModel):
    """Request payload for reviewing an existing OpenMLR project's workspace artifacts."""

    venue: str = Field(default="iclr", description="Target conference venue")
    include_latex: bool = Field(default=True, description="Scan and incorporate LaTeX paper files")
    include_notes: bool = Field(default=True, description="Scan and incorporate research notes and state")


@router.get("/api/review/rubrics")
async def list_review_rubrics() -> dict[str, Any]:
    """List all available conference rubrics, evaluation scales, and reviewer personas."""
    rubrics = {venue.value: rubric for venue, rubric in CONFERENCE_RUBRICS.items()}
    return {
        "rubrics": rubrics,
        "personas": [
            {
                "id": p["id"],
                "name": p["name"],
                "role": p["role"],
                "focus_areas": p["focus_areas"],
            }
            for p in REVIEWER_PERSONAS
        ],
    }


@router.post("/api/review/evaluate")
async def evaluate_submission_endpoint(
    req: ReviewEvaluationRequest,
    config: AgentConfig = Depends(get_config),
    user: User | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    """Simulate a multi-agent peer review committee on any provided text or LaTeX manuscript."""
    simulator = PeerReviewSimulator()
    try:
        result = await simulator.evaluate_submission(
            submission_text=req.submission_text,
            venue=req.venue,
            title=req.title,
            context=req.context,
            config=config,
        )
        report_md = simulator.format_markdown_report(result)
        res_dict = result.to_dict()
        res_dict["markdown_report"] = report_md
        return res_dict
    except Exception as e:
        logger.exception("Error simulating peer review: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Peer review evaluation failed: {str(e)}",
        ) from e


@router.post("/api/projects/{project_id}/review")
async def review_project_workspace(
    project_id: int,
    req: ProjectReviewRequest,
    db: AsyncSession = Depends(get_db),
    config: AgentConfig = Depends(get_config),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Compile project workspace manuscripts and run an autonomous peer review simulation."""
    project = await ops.get_project_by_id(db, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    ws_dir = WORKSPACES_ROOT / str(user.id) / project.slug
    if not ws_dir.exists():
        raise HTTPException(status_code=400, detail="Project workspace does not exist")

    # Aggregate submission text from LaTeX or Markdown drafts
    content_parts: list[str] = []

    if req.include_latex:
        for candidate_name in ["main.tex", "paper.tex", "manuscript.tex"]:
            tex_file = ws_dir / candidate_name
            if tex_file.exists():
                try:
                    content_parts.append(f"### File: {candidate_name}\n" + tex_file.read_text(encoding="utf-8")[:15000])
                except Exception as ex:
                    logger.warning("Failed to read %s: %s", tex_file, ex)

    if req.include_notes:
        notes_dir = ws_dir / "notes"
        if notes_dir.exists() and notes_dir.is_dir():
            for note_file in list(notes_dir.glob("*.md"))[:5]:
                try:
                    content_parts.append(f"### Research Note: {note_file.name}\n" + note_file.read_text(encoding="utf-8")[:5000])
                except Exception as ex:
                    logger.warning("Failed to read note %s: %s", note_file, ex)

    # Fallback to research state or project description if no files found
    state_file = ws_dir / ".research_state.json"
    research_state = {}
    if state_file.exists():
        try:
            research_state = json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    if not content_parts:
        if research_state:
            content_parts.append(f"Research State Plan & Goals:\n{json.dumps(research_state, indent=2)}")
        elif project.description:
            content_parts.append(f"Project Proposal & Description:\n{project.description}")
        else:
            raise HTTPException(
                status_code=400,
                detail="Workspace has no paper drafts (.tex), notes (.md), or active research state to review.",
            )

    combined_text = "\n\n".join(content_parts)
    title = project.name or "OpenMLR Research Project"

    simulator = PeerReviewSimulator()
    result = await simulator.evaluate_submission(
        submission_text=combined_text,
        venue=req.venue,
        title=title,
        context=research_state if research_state else None,
        config=config,
    )

    report_md = simulator.format_markdown_report(result)
    res_dict = result.to_dict()
    res_dict["markdown_report"] = report_md

    # Cache report into workspace
    try:
        cache_file = ws_dir / ".openmlr_review.json"
        cache_file.write_text(json.dumps(res_dict, indent=2), encoding="utf-8")
    except Exception as ex:
        logger.warning("Failed to cache review to %s: %s", ws_dir, ex)

    return res_dict


@router.get("/api/projects/{project_id}/review/latest")
async def get_latest_project_review(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve the most recent peer review result cached for a project."""
    project = await ops.get_project_by_id(db, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    ws_dir = WORKSPACES_ROOT / str(user.id) / project.slug
    cache_file = ws_dir / ".openmlr_review.json"
    if not cache_file.exists():
        raise HTTPException(status_code=404, detail="No peer review cached for this project")

    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to load cached review") from e
