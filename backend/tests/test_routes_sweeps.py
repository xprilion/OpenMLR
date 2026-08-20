"""Tests for the Hyperparameter Sweep and HPO API routes."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestSweepsRoutes:
    async def test_create_and_get_sweep(self, client: AsyncClient):
        payload = {
            "name": "LoRA Rank & Alpha Sweep",
            "description": "Optimizing LoRA hyperparameters on fine-tuning",
            "method": "random",
            "objective_metric": "eval_loss",
            "goal": "minimize",
            "max_trials": 4,
            "parameters": {
                "lora_r": {"param_type": "choice", "choices": [8, 16, 32]},
                "lora_alpha": {"param_type": "choice", "choices": [16, 32, 64]},
                "lr": {"param_type": "loguniform", "min_val": 1e-5, "max_val": 1e-3},
            },
        }

        resp = await client.post("/api/sweeps", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert "sweep" in data
        sweep = data["sweep"]
        sweep_id = sweep["sweep_id"]
        assert sweep["name"] == payload["name"]
        assert sweep["objective_metric"] == "eval_loss"

        # Get sweep
        get_resp = await client.get(f"/api/sweeps/{sweep_id}")
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert get_data["sweep"]["sweep_id"] == sweep_id

    async def test_list_sweeps(self, client: AsyncClient):
        await client.post(
            "/api/sweeps",
            json={
                "name": "CNN Filter Sweep",
                "method": "grid",
                "objective_metric": "accuracy",
                "goal": "maximize",
                "parameters": {"filters": {"param_type": "choice", "choices": [32, 64]}},
            },
        )

        resp = await client.get("/api/sweeps")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert any(s["name"] == "CNN Filter Sweep" for s in data["sweeps"])

    async def test_suggest_record_and_analysis_lifecycle(self, client: AsyncClient):
        create_resp = await client.post(
            "/api/sweeps",
            json={
                "name": "Vision Transformer Sweep",
                "method": "random",
                "objective_metric": "val_accuracy",
                "goal": "maximize",
                "max_trials": 3,
                "parameters": {
                    "patch_size": {"param_type": "choice", "choices": [8, 16]},
                    "lr": {"param_type": "uniform", "min_val": 0.0001, "max_val": 0.001},
                },
                "early_stopping": {"enabled": True, "min_steps": 2, "reduction_factor": 2.0},
            },
        )
        assert create_resp.status_code == 201
        sweep_id = create_resp.json()["sweep"]["sweep_id"]

        # Suggest trial 1
        sug_resp = await client.post(f"/api/sweeps/{sweep_id}/suggest")
        assert sug_resp.status_code == 200
        trial = sug_resp.json()["trial"]
        assert trial is not None
        trial_id = trial["trial_id"]

        # Prune check
        prune_resp = await client.post(
            f"/api/sweeps/{sweep_id}/trials/{trial_id}/prune-check",
            json={"current_step": 3, "current_metric_val": 0.95},
        )
        assert prune_resp.status_code == 200
        assert "should_prune" in prune_resp.json()

        # Record trial 1
        rec_resp = await client.post(
            f"/api/sweeps/{sweep_id}/trials/{trial_id}/record",
            json={
                "metrics": {"val_accuracy": 0.94, "loss": 0.12},
                "status": "completed",
                "step_history": [{"step": 1, "val_accuracy": 0.8}, {"step": 2, "val_accuracy": 0.94}],
            },
        )
        assert rec_resp.status_code == 200
        assert rec_resp.json()["trial"]["status"] == "completed"

        # Analysis
        analysis_resp = await client.get(f"/api/sweeps/{sweep_id}/analysis")
        assert analysis_resp.status_code == 200
        analysis = analysis_resp.json()["analysis"]
        assert analysis["completed_trials"] == 1
        assert analysis["best_metric_value"] == 0.94

        # Export report
        export_resp = await client.post(f"/api/sweeps/{sweep_id}/export")
        assert export_resp.status_code == 200
        assert "Hyperparameter Optimization Report" in export_resp.json()["report"]

        # Delete sweep
        del_resp = await client.delete(f"/api/sweeps/{sweep_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["deleted"] is True
