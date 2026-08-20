"""Datasets tool — dataset profiling, inspection, validation, and curation for AI research agents."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Callable

from ..agent.types import ToolSpec
from ..services.dataset_profiler import DatasetProfile, DatasetProfiler

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


def _format_profile_markdown(file_path: Path, profile: DatasetProfile) -> str:
    """Format DatasetProfile into human-readable markdown."""
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
    return "\n".join(output)


def _resolve_target_file(path: str) -> Path | None:
    if not path:
        return None
    p = Path(path).resolve()
    return p if p.exists() else None


def _op_profile(path: str, kwargs: dict[str, Any]) -> tuple[str, bool]:
    file_path = _resolve_target_file(path)
    if not file_path:
        return f"Error: Dataset file not found at '{path}'.", False
    sample_size = int(kwargs.get("sample_size", 2000))
    profile = DatasetProfiler.profile(file_path, sample_size=sample_size)
    return _format_profile_markdown(file_path, profile), True


def _op_inspect(path: str, kwargs: dict[str, Any]) -> tuple[str, bool]:
    file_path = _resolve_target_file(path)
    if not file_path:
        return f"Error: Dataset file not found at '{path}'.", False
    strategy = str(kwargs.get("strategy", "head"))
    samples = DatasetProfiler.sample_records(
        file_path,
        n=int(kwargs.get("n", 5)),
        offset=int(kwargs.get("offset", 0)),
        strategy=strategy,
        label_column=kwargs.get("label_column"),
    )
    output = [
        f"# Dataset Samples: {file_path.name} (strategy={strategy}, n={len(samples)})",
        "```json",
        json.dumps(samples, indent=2, default=str),
        "```",
    ]
    return "\n".join(output), True


def _op_validate(path: str, kwargs: dict[str, Any]) -> tuple[str, bool]:
    file_path = _resolve_target_file(path)
    if not file_path:
        return f"Error: Dataset file not found at '{path}'.", False
    exp_cols = _parse_list(kwargs.get("expected_columns")) if kwargs.get("expected_columns") else None
    val_res = DatasetProfiler.validate_dataset(
        file_path,
        expected_columns=exp_cols,
        max_null_pct=float(kwargs.get("max_null_pct", 20.0)),
        max_token_length=kwargs.get("max_token_length"),
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


def _op_split(path: str, kwargs: dict[str, Any]) -> tuple[str, bool]:
    file_path = _resolve_target_file(path)
    if not file_path:
        return f"Error: Dataset file not found at '{path}'.", False
    out_dir_param = str(kwargs.get("output_dir", ""))
    target_dir = out_dir_param or str(file_path.parent / f"{file_path.stem}_splits")
    manifest = DatasetProfiler.split_dataset(
        file_path,
        output_dir=target_dir,
        train_ratio=float(kwargs.get("train_ratio", 0.8)),
        val_ratio=float(kwargs.get("val_ratio", 0.1)),
        test_ratio=float(kwargs.get("test_ratio", 0.1)),
        stratify_column=kwargs.get("stratify_column"),
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


def _sync_kg(session: Any, name: str, file_path: Path | None, profile: DatasetProfile | None, description: str, tags: Any) -> bool:
    kg = getattr(getattr(session, "workspace", None), "knowledge_graph", None)
    if not kg:
        return False
    props = {
        "path": str(file_path) if file_path else "",
        "format": profile.format if profile else "",
        "total_rows": profile.total_rows if profile else 0,
        "health_score": profile.health_score if profile else 100,
        "description": description,
        "tags": _parse_list(tags) if tags else [],
    }
    kg.add_entity(
        entity_id=f"dataset_{name}",
        entity_type="dataset",
        name=name,
        properties=props,
    )
    return True


def _op_register(path: str, kwargs: dict[str, Any]) -> tuple[str, bool]:
    file_path = _resolve_target_file(path) if path else None
    dataset_name = str(kwargs.get("dataset_name", ""))
    description = str(kwargs.get("description", ""))
    tags = kwargs.get("tags")
    session = kwargs.get("session")

    name = dataset_name or (file_path.stem if file_path else "dataset")
    profile = DatasetProfiler.profile(file_path, sample_size=1000) if file_path else None
    kg_synced = _sync_kg(session, name, file_path, profile, description, tags)

    output = [
        f"# Dataset Registered: `{name}`",
        f"- **Path**: `{file_path or path or 'N/A'}`",
        f"- **Knowledge Graph Synced**: {'Yes' if kg_synced else 'No (in-memory only)'}",
        f"- **Description**: {description or 'N/A'}",
    ]
    return "\n".join(output), True


def _op_summary(_path: str, _kwargs: dict[str, Any]) -> tuple[str, bool]:
    return (
        "Datasets Tool Operations:\n"
        "- `profile`: Compute statistics, column distributions, null analysis, text token lengths, and health score.\n"
        "- `inspect_samples`: Preview sample records (head, random, stratified).\n"
        "- `validate`: Validate against schema constraints, missing values, and token limits.\n"
        "- `split`: Partition dataset into train/val/test splits.\n"
        "- `register`: Register dataset in project Knowledge Graph."
    ), True


_OP_HANDLERS: dict[str, Callable[[str, dict[str, Any]], tuple[str, bool]]] = {
    "profile": _op_profile,
    "analyze": _op_profile,
    "inspect_samples": _op_inspect,
    "sample": _op_inspect,
    "preview": _op_inspect,
    "validate": _op_validate,
    "check": _op_validate,
    "split": _op_split,
    "partition": _op_split,
    "register": _op_register,
    "register_kg": _op_register,
    "summary": _op_summary,
    "help": _op_summary,
}


async def _handle_datasets(
    operation: str = "",
    path: str = "",
    **kwargs: Any,
) -> tuple[str, bool]:
    """Handle dataset profiling, inspection, validation, split, and registration operations."""
    await asyncio.sleep(0)
    op = (operation or "").strip().lower()

    if not path and op not in ("summary", "help"):
        return "Error: 'path' parameter is required for dataset operations.", False

    handler = _OP_HANDLERS.get(op)
    if not handler:
        return (
            f"Unknown datasets operation '{operation}'. Supported: profile, inspect_samples, validate, split, register, summary.",
            False,
        )

    try:
        return handler(path, kwargs)
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
