"""Autonomous ML Research Workflow API routes.

Provides endpoints for tracking, driving, and interacting with the 5-phase
scientific research state machine (Reconnaissance -> Hypothesis -> Experimentation -> Analysis -> Paper Drafting).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..agent.research_orchestrator import PHASE_GUIDELINES, ResearchOrchestrator
from ..agent.states import MilestoneStatus, ResearchPhase
from ..db import operations as ops
from ..db.engine import get_db
from ..db.models import User
from ..dependencies import get_current_user
from .projects import WORKSPACES_ROOT

router = APIRouter(tags=["research"])
logger = logging.getLogger(__name__)

# Standard default milestones for new research projects
DEFAULT_PHASE_MILESTONES = [
    {
        "phase": ResearchPhase.RECONNAISSANCE,
        "title": "Literature Reconnaissance",
        "description": "Search academic databases (arXiv, OpenAlex, Semantic Scholar) and catalog relevant papers.",
        "criteria": ["Identify at least 5 foundational papers", "Map baseline benchmark metrics"],
    },
    {
        "phase": ResearchPhase.HYPOTHESIS,
        "title": "Hypothesis & Experimental Design",
        "description": "Formulate testable scientific claims, architectural modifications, and ablation matrices.",
        "criteria": ["Define falsifiable hypothesis", "Specify baseline vs proposed comparison criteria"],
    },
    {
        "phase": ResearchPhase.EXPERIMENTATION,
        "title": "Code Implementation & Model Training",
        "description": "Implement model code and execute training/benchmarks on local or cloud compute.",
        "criteria": ["Verify train/eval loss trajectories", "Save experiment checkpoints and logs"],
    },
    {
        "phase": ResearchPhase.ANALYSIS,
        "title": "Empirical Analysis & Self-Correction",
        "description": "Evaluate metrics against baselines, run ablations, and resolve training anomalies.",
        "criteria": ["Generate comparison tables", "Quantify statistical significance"],
    },
    {
        "phase": ResearchPhase.PAPER_DRAFTING,
        "title": "LaTeX Manuscript & Bibliography",
        "description": "Author standard conference paper sections (Abstract, Intro, Method, Results) and compile PDF.",
        "criteria": ["Ensure LaTeX compiles without error", "Validate BibTeX citation keys"],
    },
]


class ResearchStartRequest(BaseModel):
    """Request payload to initiate a research workflow."""

    goal: str = Field(..., min_length=5, description="Scientific objective or research question")
    initial_phase: str = Field(
        default="reconnaissance",
        description="Starting phase: idle, reconnaissance, hypothesis, experimentation, analysis, paper_drafting",
    )
    generate_default_milestones: bool = Field(
        default=True,
        description="Whether to prepopulate standard research milestones for each phase",
    )


class ResearchTransitionRequest(BaseModel):
    """Request payload to advance or switch research phases."""

    next_phase: str = Field(..., description="Target phase name")
    reason: str = Field(..., min_length=3, description="Rationale for phase transition")
    artifacts_produced: list[str] = Field(default_factory=list, description="Artifact keys or identifiers generated")
    milestone_id: str | None = Field(default=None, description="Optional milestone ID triggering this transition")


class MilestoneCreateRequest(BaseModel):
    """Request payload to add a milestone."""

    title: str = Field(..., min_length=2, description="Short title of milestone")
    description: str = Field(default="", description="Detailed milestone criteria or instructions")
    phase: str | None = Field(default=None, description="Target phase; defaults to active phase")
    criteria: list[str] = Field(default_factory=list, description="Verification acceptance criteria")


class MilestoneUpdateRequest(BaseModel):
    """Request payload to update or complete a milestone."""

    status: str | None = Field(default=None, description="pending, in_progress, completed, failed, skipped")
    output_artifacts: list[str] = Field(default_factory=list, description="Artifact identifiers produced by milestone")


class ArtifactCreateRequest(BaseModel):
    """Request payload to register a research artifact."""

    type: str = Field(..., description="Artifact type: paper, hypothesis, experiment, metrics, manuscript_section, bibtex")
    data: Any = Field(..., description="Artifact payload content or metadata dictionary")
    section_name: str | None = Field(default=None, description="Section name if type is manuscript_section")


def _get_project_workspace(user_id: int, project_slug: str):
    ws_dir = WORKSPACES_ROOT / str(user_id) / project_slug
    ws_dir.mkdir(parents=True, exist_ok=True)
    return ws_dir


def _load_orchestrator(user_id: int, project_slug: str) -> ResearchOrchestrator:
    ws_dir = _get_project_workspace(user_id, project_slug)
    orch = ResearchOrchestrator(workspace_path=ws_dir)
    orch.load_state()
    return orch


@router.get("/api/research/phases")
async def list_research_phases() -> dict[str, Any]:
    """List all supported research phases and their metadata."""
    phases = [
        {
            "id": p.value,
            "name": p.value.replace("_", " ").title(),
            "description": PHASE_GUIDELINES.get(p, ""),
        }
        for p in ResearchPhase
    ]
    return {"phases": phases}


@router.get("/api/research/guidelines")
async def get_all_phase_guidelines() -> dict[str, str]:
    """Get prompt guidelines for all research phases."""
    return {p.value: guidelines for p, guidelines in PHASE_GUIDELINES.items()}


@router.get("/api/projects/{project_id}/research/state")
async def get_project_research_state(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve current research state, milestones, artifacts, and transition history for a project."""
    project = await ops.get_project_by_id(db, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    orch = _load_orchestrator(user.id, project.slug)
    return {
        "project_id": project.id,
        "project_name": project.name,
        "state": orch.state.to_dict(),
        "guidelines": orch.get_phase_guidelines(),
        "context_prompt": orch.format_research_context(),
    }


@router.post("/api/projects/{project_id}/research/start")
async def start_project_research(
    project_id: int,
    req: ResearchStartRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Initialize or reset the structured scientific research state machine for a project."""
    project = await ops.get_project_by_id(db, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        init_phase = ResearchPhase(req.initial_phase)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid phase '{req.initial_phase}'. Valid phases: {[p.value for p in ResearchPhase]}",
        )

    orch = _load_orchestrator(user.id, project.slug)
    transition = orch.start_research(goal=req.goal, initial_phase=init_phase)

    if req.generate_default_milestones and not orch.state.milestones:
        for m in DEFAULT_PHASE_MILESTONES:
            orch.add_milestone(
                title=m["title"],
                description=m["description"],
                phase=m["phase"],
                criteria=m["criteria"],
            )

    orch.save_state()

    # Broadcast event if event bus is available
    if hasattr(request.app.state, "event_bus") and request.app.state.event_bus:
        try:
            request.app.state.event_bus.publish(
                "research_started",
                {
                    "project_id": project.id,
                    "goal": req.goal,
                    "current_phase": orch.current_phase.value,
                    "transition": transition.to_dict(),
                },
                project_id=str(project.id),
            )
        except Exception as ex:
            logger.warning("Failed to publish research_started event: %s", ex)

    return {
        "status": "started",
        "project_id": project.id,
        "state": orch.state.to_dict(),
        "transition": transition.to_dict(),
        "guidelines": orch.get_phase_guidelines(),
    }


@router.post("/api/projects/{project_id}/research/transition")
async def transition_project_research_phase(
    project_id: int,
    req: ResearchTransitionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Transition research phase to next stage with recorded rationale and artifacts."""
    project = await ops.get_project_by_id(db, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        next_phase = ResearchPhase(req.next_phase)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid phase '{req.next_phase}'. Valid phases: {[p.value for p in ResearchPhase]}",
        )

    orch = _load_orchestrator(user.id, project.slug)
    transition = orch.transition_to(
        next_phase=next_phase,
        reason=req.reason,
        artifacts_produced=req.artifacts_produced,
        milestone_id=req.milestone_id,
    )
    orch.save_state()

    if hasattr(request.app.state, "event_bus") and request.app.state.event_bus:
        try:
            request.app.state.event_bus.publish(
                "research_phase_transition",
                {
                    "project_id": project.id,
                    "transition": transition.to_dict(),
                    "current_phase": orch.current_phase.value,
                },
                project_id=str(project.id),
            )
        except Exception as ex:
            logger.warning("Failed to publish research_phase_transition event: %s", ex)

    return {
        "status": "transitioned",
        "transition": transition.to_dict(),
        "state": orch.state.to_dict(),
        "guidelines": orch.get_phase_guidelines(),
    }


@router.post("/api/projects/{project_id}/research/milestones")
async def create_research_milestone(
    project_id: int,
    req: MilestoneCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Add a new milestone to the project's research state."""
    project = await ops.get_project_by_id(db, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    target_phase = None
    if req.phase:
        try:
            target_phase = ResearchPhase(req.phase)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid phase '{req.phase}'")

    orch = _load_orchestrator(user.id, project.slug)
    milestone = orch.add_milestone(
        title=req.title,
        description=req.description,
        phase=target_phase,
        criteria=req.criteria,
    )
    orch.save_state()

    return {
        "status": "created",
        "milestone": milestone.to_dict(),
        "milestones_count": len(orch.state.milestones),
    }


@router.put("/api/projects/{project_id}/research/milestones/{milestone_id}")
async def update_research_milestone(
    project_id: int,
    milestone_id: str,
    req: MilestoneUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Update milestone status or mark completed with output artifacts."""
    project = await ops.get_project_by_id(db, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    orch = _load_orchestrator(user.id, project.slug)
    target_m = next((m for m in orch.state.milestones if m.milestone_id == milestone_id), None)
    if not target_m:
        raise HTTPException(status_code=404, detail=f"Milestone '{milestone_id}' not found")

    if req.status:
        try:
            target_m.status = MilestoneStatus(req.status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status '{req.status}'")

    if target_m.status == MilestoneStatus.COMPLETED:
        orch.complete_milestone(milestone_id, output_artifacts=req.output_artifacts)
    else:
        if req.output_artifacts:
            target_m.output_artifacts.extend(req.output_artifacts)
        orch.state.updated_at = __import__("time").time()

    orch.save_state()

    return {
        "status": "updated",
        "milestone": target_m.to_dict(),
    }


@router.post("/api/projects/{project_id}/research/artifacts")
async def add_research_artifact(
    project_id: int,
    req: ArtifactCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Register a scientific research artifact (paper, hypothesis, experiment, metrics, manuscript section, bibtex)."""
    project = await ops.get_project_by_id(db, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    orch = _load_orchestrator(user.id, project.slug)
    atype = req.type.lower().strip()

    if atype == "paper":
        if isinstance(req.data, dict):
            orch.add_paper(req.data)
        else:
            orch.add_paper({"title": str(req.data)})
    elif atype == "hypothesis":
        if isinstance(req.data, dict):
            orch.add_hypothesis(req.data)
        else:
            orch.add_hypothesis({"claim": str(req.data)})
    elif atype == "experiment":
        if isinstance(req.data, dict):
            orch.add_experiment(req.data)
        else:
            orch.add_experiment({"description": str(req.data)})
    elif atype == "metrics":
        if isinstance(req.data, dict):
            orch.update_metrics(req.data)
        else:
            raise HTTPException(status_code=400, detail="Metrics artifact data must be a dictionary")
    elif atype == "manuscript_section":
        sec_name = req.section_name or "main"
        orch.update_manuscript_section(sec_name, str(req.data))
    elif atype == "bibtex":
        orch.add_bibtex(str(req.data))
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported artifact type '{req.type}'. Supported types: paper, hypothesis, experiment, metrics, manuscript_section, bibtex",
        )

    orch.save_state()

    return {
        "status": "artifact_registered",
        "type": atype,
        "artifacts_summary": {
            "papers": len(orch.state.artifacts.papers),
            "hypotheses": len(orch.state.artifacts.hypotheses),
            "experiments": len(orch.state.artifacts.experiments),
            "metrics_keys": list(orch.state.artifacts.metrics.keys()),
            "sections": list(orch.state.artifacts.manuscript_sections.keys()),
            "bibtex_count": len(orch.state.artifacts.bibtex_entries),
        },
    }
