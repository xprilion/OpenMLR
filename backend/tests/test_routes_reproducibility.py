"""Unit tests for the Reproducibility REST API routes."""

import pytest
from httpx import ASGITransport, AsyncClient

from openmlr.app import app


@pytest.mark.asyncio
async def test_reproducibility_routes_audit_and_crud():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Audit
        audit_payload = {
            "target_path": "mock_test_path",
            "venue": "neurips",
            "code_snippets": {
                "exp.py": "import torch\ntorch.manual_seed(42)\ntorch.save({}, 'model.pt')",
                "requirements.txt": "torch==2.1.0\n",
            },
        }
        res_audit = await client.post("/api/reproducibility/audit?project_id=proj_routes", json=audit_payload)
        assert res_audit.status_code == 200
        report = res_audit.json()
        assert "id" in report
        report_id = report["id"]
        assert report["overall_score"] > 50.0

        # List
        res_list = await client.get("/api/reproducibility/reports?project_id=proj_routes")
        assert res_list.status_code == 200
        reports = res_list.json()
        assert len(reports) >= 1
        assert any(r["id"] == report_id for r in reports)

        # Get
        res_get = await client.get(f"/api/reproducibility/reports/{report_id}?project_id=proj_routes")
        assert res_get.status_code == 200
        assert res_get.json()["id"] == report_id

        # Dockerfile
        res_dock = await client.post(
            "/api/reproducibility/dockerfile",
            json={"framework": "pytorch", "requirements": ["torch==2.1.0"]},
        )
        assert res_dock.status_code == 200
        assert "FROM nvidia/cuda" in res_dock.json()["dockerfile"]

        # Appendix
        res_app = await client.post(
            "/api/reproducibility/appendix?project_id=proj_routes",
            json={"report_id": report_id, "paper_title": "Routes Test Paper"},
        )
        assert res_app.status_code == 200
        assert "\\section{Reproducibility Statement}" in res_app.json()["latex_appendix"]

        # Fix Determinism
        res_fix = await client.post(
            "/api/reproducibility/fix-determinism",
            json={"framework": "pytorch", "seed": 42},
        )
        assert res_fix.status_code == 200
        assert "torch.manual_seed(seed)" in res_fix.json()["determinism_snippet"]
        assert "set_seed(42)" in res_fix.json()["determinism_snippet"]

        # Delete
        res_del = await client.delete(f"/api/reproducibility/reports/{report_id}?project_id=proj_routes")
        assert res_del.status_code == 200

        # Get 404
        res_get_deleted = await client.get(f"/api/reproducibility/reports/{report_id}?project_id=proj_routes")
        assert res_get_deleted.status_code == 404
