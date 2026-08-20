"""Unit tests for Ablation REST API routes."""

import pytest
from httpx import ASGITransport, AsyncClient

from openmlr.app import app


@pytest.mark.asyncio
async def test_ablation_routes_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create study
        create_payload = {
            "title": "Routing Layer Ablation",
            "description": "Evaluating MoE top-k router vs dense",
            "project_id": "proj_ablation_routes",
            "primary_metric": "bleu_score",
            "higher_is_better": True,
            "baseline_variant_name": "MoE Top-2",
        }
        res_create = await client.post("/api/ablation", json=create_payload)
        assert res_create.status_code == 201
        data = res_create.json()
        study_id = data["study"]["id"]
        assert data["study"]["title"] == "Routing Layer Ablation"

        # 2. Record Baseline Runs
        res_b = await client.post(
            f"/api/ablation/{study_id}/runs",
            json={
                "variant_name": "MoE Top-2",
                "variant_type": "baseline",
                "metrics": {"bleu_score": [34.5, 34.8, 34.6, 35.0, 34.7]},
            },
        )
        assert res_b.status_code == 200

        # 3. Record Ablation Variant Runs
        res_v = await client.post(
            f"/api/ablation/{study_id}/runs",
            json={
                "variant_name": "Dense Baseline",
                "variant_type": "ablation",
                "removed_components": ["MoE Routing"],
                "metrics": {"bleu_score": [31.2, 31.0, 31.5, 31.1, 31.3]},
            },
        )
        assert res_v.status_code == 200

        # 4. Trigger Analyze
        res_analyze = await client.post(
            f"/api/ablation/{study_id}/analyze",
            json={"correction_method": "holm_bonferroni"},
        )
        assert res_analyze.status_code == 200
        study_data = res_analyze.json()["study"]
        assert len(study_data["component_impacts"]) >= 1
        assert study_data["component_impacts"][0]["component_name"] == "MoE Routing"
        assert study_data["component_impacts"][0]["is_critical"] is True

        # 5. Generate LaTeX Table
        res_latex = await client.post(
            f"/api/ablation/{study_id}/latex",
            json={"include_significance_stars": True},
        )
        assert res_latex.status_code == 200
        assert "\\begin{table}" in res_latex.json()["latex_table"]

        # 6. List and Get
        res_list = await client.get("/api/ablation?project_id=proj_ablation_routes")
        assert res_list.status_code == 200
        assert res_list.json()["total_count"] >= 1

        res_get = await client.get(f"/api/ablation/{study_id}")
        assert res_get.status_code == 200
        assert res_get.json()["study"]["id"] == study_id

        # 7. Delete
        res_del = await client.delete(f"/api/ablation/{study_id}")
        assert res_del.status_code == 200
        assert res_del.json()["success"] is True
