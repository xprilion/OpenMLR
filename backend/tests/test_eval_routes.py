"""Tests for the evaluation and benchmark harness API endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestEvalSuitesEndpoints:
    async def test_list_suites_returns_all_suites(self, client: AsyncClient):
        resp = await client.get("/api/eval/suites")
        assert resp.status_code == 200
        data = resp.json()
        assert "suites" in data
        assert len(data["suites"]) >= 4
        suite_ids = [s["id"] for s in data["suites"]]
        assert "reproduction" in suite_ids
        assert "optimization" in suite_ids
        assert "hypothesis" in suite_ids
        assert "full" in suite_ids

    async def test_suite_structure_and_tasks(self, client: AsyncClient):
        resp = await client.get("/api/eval/suites")
        assert resp.status_code == 200
        data = resp.json()
        for suite in data["suites"]:
            assert "id" in suite
            assert "name" in suite
            assert "task_count" in suite
            assert "tasks" in suite
            assert suite["task_count"] == len(suite["tasks"])
            for task in suite["tasks"]:
                assert "id" in task
                assert "name" in task
                assert "category" in task
                assert "difficulty" in task


class TestEvalTasksEndpoints:
    async def test_list_all_tasks(self, client: AsyncClient):
        resp = await client.get("/api/eval/tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert "tasks" in data
        assert len(data["tasks"]) >= 7

    async def test_filter_tasks_by_category(self, client: AsyncClient):
        resp = await client.get("/api/eval/tasks?category=optimization")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["tasks"]) >= 3
        for task in data["tasks"]:
            assert task["category"] == "optimization"

    async def test_get_task_details_success(self, client: AsyncClient):
        resp = await client.get("/api/eval/tasks/reproduction_resnet18_cifar10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "reproduction_resnet18_cifar10"
        assert data["category"] == "reproduction"
        assert "paper" in data
        assert "target_metrics" in data

    async def test_get_task_details_optimization(self, client: AsyncClient):
        resp = await client.get("/api/eval/tasks/optimization_fused_softmax_dropout")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "optimization_fused_softmax_dropout"
        assert data["category"] == "optimization"
        assert "specification" in data
        assert data["specification"]["kernel_name"] == "fused_softmax_dropout"

    async def test_get_task_details_hypothesis(self, client: AsyncClient):
        resp = await client.get("/api/eval/tasks/hypothesis_vit_patch_dropout")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "hypothesis_vit_patch_dropout"
        assert data["category"] == "hypothesis"
        assert "problem" in data

    async def test_get_nonexistent_task_returns_404(self, client: AsyncClient):
        resp = await client.get("/api/eval/tasks/non_existent_task_123")
        assert resp.status_code == 404
        data = resp.json()
        assert "not found" in data["detail"].lower()


class TestEvaluateTaskEndpoint:
    async def test_evaluate_reproduction_task_success(self, client: AsyncClient):
        resp = await client.post(
            "/api/eval/tasks/reproduction_resnet18_cifar10/evaluate",
            json={"agent_output": {"accuracy": 0.931, "test_loss": 0.325}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == "reproduction_resnet18_cifar10"
        assert data["success"] is True
        assert data["status"] == "completed"
        assert data["score"] >= 0.95

    async def test_evaluate_optimization_task_success(self, client: AsyncClient):
        resp = await client.post(
            "/api/eval/tasks/optimization_fused_softmax_dropout/evaluate",
            json={
                "agent_output": {
                    "optimized_latency_ms": 6.2,
                    "numerical_correctness": True,
                }
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == "optimization_fused_softmax_dropout"
        assert data["success"] is True
        assert data["status"] == "completed"
        assert data["metrics"]["speedup_ratio"] >= 1.5

    async def test_evaluate_nonexistent_task_returns_404(self, client: AsyncClient):
        resp = await client.post(
            "/api/eval/tasks/missing_task/evaluate",
            json={"agent_output": {}},
        )
        assert resp.status_code == 404


class TestRunBenchmarkSuiteEndpoint:
    async def test_run_reproduction_suite(self, client: AsyncClient):
        resp = await client.post(
            "/api/eval/run",
            json={"suite_name": "reproduction", "max_concurrency": 2},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "suite_name" in data
        assert "summary" in data
        assert "results" in data
        assert "markdown_summary" in data
        assert data["summary"]["total_tasks"] == 2
        assert data["summary"]["passed_tasks"] == 2

    async def test_run_optimization_suite_with_simulated_outputs(self, client: AsyncClient):
        simulated = {
            "optimization_fused_softmax_dropout": {"optimized_latency_ms": 5.0, "numerical_correctness": True},
            "optimization_flash_attention_tiling": {"optimized_latency_ms": 12.0, "numerical_correctness": True},
            "optimization_fused_layernorm": {"optimized_latency_ms": 3.0, "numerical_correctness": True},
        }
        resp = await client.post(
            "/api/eval/run",
            json={
                "suite_name": "optimization",
                "simulated_outputs": simulated,
                "max_concurrency": 3,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["total_tasks"] == 3
        assert data["summary"]["passed_tasks"] == 3
        assert data["summary"]["mean_speedup"] > 1.5

    async def test_run_unknown_suite_returns_400(self, client: AsyncClient):
        resp = await client.post(
            "/api/eval/run",
            json={"suite_name": "unknown_suite"},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "unknown suite" in data["detail"].lower()


class TestCustomTaskRegistrationEndpoints:
    async def test_register_custom_reproduction_task(self, client: AsyncClient):
        payload = {
            "task_id": "custom_mamba_reproduction",
            "name": "Mamba State Space Model Reproduction",
            "description": "Reproduce associative recall test accuracy from Gu & Dao 2023.",
            "paper_title": "Mamba: Linear-Time Sequence Modeling with Selective State Spaces",
            "arxiv_id": "2312.00752",
            "target_metrics": {"accuracy": 0.995},
            "dataset_name": "mqar",
            "difficulty": "hard",
            "timeout_seconds": 900.0,
        }
        resp = await client.post("/api/eval/custom-task/reproduction", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "registered"
        assert data["task_id"] == "custom_mamba_reproduction"
        assert data["category"] == "reproduction"

        # Verify task is discoverable via GET
        get_resp = await client.get("/api/eval/tasks/custom_mamba_reproduction")
        assert get_resp.status_code == 200
        assert get_resp.json()["name"] == "Mamba State Space Model Reproduction"

    async def test_register_custom_optimization_task(self, client: AsyncClient):
        payload = {
            "task_id": "custom_flash_decode_kernel",
            "name": "FlashDecoding Kernel for Long Context",
            "description": "Optimize multi-head attention decoding step for 32k context.",
            "kernel_name": "flash_decode_split_k",
            "framework": "triton",
            "baseline_latency_ms": 25.0,
            "target_speedup": 2.0,
            "difficulty": "expert",
            "timeout_seconds": 600.0,
        }
        resp = await client.post("/api/eval/custom-task/optimization", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "registered"
        assert data["task_id"] == "custom_flash_decode_kernel"
        assert data["category"] == "optimization"

        # Verify task is discoverable via GET
        get_resp = await client.get("/api/eval/tasks/custom_flash_decode_kernel")
        assert get_resp.status_code == 200
        assert get_resp.json()["specification"]["kernel_name"] == "flash_decode_split_k"
