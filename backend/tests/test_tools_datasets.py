"""Unit tests for the datasets agent tool."""

from __future__ import annotations

import csv
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from openmlr.tools.datasets import _handle_datasets, create_datasets_tool


@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    csv_file = tmp_path / "research_data.csv"
    data = [
        {"id": "1", "score": "95.5", "split": "train", "text": "Self-supervised representation learning"},
        {"id": "2", "score": "88.0", "split": "train", "text": "Reinforcement learning from human feedback"},
        {"id": "3", "score": "72.4", "split": "val", "text": "Direct preference optimization"},
    ]
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(data[0].keys()))
        writer.writeheader()
        writer.writerows(data)
    return csv_file


def test_create_datasets_tool_spec():
    tool = create_datasets_tool()
    assert tool.name == "datasets"
    assert "operation" in tool.parameters["properties"]
    assert "profile" in tool.parameters["properties"]["operation"]["enum"]
    assert "split" in tool.parameters["properties"]["operation"]["enum"]


@pytest.mark.asyncio
async def test_handle_datasets_profile(sample_csv: Path):
    output, success = await _handle_datasets(
        operation="profile",
        path=str(sample_csv),
    )
    assert success is True
    assert "Dataset Profile" in output
    assert "score" in output


@pytest.mark.asyncio
async def test_handle_datasets_inspect_samples(sample_csv: Path):
    output, success = await _handle_datasets(
        operation="inspect_samples",
        path=str(sample_csv),
        n=2,
    )
    assert success is True
    assert "Dataset Samples" in output
    assert "Direct preference optimization" in output or "Self-supervised" in output


@pytest.mark.asyncio
async def test_handle_datasets_validate(sample_csv: Path):
    output, success = await _handle_datasets(
        operation="validate",
        path=str(sample_csv),
        expected_columns=["id", "score", "split", "text"],
    )
    assert success is True
    assert "PASSED" in output


@pytest.mark.asyncio
async def test_handle_datasets_split(sample_csv: Path, tmp_path: Path):
    split_dir = tmp_path / "splits"
    output, success = await _handle_datasets(
        operation="split",
        path=str(sample_csv),
        output_dir=str(split_dir),
        train_ratio=0.7,
        val_ratio=0.3,
        test_ratio=0.0,
    )
    assert success is True
    assert "Dataset Split Completed" in output
    assert (split_dir / "split_manifest.json").exists()


@pytest.mark.asyncio
async def test_handle_datasets_register(sample_csv: Path):
    mock_session = MagicMock()
    mock_kg = MagicMock()
    mock_session.workspace.knowledge_graph = mock_kg

    output, success = await _handle_datasets(
        operation="register",
        path=str(sample_csv),
        dataset_name="cifar10_custom",
        description="Custom CIFAR-10 evaluation set",
        tags=["cv", "benchmark"],
        session=mock_session,
    )
    assert success is True
    assert "Dataset Registered" in output
    assert mock_kg.add_entity.called


@pytest.mark.asyncio
async def test_handle_datasets_summary_help():
    output, success = await _handle_datasets(operation="summary")
    assert success is True
    assert "Datasets Tool Operations" in output


@pytest.mark.asyncio
async def test_handle_datasets_missing_path():
    output, success = await _handle_datasets(operation="profile", path="")
    assert success is False
    assert "required" in output.lower()
