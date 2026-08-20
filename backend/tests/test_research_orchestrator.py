"""Tests for Research State Machine & Orchestrator."""

import tempfile
from pathlib import Path

from openmlr.agent.prompts import build_system_prompt
from openmlr.agent.research_orchestrator import ResearchOrchestrator
from openmlr.agent.states import (
    MilestoneStatus,
    PhaseTransition,
    ResearchArtifacts,
    ResearchMilestone,
    ResearchPhase,
    ResearchState,
)


class TestResearchStates:
    """Test state objects and data models."""

    def test_research_phases_enum(self):
        assert ResearchPhase.IDLE == "idle"
        assert ResearchPhase.RECONNAISSANCE == "reconnaissance"
        assert ResearchPhase.HYPOTHESIS == "hypothesis"
        assert ResearchPhase.EXPERIMENTATION == "experimentation"
        assert ResearchPhase.ANALYSIS == "analysis"
        assert ResearchPhase.PAPER_DRAFTING == "paper_drafting"
        assert ResearchPhase.COMPLETED == "completed"

    def test_milestone_serialization(self):
        m = ResearchMilestone(
            milestone_id="m1",
            phase=ResearchPhase.RECONNAISSANCE,
            title="Survey Attention Mechanisms",
            description="Collect top 10 papers on linear attention",
            criteria=["10 papers collected"],
        )
        data = m.to_dict()
        assert data["milestone_id"] == "m1"
        assert data["phase"] == "reconnaissance"
        assert data["status"] == "pending"

        restored = ResearchMilestone.from_dict(data)
        assert restored.milestone_id == "m1"
        assert restored.phase == ResearchPhase.RECONNAISSANCE
        assert restored.title == "Survey Attention Mechanisms"

    def test_phase_transition_serialization(self):
        t = PhaseTransition(
            from_phase=ResearchPhase.RECONNAISSANCE,
            to_phase=ResearchPhase.HYPOTHESIS,
            reason="Completed literature review",
            artifacts_produced=["paper_1", "paper_2"],
        )
        data = t.to_dict()
        assert data["from_phase"] == "reconnaissance"
        assert data["to_phase"] == "hypothesis"
        assert data["artifacts_produced"] == ["paper_1", "paper_2"]

        restored = PhaseTransition.from_dict(data)
        assert restored.from_phase == ResearchPhase.RECONNAISSANCE
        assert restored.to_phase == ResearchPhase.HYPOTHESIS
        assert restored.artifacts_produced == ["paper_1", "paper_2"]

    def test_research_artifacts_serialization(self):
        artifacts = ResearchArtifacts(
            papers=[{"id": "2401.0001", "title": "Test Paper"}],
            hypotheses=[{"claim": "Method A outperforms Method B"}],
            experiments=[{"run_id": "exp_1", "status": "completed"}],
            metrics={"val_loss": 0.35, "accuracy": 0.94},
            manuscript_sections={"abstract": "This paper presents..."},
            bibtex_entries=["@article{test2026, title={Test}}"],
        )
        data = artifacts.to_dict()
        assert len(data["papers"]) == 1
        assert data["metrics"]["accuracy"] == 0.94

        restored = ResearchArtifacts.from_dict(data)
        assert len(restored.papers) == 1
        assert restored.metrics["accuracy"] == 0.94
        assert restored.manuscript_sections["abstract"] == "This paper presents..."

    def test_research_state_serialization(self):
        state = ResearchState(
            goal="Investigate FlashAttention-3 on TPU",
            current_phase=ResearchPhase.EXPERIMENTATION,
        )
        state.milestones.append(
            ResearchMilestone(
                milestone_id="m1",
                phase=ResearchPhase.EXPERIMENTATION,
                title="Run Benchmark",
                description="Profile FLOPs on Cloud TPU v5e",
            )
        )
        data = state.to_dict()
        assert data["goal"] == "Investigate FlashAttention-3 on TPU"
        assert data["current_phase"] == "experimentation"

        restored = ResearchState.from_dict(data)
        assert restored.goal == state.goal
        assert restored.current_phase == ResearchPhase.EXPERIMENTATION
        assert len(restored.milestones) == 1
        assert restored.milestones[0].milestone_id == "m1"


