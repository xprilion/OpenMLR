"""Unit tests for DatasetProfiler (profiling, statistics, validation, splitting)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from openmlr.services.dataset_profiler import DatasetProfiler


@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    csv_file = tmp_path / "data.csv"
    data = [
        {"id": "1", "age": "25", "income": "50000", "label": "A", "text": "Short sample text", "active": "true"},
        {"id": "2", "age": "30", "income": "60000", "label": "A", "text": "Another sentence for ML training.", "active": "true"},
        {"id": "3", "age": "45", "income": "90000", "label": "B", "text": "Natural language processing benchmarks.", "active": "false"},
        {"id": "4", "age": "35", "income": "75000", "label": "A", "text": "Transformer self-attention mechanisms.", "active": "true"},
        {"id": "5", "age": "", "income": "80000", "label": "B", "text": "", "active": "false"},
    ]
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(data[0].keys()))
        writer.writeheader()
        writer.writerows(data)
    return csv_file


@pytest.fixture
def sample_jsonl(tmp_path: Path) -> Path:
    jsonl_file = tmp_path / "data.jsonl"
    data = [
        {"prompt": "What is attention?", "response": "Attention is all you need.", "rating": 5},
        {"prompt": "Explain gradient descent.", "response": "Optimization algorithm.", "rating": 4},
        {"prompt": "Define cross-entropy.", "response": "Loss function for classification.", "rating": 5},
    ]
    with open(jsonl_file, "w", encoding="utf-8") as f:
        for r in data:
            f.write(json.dumps(r) + "\n")
    return jsonl_file


def test_detect_format():
    assert DatasetProfiler.detect_format("data.csv") == "csv"
    assert DatasetProfiler.detect_format("data.tsv") == "tsv"
    assert DatasetProfiler.detect_format("data.jsonl") == "jsonl"
    assert DatasetProfiler.detect_format("data.ndjson") == "jsonl"
    assert DatasetProfiler.detect_format("data.json") == "json"
    assert DatasetProfiler.detect_format("data.txt") == "text"


def test_load_records_csv(sample_csv: Path):
    records, fmt, size = DatasetProfiler.load_records(sample_csv)
    assert fmt == "csv"
    assert len(records) == 5
    assert size > 0
    assert records[0]["id"] == "1"


def test_load_records_jsonl(sample_jsonl: Path):
    records, fmt, size = DatasetProfiler.load_records(sample_jsonl)
    assert fmt == "jsonl"
    assert len(records) == 3
    assert records[0]["rating"] == 5


def test_load_records_empty_or_missing(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        DatasetProfiler.load_records(tmp_path / "missing.csv")

    empty_file = tmp_path / "empty.csv"
    empty_file.touch()
    records, fmt, size = DatasetProfiler.load_records(empty_file)
    assert len(records) == 0


def test_profile_csv(sample_csv: Path):
    prof = DatasetProfiler.profile(sample_csv)
    assert prof.total_rows == 5
    assert prof.total_columns == 6
    assert prof.health_score > 50
    assert "income" in prof.columns
    assert prof.columns["income"].dtype == "numeric"
    assert prof.columns["income"].stats["min"] == 50000.0
    assert prof.columns["income"].stats["max"] == 90000.0
    assert prof.columns["active"].dtype == "boolean"
    assert prof.columns["label"].dtype == "categorical"


def test_sample_records_strategies(sample_csv: Path):
    head_samples = DatasetProfiler.sample_records(sample_csv, n=2, strategy="head")
    assert len(head_samples) == 2
    assert head_samples[0]["id"] == "1"

    random_samples = DatasetProfiler.sample_records(sample_csv, n=3, strategy="random", seed=123)
    assert len(random_samples) == 3

    stratified_samples = DatasetProfiler.sample_records(
        sample_csv, n=4, strategy="stratified", label_column="label", seed=123
    )
    assert len(stratified_samples) <= 4


def test_validate_dataset_pass(sample_csv: Path):
    res = DatasetProfiler.validate_dataset(
        sample_csv,
        expected_columns=["id", "age", "income", "label"],
        max_null_pct=50.0,
    )
    assert res["valid"] is True
    assert len(res["errors"]) == 0


def test_validate_dataset_fail_missing_col(sample_csv: Path):
    res = DatasetProfiler.validate_dataset(
        sample_csv,
        expected_columns=["id", "nonexistent_col"],
    )
    assert res["valid"] is False
    assert any("nonexistent_col" in err for err in res["errors"])


def test_split_dataset(sample_csv: Path, tmp_path: Path):
    out_dir = tmp_path / "splits"
    manifest = DatasetProfiler.split_dataset(
        sample_csv,
        output_dir=out_dir,
        train_ratio=0.6,
        val_ratio=0.2,
        test_ratio=0.2,
        seed=42,
    )
    assert manifest["total_records"] == 5
    assert manifest["train_count"] + manifest["val_count"] + manifest["test_count"] == 5
    assert Path(manifest["splits"]["train"]).exists()
    assert Path(manifest["splits"]["val"]).exists()
    assert Path(manifest["splits"]["test"]).exists()
    assert (out_dir / "split_manifest.json").exists()
