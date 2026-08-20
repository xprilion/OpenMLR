"""Tests for the Research Workflow & State Machine API routes."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from openmlr.db import operations as ops
from openmlr.db.models import User

pytestmark = pytest.mark.asyncio


class TestResearchPhasesAndGuidelines:
    async def test_list_research_phases(self, client: AsyncClient):
        resp = await client.get("/api/research/phases")
        assert resp.status_code == 200
        data = resp.json()
        assert "phases" in data
        phase_ids = [p["id"] for p in data["phases"]]
        assert "idle" in phase_ids
        assert "reconnaissance" in phase_ids
        assert "hypothesis" in phase_ids
        assert "experimentation" in phase_ids
        assert "analysis" in phase_ids
        assert "paper_drafting" in phase_ids
        assert "completed" in phase_ids

    async def test_get_all_guidelines(self, client: AsyncClient):
        resp = await client.get("/api/research/guidelines")
        assert resp.status_code == 200
        data = resp.json()
        assert "reconnaissance" in data
        assert "hypothesis" in data
        assert "experimentation" in data
        assert "analysis" in data
        assert "paper_drafting" in data


class TestProjectResearchWorkflow:
    @pytest.fixture
    async def project(self, db_session: AsyncSession, test_user: User):
        return await ops.create_project(
            db_session,
            user_id=test_user.id,
            name="Autonomous Attention Scaling",
            slug="autonomous-attention-scaling",
            description="Investigate sub-quadratic attention variants",
        )

    async def test_get_initial_research_state(
        self, auth_client: AsyncClient, project
    ):
        resp = await auth_client.get(f"/api/projects/{project.id}/research/state")
        assert resp.status_code == 200
        data = resp.json()
        assert data["project_id"] == project.id
        assert data["project_name"] == "Autonomous Attention Scaling"
        assert "state" in data
        assert "guidelines" in data

    async def test_start_research_workflow(
        self, auth_client: AsyncClient, project
    ):
        resp = await auth_client.post(
            f"/api/projects/{project.id}/research/start",
            json={
                "goal": "Benchmark FlashAttention-3 vs RingAttention",
                "initial_phase": "reconnaissance",
                "generate_default_milestones": True,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "started"
        assert data["state"]["goal"] == "Benchmark FlashAttention-3 vs RingAttention"
        assert data["state"]["current_phase"] == "reconnaissance"
        assert len(data["state"]["milestones"]) >= 5

    async def test_start_research_invalid_phase(
        self, auth_client: AsyncClient, project
    ):
        resp = await auth_client.post(
            f"/api/projects/{project.id}/research/start",
            json={
                "goal": "Invalid Phase Test",
                "initial_phase": "invalid_unknown_phase",
            },
        )
        assert resp.status_code == 400
        assert "invalid phase" in resp.json()["detail"].lower()

    async def test_transition_phase(
        self, auth_client: AsyncClient, project
    ):
        # Start first
        await auth_client.post(
            f"/api/projects/{project.id}/research/start",
            json={
                "goal": "LoRA Rank Scaling Analysis",
                "initial_phase": "reconnaissance",
            },
        )

        # Transition to hypothesis
        resp = await auth_client.post(
            f"/api/projects/{project.id}/research/transition",
            json={
                "next_phase": "hypothesis",
                "reason": "Cataloged 8 foundational literature papers",
                "artifacts_produced": ["paper_survey_table"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "transitioned"
        assert data["state"]["current_phase"] == "hypothesis"
        assert data["transition"]["to_phase"] == "hypothesis"
        assert "paper_survey_table" in data["transition"]["artifacts_produced"]

    async def test_create_and_update_milestone(
        self, auth_client: AsyncClient, project
    ):
        # Add custom milestone
        resp = await auth_client.post(
            f"/api/projects/{project.id}/research/milestones",
            json={
                "title": "Train baseline ResNet-18",
                "description": "Achieve >92% accuracy on CIFAR-10",
                "phase": "experimentation",
                "criteria": ["Accuracy >= 0.92", "Loss <= 0.35"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "created"
        milestone = data["milestone"]
        m_id = milestone["milestone_id"]
        assert milestone["title"] == "Train baseline ResNet-18"
        assert milestone["status"] == "pending"

        # Update milestone to completed
        update_resp = await auth_client.put(
            f"/api/projects/{project.id}/research/milestones/{m_id}",
            json={
                "status": "completed",
                "output_artifacts": ["baseline_model.pt", "eval_log.json"],
            },
        )
        assert update_resp.status_code == 200
        updated_data = update_resp.json()
        assert updated_data["status"] == "updated"
        assert updated_data["milestone"]["status"] == "completed"
        assert "baseline_model.pt" in updated_data["milestone"]["output_artifacts"]

    async def test_register_artifacts(
        self, auth_client: AsyncClient, project
    ):
        # Register paper
        p_resp = await auth_client.post(
            f"/api/projects/{project.id}/research/artifacts",
            json={"type": "paper", "data": {"arxiv_id": "2401.00001", "title": "Scalable ML"}},
        )
        assert p_resp.status_code == 200
        assert p_resp.json()["artifacts_summary"]["papers"] >= 1

        # Register hypothesis
        h_resp = await auth_client.post(
            f"/api/projects/{project.id}/research/artifacts",
            json={"type": "hypothesis", "data": {"claim": "Quantization retains 99% accuracy"}},
        )
        assert h_resp.status_code == 200
        assert h_resp.json()["artifacts_summary"]["hypotheses"] >= 1

        # Register metrics
        m_resp = await auth_client.post(
            f"/api/projects/{project.id}/research/artifacts",
            json={"type": "metrics", "data": {"train_loss": 0.24, "val_loss": 0.29}},
        )
        assert m_resp.status_code == 200
        assert "train_loss" in m_resp.json()["artifacts_summary"]["metrics_keys"]

        # Register manuscript section
        s_resp = await auth_client.post(
            f"/api/projects/{project.id}/research/artifacts",
            json={
                "type": "manuscript_section",
                "section_name": "methodology",
                "data": "\\section{Methodology}\nWe propose a novel attention operator...",
            },
        )
        assert s_resp.status_code == 200
        assert "methodology" in s_resp.json()["artifacts_summary"]["sections"]

        # Register bibtex
        b_resp = await auth_client.post(
            f"/api/projects/{project.id}/research/artifacts",
            json={
                "type": "bibtex",
                "data": "@article{scale2026, title={Scalable ML}}",
            },
        )
        assert b_resp.status_code == 200
        assert b_resp.json()["artifacts_summary"]["bibtex_count"] >= 1

    async def test_nonexistent_project_returns_404(
        self, auth_client: AsyncClient
    ):
        resp = await auth_client.get("/api/projects/999999/research/state")
        assert resp.status_code == 404
