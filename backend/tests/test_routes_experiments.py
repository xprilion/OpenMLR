"""Tests for the Machine Learning Experiments and Run Tracking API routes."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestExperimentsRoutes:
    async def test_create_and_get_run(self, client: AsyncClient):
        payload = {
            "name": "Transformer-FlashAttention-Benchmark",
            "description": "Benchmarking memory footprint and throughput",
            "hyperparameters": {
                "lr": 0.0003,
                "batch_size": 64,
                "model": "Llama-1B",
            },
            "compute_target": "Local H100",
            "tags": ["transformer", "flashattention", "benchmark"],
            "total_steps": 200,
            "total_epochs": 2,
        }

        create_resp = await client.post("/api/experiments/runs", json=payload)
        assert create_resp.status_code == 201
        data = create_resp.json()
        assert data["status"] == "created"
        run = data["run"]
        run_id = run["id"]
        assert run["name"] == payload["name"]
        assert run["hyperparameters"]["model"] == "Llama-1B"

        # Get run details
        get_resp = await client.get(f"/api/experiments/runs/{run_id}")
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert get_data["run"]["id"] == run_id
        assert get_data["run"]["name"] == payload["name"]

    async def test_list_runs_with_query_params(self, client: AsyncClient):
        # Create two runs
        await client.post(
            "/api/experiments/runs",
            json={"name": "Diffusion-UNet-Run", "tags": ["cv", "diffusion"]},
        )
        await client.post(
            "/api/experiments/runs",
            json={"name": "RL-PPO-Agent", "tags": ["rl", "ppo"]},
        )

        resp = await client.get("/api/experiments/runs?search=diffusion")
        assert resp.status_code == 200
        data = resp.json()
        assert "runs" in data
        assert any("Diffusion-UNet-Run" in r["name"] for r in data["runs"])
        assert not any("RL-PPO-Agent" in r["name"] for r in data["runs"])

    async def test_log_metrics_and_retrieve_trajectory(self, client: AsyncClient):
        create_resp = await client.post(
            "/api/experiments/runs",
            json={"name": "Metric-Tracking-Test", "total_steps": 50},
        )
        run_id = create_resp.json()["run"]["id"]

        # Log step 10
        metric_resp1 = await client.post(
            f"/api/experiments/runs/{run_id}/metrics",
            json={
                "step": 10,
                "epoch": 1,
                "metrics": {"train_loss": 3.5, "val_loss": 3.8, "lr": 0.001},
            },
        )
        assert metric_resp1.status_code == 200
        assert metric_resp1.json()["current_step"] == 10
        assert metric_resp1.json()["best_val_loss"] == 3.8

        # Log step 20 with lower val loss
        metric_resp2 = await client.post(
            f"/api/experiments/runs/{run_id}/metrics",
            json={
                "step": 20,
                "epoch": 1,
                "metrics": {"train_loss": 2.8, "val_loss": 3.1, "lr": 0.0009},
            },
        )
        assert metric_resp2.status_code == 200
        assert metric_resp2.json()["best_val_loss"] == 3.1

        # Check full run state
        get_resp = await client.get(f"/api/experiments/runs/{run_id}")
        run_data = get_resp.json()["run"]
        assert len(run_data["metrics"]["train_loss"]) == 2
        assert run_data["best_val_loss"] == 3.1

    async def test_update_status_and_logs(self, client: AsyncClient):
        create_resp = await client.post(
            "/api/experiments/runs",
            json={"name": "Status-Log-Test"},
        )
        run_id = create_resp.json()["run"]["id"]

        # Append logs
        log_resp = await client.post(
            f"/api/experiments/runs/{run_id}/logs",
            json={"lines": ["[INFO] Starting dataloader", "[INFO] GPU Allocated: 14.2 GB"]},
        )
        assert log_resp.status_code == 200
        assert log_resp.json()["total_lines"] == 2

        # Get logs
        get_log_resp = await client.get(f"/api/experiments/runs/{run_id}/logs")
        assert get_log_resp.status_code == 200
        assert len(get_log_resp.json()["logs"]) == 2

        # Update status to completed
        status_resp = await client.post(
            f"/api/experiments/runs/{run_id}/status",
            json={"status": "completed", "reason": "Target loss achieved"},
        )
        assert status_resp.status_code == 200
        assert status_resp.json()["run"]["status"] == "completed"

    async def test_register_checkpoint(self, client: AsyncClient):
        create_resp = await client.post(
            "/api/experiments/runs",
            json={"name": "Checkpoint-Test"},
        )
        run_id = create_resp.json()["run"]["id"]

        cp_resp = await client.post(
            f"/api/experiments/runs/{run_id}/checkpoints",
            json={
                "name": "model_epoch_5.pt",
                "step": 500,
                "epoch": 5,
                "path": "/checkpoints/model_epoch_5.pt",
                "file_size_mb": 750.2,
                "metrics": {"val_loss": 1.45, "accuracy": 0.88},
            },
        )
        assert cp_resp.status_code == 200
        cp_data = cp_resp.json()["checkpoint"]
        assert cp_data["name"] == "model_epoch_5.pt"
        assert cp_data["file_size_mb"] == 750.2

    async def test_compare_runs(self, client: AsyncClient):
        r1_resp = await client.post(
            "/api/experiments/runs",
            json={"name": "Run-Comparison-A", "hyperparameters": {"opt": "adamw", "lr": 0.001}},
        )
        r2_resp = await client.post(
            "/api/experiments/runs",
            json={"name": "Run-Comparison-B", "hyperparameters": {"opt": "lion", "lr": 0.0001}},
        )
        id1 = r1_resp.json()["run"]["id"]
        id2 = r2_resp.json()["run"]["id"]

        await client.post(
            f"/api/experiments/runs/{id1}/metrics",
            json={"step": 10, "metrics": {"train_loss": 2.0, "val_loss": 2.2}},
        )
        await client.post(
            f"/api/experiments/runs/{id2}/metrics",
            json={"step": 10, "metrics": {"train_loss": 1.8, "val_loss": 1.9}},
        )

        comp_resp = await client.get(f"/api/experiments/compare?run_ids={id1},{id2}")
        assert comp_resp.status_code == 200
        comp = comp_resp.json()
        assert len(comp["runs"]) == 2
        assert "opt" in comp["hyperparameters_comparison"]
        assert comp["metrics_summary"][id1]["best_val_loss"] == 2.2
        assert comp["metrics_summary"][id2]["best_val_loss"] == 1.9

    async def test_delete_run(self, client: AsyncClient):
        create_resp = await client.post(
            "/api/experiments/runs",
            json={"name": "Run-To-Delete"},
        )
        run_id = create_resp.json()["run"]["id"]

        del_resp = await client.delete(f"/api/experiments/runs/{run_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "deleted"

        # Subsequent get returns 404
        get_resp = await client.get(f"/api/experiments/runs/{run_id}")
        assert get_resp.status_code == 404

    async def test_error_handling(self, client: AsyncClient):
        # 404 on nonexistent run
        resp = await client.get("/api/experiments/runs/nonexistent-run-id")
        assert resp.status_code == 404

        # 400 on invalid status
        create_resp = await client.post("/api/experiments/runs", json={"name": "Test"})
        run_id = create_resp.json()["run"]["id"]
        bad_status_resp = await client.post(
            f"/api/experiments/runs/{run_id}/status",
            json={"status": "invalid_status_xyz"},
        )
        assert bad_status_resp.status_code == 400
