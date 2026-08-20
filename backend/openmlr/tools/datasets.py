"""Datasets tool — dataset profiling, inspection, validation, and curation for AI research agents."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ..agent.types import ToolSpec
from ..services.dataset_profiler import DatasetProfiler

log = logging.getLogger(__name__)


def _parse_list(val: Any) -> list[str]:
    """Parse list or comma-separated string."""
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    if isinstance(val, str) and val.strip():
        if val.strip().startswith("[") and val.strip().endswith("]"):
            try:
                parsed = json.loads(val)
                if isinstance(parsed, list):
                    return [str(x).strip() for x in parsed if str(x).strip()]
            except Exception:
                pass
        return [x.strip() for x in val.split(",") if x.strip()]
    return []


async def _handle_datasets(
    operation: str,
    path: str = "",
    sample_size: int = 2000,
    n: int = 5,
    offset: int = 0,
    strategy: str = "head",
    label_column: str | None = None,
    expected_columns: Any = None,
    max_null_pct: float = 20.0,
    max_token_length: int | None = None,
    output_dir: str = "",
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
    stratify_column: str | None = None,
    dataset_name: str = "",
    description: str = "",
    tags: Any = None,
    session=None,
    **kwargs: Any,
) -> tuple[str, bool]:
    """Handle dataset profiling, inspection, validation, split, and registration operations."""
    op = (operation or "").strip().lower()

    if not path and op not in ("summary", "help"):
        return "Error: 'path' parameter is required for dataset operations.", False

    file_path = Path(path) if path else None

    try:
        if op in ("profile", "analyze"):
            if not file_path or not file_path.exists():
                return f"Error: Dataset file not found at '{path}'.", False

            profile = DatasetProfiler.profile(file_path, sample_size=sample_size)
            p_dict = profile.to_dict()

            output = [
                f"# Dataset Profile: {file_path.name}",
                f"- **Format**: {profile.format.upper()}",
                f"- **Sampled Rows**: {profile.total_rows:,}",
                f"- **Columns**: {profile.total_columns}",
                f"- **File Size**: {profile.file_size_bytes / (1024 * 1024):.2f} MB",
                f"- **Health Score**: {profile.health_score}/100",
                "",
            ]

            if profile.warnings:
                output.append("### Diagnostic Warnings")
                for w in profile.warnings:
                    output.append(f"- ⚠️ {w}")
                output.append("")

            output.append("### Column Details")
            for c_name, c_prof in profile.columns.items():
                stats = c_prof.stats
                line = f"- **`{c_name}`** (`{c_prof.dtype}`): {c_prof.null_percentage}% null ({c_prof.null_count}/{c_prof.total_count}), {c_prof.unique_count} unique."
                if c_prof.dtype == "numeric":
                    line += f" Range: [{stats.get('min')}, {stats.get('max')}], Mean: {stats.get('mean')}, Std: {stats.get('std')}."
                elif c_prof.dtype == "categorical":
                    line += f" Imbalance: {stats.get('imbalance_ratio', 1.0)}x. Top classes: {list(stats.get('top_classes', {}).keys())[:4]}."
                elif c_prof.dtype == "text":
                    line += f" Avg chars: {stats.get('char_len_avg')}, Mean tokens: {stats.get('token_est_mean')}, Max tokens: {stats.get('token_est_max')}."
                output.append(line)

            output.append("\n```json\n" + json.dumps(p_dict, indent=2) + "\n```")
            return "\n".join(output), True

        elif op in ("inspect_samples", "sample", "preview"):
            if not file_path or not file_path.exists():
                return f"Error: Dataset file not found at '{path}'.", False

            samples = DatasetProfiler.sample_records(
                file_path,
                n=n,
                offset=offset,
                strategy=strategy,
                label_column=label_column,
            )

            output = [
                f"# Dataset Samples: {file_path.name} (strategy={strategy}, n={len(samples)})",
                "```json",
                json.dumps(samples, indent=2, default=str),
                "```",
            ]
            return "\n".join(output), True

        elif op in ("validate", "check"):
            if not file_path or not file_path.exists():
                return f"Error: Dataset file not found at '{path}'.", False

            exp_cols = _parse_list(expected_columns) if expected_columns else None
            val_res = DatasetProfiler.validate_dataset(
                file_path,
                expected_columns=exp_cols,
                max_null_pct=max_null_pct,
                max_token_length=max_token_length,
            )

            status_str = "PASSED ✅" if val_res["valid"] else "FAILED ❌"
            output = [
                f"# Dataset Validation: {file_path.name} — {status_str}",
                f"- **Health Score**: {val_res.get('health_score', 0)}/100",
                f"- **Rows**: {val_res.get('total_rows', 0)} | **Columns**: {val_res.get('total_columns', 0)}",
                "",
            ]
            if val_res["errors"]:
                output.append("### Validation Errors")
                for err in val_res["errors"]:
                    output.append(f"- ❌ {err}")
                output.append("")

            if val_res["warnings"]:
                output.append("### Warnings")
                for w in val_res["warnings"]:
                    output.append(f"- ⚠️ {w}")

            return "\n".join(output), val_res["valid"]

        elif op in ("split", "partition"):
            if not file_path or not file_path.exists():
                return f"Error: Dataset file not found at '{path}'.", False

            target_dir = output_dir or str(file_path.parent / f"{file_path.stem}_splits")
            manifest = DatasetProfiler.split_dataset(
                file_path,
                output_dir=target_dir,
                train_ratio=train_ratio,
                val_ratio=val_ratio,
                test_ratio=test_ratio,
                stratify_column=stratify_column,
            )

            output = [
                f"# Dataset Split Completed: {file_path.name}",
                f"- **Train records**: {manifest['train_count']:,} (`{manifest['splits']['train']}`)",
                f"- **Val records**: {manifest['val_count']:,} (`{manifest['splits']['val']}`)",
                f"- **Test records**: {manifest['test_count']:,} (`{manifest['splits']['test']}`)",
                f"- **Stratified**: {manifest['stratified_by'] or 'Random'}",
                f"- **Manifest**: `{target_dir}/split_manifest.json`",
            ]
            return "\n".join(output), True

        elif op in ("register", "register_kg"):
            name = dataset_name or (file_path.stem if file_path else "dataset")
            profile = DatasetProfiler.profile(file_path, sample_size=1000) if file_path and file_path.exists() else None

            # Attempt knowledge graph registration
            kg_synced = False
            if session and hasattr(session, "workspace"):
                ws = getattr(session, "workspace", None)
                if ws and hasattr(ws, "knowledge_graph") and ws.knowledge_graph:
                    props = {
                        "path": str(file_path) if file_path else "",
                        "format": profile.format if profile else "",
                        "total_rows": profile.total_rows if profile else 0,
                        "health_score": profile.health_score if profile else 100,
                        "description": description,
                        "tags": _parse_list(tags) if tags else [],
                    }
                    ws.knowledge_graph.add_entity(
                        entity_id=f"dataset_{name}",
                        entity_type="dataset",
                        name=name,
                        properties=props,
                    )
                    kg_synced = True

            output = [
                f"# Dataset Registered: `{name}`",
                f"- **Path**: `{path}`",
                f"- **Knowledge Graph Synced**: {'Yes' if kg_synced else 'No (in-memory only)'}",
                f"- **Description**: {description or 'N/A'}",
            ]
            return "\n".join(output), True

        elif op in ("summary", "help"):
            return (
                "Datasets Tool Operations:\n"
                "- `profile`: Compute statistics, column distributions, null analysis, text token lengths, and health score.\n"
                "- `inspect_samples`: Preview sample records (head, random, stratified).\n"
                "- `validate`: Validate against schema constraints, missing values, and token limits.\n"
                "- `split`: Partition dataset into train/val/test splits.\n"
                "- `register`: Register dataset in project Knowledge Graph."
            ), True

        else:
            return (
                f"Unknown datasets operation '{operation}'. Supported: profile, inspect_samples, validate, split, register, summary.",
                False,
            )

    except Exception as e:
        log.exception("Error executing datasets operation '%s': %s", op, e)
        return f"Error executing datasets operation '{op}': {e}", False


def create_datasets_tool() -> ToolSpec:
    """Create the ToolSpec definition for the datasets tool."""
    return ToolSpec(
        name="datasets",
        description=(
            "Inspect, profile, validate, and partition machine learning datasets. "
            "Supports CSV, TSV, JSON, JSONL, and text formats. Computes column distributions, "
            "missingness, class balance, token length distributions, and generates reproducible splits."
        ),
        parameters={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "Operation: profile, inspect_samples, validate, split, register, summary",
                    "enum": ["profile", "inspect_samples", "validate", "split", "register", "summary"],
                },
                "path": {
                    "type": "string",
                    "description": "Path to the dataset file (CSV, JSONL, TSV, JSON, TXT)",
                },
                "sample_size": {
                    "type": "integer",
                    "description": "Maximum number of rows to sample for profiling (default: 2000)",
                },
                "n": {
                    "type": "integer",
                    "description": "Number of sample rows to inspect (default: 5)",
                },
                "offset": {
                    "type": "integer",
                    "description": "Offset index for inspecting samples (default: 0)",
                },
                "strategy": {
                    "type": "string",
                    "description": "Sampling strategy: head, random, stratified (default: head)",
                    "enum": ["head", "random", "stratified"],
                },
                "label_column": {
                    "type": "string",
                    "description": "Label or class column name for stratified sampling",
                },
                "expected_columns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of expected column names for validation",
                },
                "max_null_pct": {
                    "type": "number",
                    "description": "Maximum allowed null percentage per column in validation (default: 20.0)",
                },
                "max_token_length": {
                    "type": "integer",
                    "description": "Maximum allowed token count for text columns in validation",
                },
                "output_dir": {
                    "type": "string",
                    "description": "Target directory for writing train/val/test splits",
                },
                "train_ratio": {
                    "type": "number",
                    "description": "Train partition ratio (default: 0.8)",
                },
                "val_ratio": {
                    "type": "number",
                    "description": "Validation partition ratio (default: 0.1)",
                },
                "test_ratio": {
                    "type": "number",
                    "description": "Test partition ratio (default: 0.1)",
                },
                "stratify_column": {
                    "type": "string",
                    "description": "Column name to stratify class distributions when splitting",
                },
                "dataset_name": {
                    "type": "string",
                    "description": "Identifier name for registering in Knowledge Graph",
                },
                "description": {
                    "type": "string",
                    "description": "Research notes or description of the dataset",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Categorization tags",
                },
            },
            "required": ["operation"],
        },
        handler=_handle_datasets,
    )
