"""Unit tests for the Figures REST API endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from openmlr.app import app


@pytest.mark.asyncio
async def test_figures_crud_routes():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Generate figure
        payload = {
            "title": "Empirical Scaling Law",
            "caption": "Compute vs. loss scaling on OpenWebText.",
            "plot_type": "loss_curve",
            "style_theme": "neurips",
            "palette": "colorblind",
            "x_label": "FLOPs",
            "y_label": "Test Perplexity",
            "series_data": {
                "Dense": [{"x": 1e18, "y": 12.4}, {"x": 1e19, "y": 8.2}],
                "Sparse MoE": [{"x": 1e18, "y": 9.1}, {"x": 1e19, "y": 5.7}],
            },
            "categories": [],
            "values_matrix": [],
            "width_inches": 6.0,
            "height_inches": 4.0,
            "generate_tikz": True,
        }
        res = await client.post("/api/figures?project_id=proj_api", json=payload)
        assert res.status_code == 201
        data = res.json()
        fig_id = data["figure"]["id"]
        assert data["figure"]["title"] == "Empirical Scaling Law"

        # List figures
        res_list = await client.get("/api/figures?project_id=proj_api")
        assert res_list.status_code == 200
        assert res_list.json()["total_count"] >= 1

        # Get figure
        res_get = await client.get(f"/api/figures/{fig_id}?project_id=proj_api")
        assert res_get.status_code == 200
        assert res_get.json()["figure"]["id"] == fig_id

        # Multi-panel
        multi_res = await client.post(
            "/api/figures/multi-panel?project_id=proj_api",
            json={
                "title": "Combined Results",
                "caption": "Summary of all figures.",
                "figure_ids": [fig_id],
                "columns": 1,
                "subcaptions": {},
            },
        )
        assert multi_res.status_code == 200
        assert multi_res.json()["figure_count"] == 1

        # Delete figure
        del_res = await client.delete(f"/api/figures/{fig_id}?project_id=proj_api")
        assert del_res.status_code == 200
        assert del_res.json()["success"] is True