class TestResearchOrchestrator:
    """Test orchestrator lifecycle, transitions, and context generation."""

    def test_initialization(self):
        orchestrator = ResearchOrchestrator(goal="Evaluate LoRA rank scaling")
        assert orchestrator.goal == "Evaluate LoRA rank scaling"
        assert orchestrator.current_phase == ResearchPhase.IDLE

    def test_start_research_flow(self):
        orchestrator = ResearchOrchestrator()
        t = orchestrator.start_research("Autonomous ML Discovery")
        assert orchestrator.current_phase == ResearchPhase.RECONNAISSANCE
        assert t.from_phase == ResearchPhase.IDLE
        assert t.to_phase == ResearchPhase.RECONNAISSANCE
        assert len(orchestrator.state.history) == 1

    def test_transitions_through_phases(self):
        orch = ResearchOrchestrator(goal="Transformer Optimization")
        orch.start_research("Transformer Optimization")

        # 1. Reconnaissance -> Hypothesis
        t1 = orch.transition_to(
            ResearchPhase.HYPOTHESIS,
            reason="Found baseline paper arXiv:2401.12345",
            artifacts_produced=["paper_2401_12345"],
        )
        assert orch.current_phase == ResearchPhase.HYPOTHESIS
        assert t1.to_phase == ResearchPhase.HYPOTHESIS

        # 2. Hypothesis -> Experimentation
        t2 = orch.transition_to(
            ResearchPhase.EXPERIMENTATION,
            reason="Defined testable hypothesis H1 and ablation matrix",
        )
        assert orch.current_phase == ResearchPhase.EXPERIMENTATION

        # 3. Experimentation -> Analysis
        t3 = orch.transition_to(
            ResearchPhase.ANALYSIS,
            reason="Training run completed across 5 seeds",
            artifacts_produced=["run_001", "run_002"],
        )
        assert orch.current_phase == ResearchPhase.ANALYSIS

        # 4. Analysis -> Paper Drafting
        t4 = orch.transition_to(
            ResearchPhase.PAPER_DRAFTING,
            reason="Hypothesis confirmed with p < 0.01",
        )
        assert orch.current_phase == ResearchPhase.PAPER_DRAFTING

        # 5. Paper Drafting -> Completed
        t5 = orch.transition_to(
            ResearchPhase.COMPLETED,
            reason="LaTeX manuscript and BibTeX bibliography compiled",
        )
        assert orch.current_phase == ResearchPhase.COMPLETED
        assert len(orch.state.history) == 6  # start + 5 transitions

    def test_milestone_management(self):
        orch = ResearchOrchestrator(goal="Kernel speedup")
        m = orch.add_milestone(
            title="Profile Triton kernel",
            description="Measure latency vs cuBLAS baseline",
            phase=ResearchPhase.EXPERIMENTATION,
            criteria=["Speedup > 1.2x"],
        )
        assert m.status == MilestoneStatus.PENDING
        assert len(orch.state.milestones) == 1

        success = orch.complete_milestone(m.milestone_id, output_artifacts=["kernel_bench.json"])
        assert success is True
        assert m.status == MilestoneStatus.COMPLETED
        assert "kernel_bench.json" in m.output_artifacts

        # Non-existent milestone
        assert orch.complete_milestone("non_existent") is False

    def test_artifact_registration(self):
        orch = ResearchOrchestrator(goal="Artifact tracking")
        orch.add_paper({"arxiv_id": "2305.18290", "title": "DPO"})
        orch.add_hypothesis({"id": "H1", "statement": "DPO is more sample efficient"})
        orch.add_experiment({"id": "exp1", "lr": 1e-5, "epochs": 3})
        orch.update_metrics({"eval_reward": 0.82})
        orch.update_manuscript_section("introduction", "Direct Preference Optimization has emerged...")
        orch.add_bibtex("@article{rafailov2023direct, title={Direct Preference Optimization}}")

        art = orch.state.artifacts
        assert len(art.papers) == 1
        assert len(art.hypotheses) == 1
        assert len(art.experiments) == 1
        assert art.metrics["eval_reward"] == 0.82
        assert "introduction" in art.manuscript_sections
        assert len(art.bibtex_entries) == 1

        # Duplicate bibtex ignored
        orch.add_bibtex("@article{rafailov2023direct, title={Direct Preference Optimization}}")
        assert len(art.bibtex_entries) == 1

    def test_phase_guidelines_and_context_formatting(self):
        orch = ResearchOrchestrator(goal="FlashAttention research")
        orch.start_research("FlashAttention research")
        orch.add_milestone("Collect 5 papers", "Survey flashattention variants")

        guidelines = orch.get_phase_guidelines(ResearchPhase.RECONNAISSANCE)
        assert "RECONNAISSANCE" in guidelines
        assert "literature searches" in guidelines.lower()

        context_str = orch.format_research_context()
        assert "Research Harness State" in context_str
        assert "FlashAttention research" in context_str
        assert "Collect 5 papers" in context_str
        assert "Artifacts Summary" in context_str

    def test_state_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            orch1 = ResearchOrchestrator(goal="Persistence Test", workspace_path=tmppath)
            orch1.start_research("Persistence Test")
            orch1.add_paper({"title": "Test Paper 1"})
            saved_file = orch1.save_state()
            assert saved_file.exists()

            orch2 = ResearchOrchestrator(workspace_path=tmppath)
            loaded = orch2.load_state()
            assert loaded is True
            assert orch2.goal == "Persistence Test"
            assert orch2.current_phase == ResearchPhase.RECONNAISSANCE
            assert len(orch2.state.artifacts.papers) == 1

    def test_prompt_injection(self):
        orch = ResearchOrchestrator(goal="DeepSeek-R1 Replication")
        orch.start_research("DeepSeek-R1 Replication")
        r_ctx = orch.format_research_context()

        system_prompt = build_system_prompt(
            tool_specs=[],
            research_context=r_ctx,
        )
        assert "Research Harness State" in system_prompt
        assert "DeepSeek-R1 Replication" in system_prompt
