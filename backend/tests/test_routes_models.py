"""Tests for Model Registry, Model Card, Checkpoint Inspection, and Quantization API routes."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestModelsRoutes:
    async def test_register_and_get_model(self, auth_client: AsyncClient):
        payload = {
            "name": "Diffusion-XL-OpenMLR",
            "version": "1.0.0",
            "architecture": "U-Net/DiT",
            "framework": "safetensors",
            "task_type": "diffusion",
            "status": "evaluated",
            "description": "Latent diffusion backbone for image generation.",
            "parameters_count": 2_600_000_000,
            "model_size_mb": 5200.0,
            "tags": ["vision", "diffusion"],
            "metrics": {"fid": 12.4, "clip_score": 0.32},
            "hyperparameters": {"steps": 50, "guidance_scale": 7.5},
        }

        resp = await auth_client.post("/api/model-registry?project_id=test_proj", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert "model" in data
        model = data["model"]
        mid = model["id"]
        assert model["name"] == payload["name"]
        assert model["task_type"] == "diffusion"

        # Get model
        get_resp = await auth_client.get(f"/api/model-registry/{mid}?project_id=test_proj")
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert get_data["model"]["id"] == mid

    async def test_list_and_filter_models(self, auth_client: AsyncClient):
        await auth_client.post(
            "/api/model-registry?project_id=list_proj",
            json={
                "name": "Classifier-A",
                "framework": "pytorch",
                "task_type": "classification",
                "tags": ["nlp"],
            },
        )
        await auth_client.post(
            "/api/model-registry?project_id=list_proj",
            json={
                "name": "LLM-B",
                "framework": "safetensors",
                "task_type": "causal_lm",
                "tags": ["nlp"],
            },
        )

        resp = await auth_client.get("/api/model-registry?project_id=list_proj")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] >= 2

        filtered_resp = await auth_client.get("/api/model-registry?project_id=list_proj&task_type=causal_lm")
        assert filtered_resp.status_code == 200
        filtered_data = filtered_resp.json()
        assert all(m["task_type"] == "causal_lm" for m in filtered_data["models"])

    async def test_update_and_delete_model(self, auth_client: AsyncClient):
        reg = await auth_client.post(
            "/api/model-registry?project_id=mod_proj",
            json={"name": "TempModel", "status": "draft"},
        )
        mid = reg.json()["model"]["id"]

        # Update
        up_resp = await auth_client.put(
            f"/api/model-registry/{mid}?project_id=mod_proj",
            json={"status": "production", "description": "Ready for prod"},
        )
        assert up_resp.status_code == 200
        assert up_resp.json()["model"]["status"] == "production"

        # Delete
        del_resp = await auth_client.delete(f"/api/model-registry/{mid}?project_id=mod_proj")
        assert del_resp.status_code == 200
        assert del_resp.json()["success"] is True

        # Check 404
        get_404 = await auth_client.get(f"/api/model-registry/{mid}?project_id=mod_proj")
        assert get_404.status_code == 404

    async def test_generate_model_card(self, auth_client: AsyncClient):
        reg = await auth_client.post(
            "/api/model-registry?project_id=card_proj",
            json={
                "name": "ResNet-50-Ablated",
                "version": "1.0.0",
                "parameters_count": 25_000_000,
                "model_size_mb": 100.0,
                "metrics": {"top1_accuracy": 0.79},
            },
        )
        mid = reg.json()["model"]["id"]

        card_resp = await auth_client.post(
            f"/api/model-registry/{mid}/card?project_id=card_proj",
            json={
                "author": "Autonomous Scientist",
                "license": "Apache-2.0",
                "gpu_type": "NVIDIA A100",
                "gpu_hours": 12.0,
            },
        )
        assert card_resp.status_code == 200
        card_data = card_resp.json()
        assert "markdown" in card_data
        assert "latex" in card_data
        assert "bibtex" in card_data
        assert card_data["co2_emissions_kg"] > 0

    async def test_plan_quantization(self, auth_client: AsyncClient):
        reg = await auth_client.post(
            "/api/model-registry?project_id=quant_proj",
            json={
                "name": "Qwen-7B-OpenMLR",
                "parameters_count": 7_000_000_000,
                "model_size_mb": 14000.0,
            },
        )
        mid = reg.json()["model"]["id"]

        quant_resp = await auth_client.post(
            f"/api/model-registry/{mid}/quantization?project_id=quant_proj",
            json={"target_precisions": ["fp16", "int8", "int4"]},
        )
        assert quant_resp.status_code == 200
        data = quant_resp.json()
        assert len(data["estimates"]) == 3

    async def test_inspect_checkpoint_route(self, auth_client: AsyncClient):
        insp_resp = await auth_client.post(
            "/api/model-registry/inspect",
            json={
                "checkpoint_path": "model.safetensors",
                "parameters_count": 1_500_000_000,
                "framework": "safetensors",
            },
        )
        assert insp_resp.status_code == 200
        data = insp_resp.json()
        assert data["file_format"] == "safetensors"
        assert data["estimated_vram_fp16_mb"] > 0

    async def test_compare_models_route(self, auth_client: AsyncClient):
        r1 = await auth_client.post(
            "/api/model-registry?project_id=cmp_proj",
            json={"name": "Model-Alpha", "metrics": {"accuracy": 0.82}},
        )
        r2 = await auth_client.post(
            "/api/model-registry?project_id=cmp_proj",
            json={"name": "Model-Beta", "metrics": {"accuracy": 0.91}},
        )
        id1 = r1.json()["model"]["id"]
        id2 = r2.json()["model"]["id"]

        cmp_resp = await auth_client.post(
            "/api/model-registry/compare?project_id=cmp_proj",
            json={"model_ids": [id1, id2]},
        )
        assert cmp_resp.status_code == 200
        data = cmp_resp.json()
        assert data["recommended_model_id"] == id2
