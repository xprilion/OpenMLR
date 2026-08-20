"""Research Phase & State Definitions for OpenMLR Autonomous Research Harness.

Defines the state machine, research phases, milestones, transitions, and research artifacts
that guide autonomous ML research exploration from literature reconnaissance to paper drafting.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ResearchPhase(str, Enum):
    """Standard phases of the autonomous machine learning research lifecycle."""

    IDLE = "idle"
    RECONNAISSANCE = "reconnaissance"  # Literature search, citation crawling, related work
    HYPOTHESIS = "hypothesis"          # Testable hypothesis formulation, baseline design
    EXPERIMENTATION = "experimentation"  # Model training, code execution, metric logging
    ANALYSIS = "analysis"              # Metric analysis, ablation studies, error recovery
    PAPER_DRAFTING = "paper_drafting"  # LaTeX manuscript writing, figures, BibTeX
    COMPLETED = "completed"            # Research pipeline successfully finished


class MilestoneStatus(str, Enum):
    """Execution status for research milestones."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PhaseTransition:
    """Record of a transition between research phases."""

    from_phase: ResearchPhase
    to_phase: ResearchPhase
    reason: str
    timestamp: float = field(default_factory=time.time)
    artifacts_produced: list[str] = field(default_factory=list)
    milestone_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_phase": self.from_phase.value,
            "to_phase": self.to_phase.value,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "artifacts_produced": self.artifacts_produced,
            "milestone_id": self.milestone_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PhaseTransition:
        return cls(
            from_phase=ResearchPhase(data["from_phase"]),
            to_phase=ResearchPhase(data["to_phase"]),
            reason=data.get("reason", ""),
            timestamp=data.get("timestamp", time.time()),
            artifacts_produced=data.get("artifacts_produced", []),
            milestone_id=data.get("milestone_id"),
        )


@dataclass
class ResearchMilestone:
    """A discrete verifiable goal within a research phase."""

    milestone_id: str
    phase: ResearchPhase
    title: str
    description: str
    status: MilestoneStatus = MilestoneStatus.PENDING
    criteria: list[str] = field(default_factory=list)
    output_artifacts: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "milestone_id": self.milestone_id,
            "phase": self.phase.value,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "criteria": self.criteria,
            "output_artifacts": self.output_artifacts,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResearchMilestone:
        return cls(
            milestone_id=data["milestone_id"],
            phase=ResearchPhase(data["phase"]),
            title=data.get("title", ""),
            description=data.get("description", ""),
            status=MilestoneStatus(data.get("status", MilestoneStatus.PENDING.value)),
            criteria=data.get("criteria", []),
            output_artifacts=data.get("output_artifacts", []),
            created_at=data.get("created_at", time.time()),
            completed_at=data.get("completed_at"),
        )


@dataclass
class ResearchArtifacts:
    """Collection of artifacts generated during research execution."""

    papers: list[dict[str, Any]] = field(default_factory=list)
    hypotheses: list[dict[str, Any]] = field(default_factory=list)
    experiments: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    manuscript_sections: dict[str, str] = field(default_factory=dict)
    bibtex_entries: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResearchArtifacts:
        return cls(
            papers=data.get("papers", []),
            hypotheses=data.get("hypotheses", []),
            experiments=data.get("experiments", []),
            metrics=data.get("metrics", {}),
            manuscript_sections=data.get("manuscript_sections", {}),
            bibtex_entries=data.get("bibtex_entries", []),
            notes=data.get("notes", []),
        )


@dataclass
class ResearchState:
    """Overall persistent state of an autonomous research exploration session."""

    goal: str
    current_phase: ResearchPhase = ResearchPhase.IDLE
    milestones: list[ResearchMilestone] = field(default_factory=list)
    history: list[PhaseTransition] = field(default_factory=list)
    artifacts: ResearchArtifacts = field(default_factory=ResearchArtifacts)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "current_phase": self.current_phase.value,
            "milestones": [m.to_dict() for m in self.milestones],
            "history": [h.to_dict() for h in self.history],
            "artifacts": self.artifacts.to_dict(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResearchState:
        return cls(
            goal=data.get("goal", ""),
            current_phase=ResearchPhase(data.get("current_phase", ResearchPhase.IDLE.value)),
            milestones=[
                ResearchMilestone.from_dict(m) for m in data.get("milestones", [])
            ],
            history=[PhaseTransition.from_dict(h) for h in data.get("history", [])],
            artifacts=ResearchArtifacts.from_dict(data.get("artifacts", {})),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )
