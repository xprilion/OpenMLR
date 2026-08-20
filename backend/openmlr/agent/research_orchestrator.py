"""Autonomous Research Orchestration Engine for OpenMLR.

Drives systematic multi-phase scientific research:
1. Reconnaissance -> 2. Hypothesis -> 3. Experimentation -> 4. Analysis -> 5. Paper Drafting
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from .states import (
    MilestoneStatus,
    PhaseTransition,
    ResearchMilestone,
    ResearchPhase,
    ResearchState,
)

logger = logging.getLogger(__name__)

# Standard phase guidance prompts for the research agent
PHASE_GUIDELINES: dict[ResearchPhase, str] = {
    ResearchPhase.IDLE: (
        "Phase: IDLE. Ready to initiate a new structured research workflow."
    ),
    ResearchPhase.RECONNAISSANCE: (
        "Phase: RECONNAISSANCE (Literature Reconnaissance & Related Work).\n"
        "• Conduct broad literature searches across arXiv, OpenAlex, and Semantic Scholar.\n"
        "• Trace citation trees and analyze baseline architectures, benchmarks, and dataset methodologies.\n"
        "• Save relevant paper abstracts, citations, and key claims to project knowledge and research notes.\n"
        "• Goal: Identify concrete empirical baselines and unaddressed research gaps before proposing methods."
    ),
    ResearchPhase.HYPOTHESIS: (
        "Phase: HYPOTHESIS & PROPOSAL (Formulation & Experimental Design).\n"
        "• Formulate precise, testable, and falsifiable ML hypotheses.\n"
        "• Specify architectural modifications, training loss objectives, or algorithmic invariants.\n"
        "• Design controlled ablation studies and define quantitative evaluation metrics (e.g. Perplexity, Accuracy, FLOPs).\n"
        "• Define clear acceptance criteria and comparison benchmarks against standard baselines."
    ),
    ResearchPhase.EXPERIMENTATION: (
        "Phase: EXPERIMENTATION (Code Implementation & Compute Execution).\n"
        "• Implement clean, modular PyTorch / JAX scripts in the project workspace.\n"
        "• Dispatch training runs to local or remote compute nodes with proper logging and checkpointing.\n"
        "• Monitor training loss trajectories, learning rate schedules, and GPU resource utilization.\n"
        "• Log all run metrics, seeds, hyperparameters, and generated checkpoints systematically."
    ),
    ResearchPhase.ANALYSIS: (
        "Phase: ANALYSIS & SELF-CORRECTION (Empirical Findings & Ablations).\n"
        "• Analyze convergence stability, loss curves, eval benchmark scores, and error patterns.\n"
        "• If training diverged or encountered CUDA OOM / numerical NaN, apply automated self-healing.\n"
        "• Synthesize comparative tables and ablation matrices evaluating hypothesis validation.\n"
        "• Extract definitive conclusions and state-of-the-art comparisons."
    ),
    ResearchPhase.PAPER_DRAFTING: (
        "Phase: PAPER DRAFTING (LaTeX Manuscript & BibTeX Compilation).\n"
        "• Draft standard academic conference sections (Abstract, Introduction, Method, Experiments, Conclusion).\n"
        "• Structure clear LaTeX tables, algorithm blocks, and figure inclusions.\n"
        "• Maintain clean BibTeX citation entries with verified authors, DOIs, and arXiv identifiers.\n"
        "• Ensure LaTeX code compiles cleanly with no missing cross-references or undefined keys."
    ),
    ResearchPhase.COMPLETED: (
        "Phase: COMPLETED. Research pipeline deliverables are fulfilled and verified."
    ),
}


class ResearchOrchestrator:
    """Manages the autonomous scientific research lifecycle state machine."""

    def __init__(
        self,
        goal: str = "",
        state: ResearchState | None = None,
        workspace_path: str | Path | None = None,
    ):
        self.workspace_path = Path(workspace_path) if workspace_path else None
        self.state = state or ResearchState(goal=goal)
        if goal and not self.state.goal:
            self.state.goal = goal

    @property
    def current_phase(self) -> ResearchPhase:
        return self.state.current_phase

    @property
    def goal(self) -> str:
        return self.state.goal

    def start_research(
        self, goal: str, initial_phase: ResearchPhase = ResearchPhase.RECONNAISSANCE
    ) -> PhaseTransition:
        """Start a new research project with a stated scientific goal."""
        self.state.goal = goal
        self.state.created_at = time.time()
        self.state.updated_at = time.time()
        transition = self.transition_to(
            next_phase=initial_phase,
            reason=f"Initiating research project: {goal[:100]}",
        )
        return transition

    def transition_to(
        self,
        next_phase: ResearchPhase,
        reason: str,
        artifacts_produced: list[str] | None = None,
        milestone_id: str | None = None,
    ) -> PhaseTransition:
        """Transition from current phase to next phase."""
        from_phase = self.state.current_phase
        transition = PhaseTransition(
            from_phase=from_phase,
            to_phase=next_phase,
            reason=reason,
            timestamp=time.time(),
            artifacts_produced=artifacts_produced or [],
            milestone_id=milestone_id,
        )
        self.state.history.append(transition)
        self.state.current_phase = next_phase
        self.state.updated_at = time.time()
        clean_reason = "".join(c for c in str(reason) if c.isprintable()).strip()[:150]
        logger.info("Research phase transition: %s -> %s (%s)", from_phase.value, next_phase.value, clean_reason)
        return transition

    def add_milestone(
        self,
        title: str,
        description: str,
        phase: ResearchPhase | None = None,
        criteria: list[str] | None = None,
    ) -> ResearchMilestone:
        """Add a structured milestone to the active research plan."""
        target_phase = phase or self.state.current_phase
        m_id = f"m_{len(self.state.milestones) + 1}_{int(time.time()) % 10000}"
        milestone = ResearchMilestone(
            milestone_id=m_id,
            phase=target_phase,
            title=title,
            description=description,
            status=MilestoneStatus.PENDING,
            criteria=criteria or [],
            created_at=time.time(),
        )
        self.state.milestones.append(milestone)
        self.state.updated_at = time.time()
        return milestone

    def complete_milestone(
        self, milestone_id: str, output_artifacts: list[str] | None = None
    ) -> bool:
        """Mark a milestone as successfully completed."""
        for m in self.state.milestones:
            if m.milestone_id == milestone_id:
                m.status = MilestoneStatus.COMPLETED
                m.completed_at = time.time()
                if output_artifacts:
                    m.output_artifacts.extend(output_artifacts)
                self.state.updated_at = time.time()
                return True
        return False

    def add_paper(self, paper_data: dict[str, Any]) -> None:
        """Register a discovered academic paper artifact."""
        self.state.artifacts.papers.append(paper_data)
        self.state.updated_at = time.time()

    def add_hypothesis(self, hypothesis_data: dict[str, Any]) -> None:
        """Register a scientific hypothesis artifact."""
        self.state.artifacts.hypotheses.append(hypothesis_data)
        self.state.updated_at = time.time()

    def add_experiment(self, experiment_data: dict[str, Any]) -> None:
        """Register an executed experiment artifact."""
        self.state.artifacts.experiments.append(experiment_data)
        self.state.updated_at = time.time()

    def update_metrics(self, metrics: dict[str, Any]) -> None:
        """Update or merge experiment metrics dictionary."""
        self.state.artifacts.metrics.update(metrics)
        self.state.updated_at = time.time()

    def update_manuscript_section(self, section_name: str, content: str) -> None:
        """Update or insert a drafted manuscript section."""
        self.state.artifacts.manuscript_sections[section_name] = content
        self.state.updated_at = time.time()

    def add_bibtex(self, bibtex: str) -> None:
        """Register a BibTeX citation entry."""
        if bibtex.strip() and bibtex not in self.state.artifacts.bibtex_entries:
            self.state.artifacts.bibtex_entries.append(bibtex.strip())
            self.state.updated_at = time.time()

    def get_phase_guidelines(self, phase: ResearchPhase | None = None) -> str:
        """Get instructions and priorities for the specified or current phase."""
        target_phase = phase or self.state.current_phase
        return PHASE_GUIDELINES.get(target_phase, PHASE_GUIDELINES[ResearchPhase.IDLE])

    def format_research_context(self) -> str:
        """Format current research progress, active milestones, and artifacts as prompt context."""
        if self.state.current_phase == ResearchPhase.IDLE and not self.state.goal:
            return ""

        lines = [
            "### Research Harness State",
            f"**Goal**: {self.state.goal or 'Not set'}",
            f"**Active Phase**: {self.state.current_phase.value.upper()}",
            f"**Guidelines**:\n{self.get_phase_guidelines()}",
        ]

        # Milestones
        if self.state.milestones:
            lines.append("\n**Research Milestones**:")
            for m in self.state.milestones:
                status_icon = "✓" if m.status == MilestoneStatus.COMPLETED else "○"
                lines.append(
                    f"[{status_icon}] ({m.phase.value}) {m.title}: {m.description} [{m.status.value}]"
                )

        # Artifact counts summary
        art = self.state.artifacts
        lines.append(
            f"\n**Artifacts Summary**: {len(art.papers)} papers, "
            f"{len(art.hypotheses)} hypotheses, {len(art.experiments)} experiments, "
            f"{len(art.manuscript_sections)} draft sections, {len(art.bibtex_entries)} bibtex entries."
        )

        return "\n".join(lines)

    def _get_safe_state_path(self, path: str | Path | None = None) -> Path:
        """Resolve a safe, contained path for saving/loading state."""
        base_dir = self.workspace_path.resolve() if self.workspace_path else Path.cwd().resolve()
        meta_dir = (base_dir / ".project-meta").resolve()
        meta_dir.mkdir(parents=True, exist_ok=True)
        if path is not None:
            filename = Path(path).name
            return (meta_dir / filename).resolve()
        return (meta_dir / "research_state.json").resolve()

    def save_state(self, path: str | Path | None = None) -> Path:
        """Persist state JSON to disk."""
        target = self._get_safe_state_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.state.to_dict(), indent=2), encoding="utf-8")
        return target

    def load_state(self, path: str | Path | None = None) -> bool:
        """Load state JSON from disk."""
        target = self._get_safe_state_path(path)
        if not target.exists():
            return False
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
            self.state = ResearchState.from_dict(data)
            return True
        except Exception as e:
            logger.warning("Failed to load research state from %s: %s", target, e)
            return False
