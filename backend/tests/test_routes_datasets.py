"""Tests for the Dataset Management, Profiling, and Split API routes."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


@pytest.fixture
def sample_dataset_path(tmp_path: Path) -> str:
    file_path = tmp_path / "train_data.csv"
    data = [
        {"id": "1", "feature1": "10.5", "feature2": "20.1", "label": "pos", "text": "Good performance on CIFAR"},
        {"id": "2", "feature1": "15.2", "feature2": "18.3", "label": "neg", "text": "Poor generalization error"},
        {"id": "3", "feature1": "12.0", "feature2": "19.5", "label": "pos", "text": "Accurate prediction output"},
        {"id": "4", "feature1": "11.1", "feature2": "22.4", "label": "pos", "text": "Robust against adversarial noise"},
    ]
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(data[0].keys()))
        writer.writeheader()
        writer.writerows(data)
    return str(file_path)


class TestDatasetsRoutes:
    async def test_profile_dataset_endpoint(self, client: AsyncClient, sample_dataset_path: str):
        resp = await client.post(
            "/api/datasets/profile",
            json={"path": sample_dataset_path, "sample_size": 100},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["profile"]["total_rows"] == 4
        assert data["profile"]["total_columns"] == 5
        assert "feature1" in data["profile"]["columns"]
        assert data["profile"]["columns"]["feature1"]["dtype"] == "numeric"

    async def test_profile_dataset_not_found(self, client: AsyncClient):
        resp = await client.post(
            "/api/datasets/profile",
            json={"path": "/nonexistent/data.csv"},
        )
        assert resp.status_code == 404

    async def test_inspect_samples_endpoint(self, client: AsyncClient, sample_dataset_path: str):
        resp = await client.post(
            "/api/datasets/inspect",
            json={"path": sample_dataset_path, "n": 2, "strategy": "head"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["total_sampled"] == 2
        assert len(data["samples"]) == 2

    async def test_validate_dataset_endpoint(self, client: AsyncClient, sample_dataset_path: str):
        resp = await client.post(
            "/api/datasets/validate",
            json={
                "path": sample_dataset_path,
                "expected_columns": ["id", "feature1", "label"],
                "max_null_pct": 10.0,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["validation"]["valid"] is True

    async def test_split_dataset_endpoint(self, client: AsyncClient, sample_dataset_path: str, tmp_path: Path):
        out_dir = str(tmp_path / "splits_api")
        resp = await client.post(
            "/api/datasets/split",
            json={
                "path": sample_dataset_path,
                "output_dir": out_dir,
                "train_ratio": 0.5,
                "val_ratio": 0.25,
                "test_ratio": 0.25,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["manifest"]["train_count"] == 2
