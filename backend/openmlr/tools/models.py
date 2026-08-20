"""Agent tool for Model Registry, Checkpoint Governance, Model Card generation, and Quantization."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

from ..agent.types import ToolSpec
from ..services.model_registry import ModelRegistryService
from ..services.model_types import (
    GenerateModelCardRequest,
    InspectCheckpointRequest,
    RegisterModelRequest,
)

log = logging.getLogger("openmlr.tools.models")


def _resolve_project_id(explicit_proj: str | None, getter: Callable[[], str | None] | None) -> str:
    if explicit_proj and explicit_proj.strip():
        return explicit_proj.strip()
    if getter:
        val = getter()
        if val and val.strip():
            return val.strip()
    return "default"


def _parse_dict(val: Any) -> dict[str, Any]:
    if isinstance(val, dict):
        return val
    if isinstance(val, str) and val.strip():
        try:
            parsed = json.loads(val)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    return {}


def _handle_register(proj: str, kwargs: dict[str, Any]) -> tuple[str, bool]:
    name = kwargs.get("name")
    if not name:
        return "Error: Field `name` is required for registering a model.", False

    req = RegisterModelRequest(
        name=name,
        version=kwargs.get("version", "1.0.0"),
        architecture=kwargs.get("architecture", "Transformer"),
        framework=kwargs.get("framework", "pytorch"),  # type: ignore
        task_type=kwargs.get("task_type", "causal_lm"),  # type: ignore
        status=kwargs.get("status", "evaluated"),  # type: ignore
        description=kwargs.get("description", ""),
        parameters_count=int(kwargs.get("parameters_count", 0)),
        model_size_mb=float(kwargs.get("model_size_mb", 0.0)),
        checkpoint_path=kwargs.get("checkpoint_path", ""),
        base_model=kwargs.get("base_model", ""),
        tags=kwargs.get("tags") or [],
        metrics=_parse_dict(kwargs.get("metrics")),
        hyperparameters=_parse_dict(kwargs.get("hyperparameters")),
        lineage=_parse_dict(kwargs.get("lineage")),
    )
    artifact = ModelRegistryService.register_model(proj, req)
    msg = (
        f"✅ Model artifact '{artifact.name}' (v{artifact.version}) registered successfully!\n"
        f"- Model ID: `{artifact.id}`\n"
        f"- Architecture: `{artifact.architecture}` ({artifact.framework})\n"
        f"- Parameters: {artifact.parameters_count:,}\n"
        f"- Size: {artifact.model_size_mb:.2f} MB\n"
        f"- Status: `{artifact.status}`\n"
        f"- Metrics: {json.dumps(artifact.metrics)}"
    )
    return msg, True


def _handle_list(proj: str, kwargs: dict[str, Any]) -> tuple[str, bool]:
    models = ModelRegistryService.list_models(
        project_id=proj,
        task_type=kwargs.get("task_type"),
        framework=kwargs.get("framework"),
        status=kwargs.get("status"),
    )
    if not models:
        return f"No model artifacts registered in project `{proj}`.", True
    lines = [f"Found {len(models)} model artifacts in project `{proj}`:"]
    for m in models:
        lines.append(
            f"- **{m.name}** (v{m.version}, `{m.id}`): {m.architecture} | {m.parameters_count:,} params | {m.model_size_mb:.1f} MB | status: {m.status}"
        )
    return "\n".join(lines), True


def _handle_get(proj: str, kwargs: dict[str, Any]) -> tuple[str, bool]:
    model_id = kwargs.get("model_id")
    if not model_id:
        return "Error: `model_id` is required for get action.", False
    m = ModelRegistryService.get_model(proj, model_id)
    if not m:
        return f"Error: Model artifact `{model_id}` not found in project `{proj}`.", False
    msg = (
        f"### Model Artifact: {m.name} (v{m.version})\n"
        f"- **ID:** `{m.id}`\n"
        f"- **Architecture:** {m.architecture} ({m.framework})\n"
        f"- **Task Type:** {m.task_type}\n"
        f"- **Status:** {m.status}\n"
        f"- **Parameters:** {m.parameters_count:,}\n"
        f"- **Disk Size:** {m.model_size_mb:.2f} MB\n"
        f"- **Checkpoint Path:** `{m.checkpoint_path or 'N/A'}`\n"
        f"- **Base Model:** `{m.base_model or 'Trained from scratch'}`\n"
        f"- **Metrics:** {json.dumps(m.metrics, indent=2)}\n"
        f"- **Hyperparameters:** {json.dumps(m.hyperparameters, indent=2)}"
    )
    return msg, True


def _handle_inspect_checkpoint(kwargs: dict[str, Any]) -> tuple[str, bool]:
    req = InspectCheckpointRequest(
        checkpoint_path=kwargs.get("checkpoint_path", ""),
        parameters_count=int(kwargs.get("parameters_count", 0)),
        model_size_mb=float(kwargs.get("model_size_mb", 0.0)),
        framework=kwargs.get("framework", "pytorch"),
    )
    insp = ModelRegistryService.inspect_checkpoint(req)
    msg = (
        f"### Checkpoint Inspection Report\n"
        f"- **Format:** `{insp.file_format}`\n"
        f"- **Total Parameters:** {insp.total_parameters:,}\n"
        f"- **Total Disk Size:** {insp.total_size_mb:.2f} MB\n"
        f"- **Estimated VRAM (FP32):** {insp.estimated_vram_fp32_mb:.1f} MB\n"
        f"- **Estimated VRAM (FP16/BF16):** {insp.estimated_vram_fp16_mb:.1f} MB\n"
        f"- **Estimated VRAM (INT8):** {insp.estimated_vram_int8_mb:.1f} MB\n"
        f"- **Estimated VRAM (INT4):** {insp.estimated_vram_int4_mb:.1f} MB\n"
        f"- **Layers Count:** {insp.layers_count}"
    )
    return msg, True


def _handle_generate_card(proj: str, kwargs: dict[str, Any]) -> tuple[str, bool]:
    model_id = kwargs.get("model_id")
    if not model_id:
        return "Error: `model_id` is required for generate_card action.", False
    card_req = GenerateModelCardRequest(
        author=kwargs.get("author", "OpenMLR Research Agent"),
        license=kwargs.get("license", "Apache-2.0"),
        intended_use=kwargs.get("intended_use", ""),
        limitations=kwargs.get("limitations", ""),
        evaluation_notes=kwargs.get("evaluation_notes", ""),
        gpu_type=kwargs.get("gpu_type", "NVIDIA A100-SXM4-80GB"),
        gpu_hours=float(kwargs.get("gpu_hours", 24.0)),
    )
    card = ModelRegistryService.generate_model_card(proj, model_id, card_req)
    if not card:
        return f"Error: Model artifact `{model_id}` not found in project `{proj}`.", False
    return card.markdown, True


def _handle_plan_quantization(proj: str, kwargs: dict[str, Any]) -> tuple[str, bool]:
    model_id = kwargs.get("model_id")
    if not model_id:
        return "Error: `model_id` is required for plan_quantization action.", False
    model = ModelRegistryService.get_model(proj, model_id)
    if not model:
        return f"Error: Model artifact `{model_id}` not found in project `{proj}`.", False
    targets = kwargs.get("target_precisions") or ["fp16", "bf16", "fp8", "int8", "int4"]
    estimates = ModelRegistryService.plan_quantization(model, targets)
    rows = [
        f"### Quantization Planning for {model.name} ({model.parameters_count:,} params)",
        "| Precision | Est. Size | Est. VRAM | Compression | Speedup | Suggested Engine |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for e in estimates:
        rows.append(
            f"| **{e.target_precision}** | {e.estimated_size_mb:.1f} MB | {e.estimated_vram_mb:.1f} MB | {e.compression_ratio:.1f}x | {e.expected_latency_speedup:.1f}x | {e.suggested_engine} |"
        )
    return "\n".join(rows), True


def _handle_compare(proj: str, kwargs: dict[str, Any]) -> tuple[str, bool]:
    model_ids = kwargs.get("model_ids")
    if not model_ids or len(model_ids) < 2:
        return "Error: `model_ids` requires at least 2 model IDs to compare.", False
    comp = ModelRegistryService.compare_models(proj, model_ids)
    if "error" in comp:
        return f"Error: {comp['error']}", False
    lines = [
        "### Model Comparison Analysis",
        f"- **Recommendation:** {comp['recommendation_reason']}",
        f"- **Recommended ID:** `{comp['recommended_model_id']}`\n",
        "**Parameters & Sizes:**",
    ]
    for m in comp["compared_models"]:
        lines.append(f"- **{m['name']}** (v{m['version']}): {m['parameters_count']:,} params, {m['model_size_mb']:.1f} MB")
    return "\n".join(lines), True


def create_models_tool(get_project_id: Callable[[], str | None] | None = None) -> ToolSpec:
    """Create the 'models' agent tool spec."""

    async def _execute(action: str = "list", **kwargs: Any) -> tuple[str, bool]:
        await asyncio.sleep(0)
        proj = _resolve_project_id(kwargs.get("project_id"), get_project_id)
        act = (action or "list").lower().strip()

        handlers = {
            "register": lambda: _handle_register(proj, kwargs),
            "list": lambda: _handle_list(proj, kwargs),
            "get": lambda: _handle_get(proj, kwargs),
            "inspect_checkpoint": lambda: _handle_inspect_checkpoint(kwargs),
            "generate_card": lambda: _handle_generate_card(proj, kwargs),
            "plan_quantization": lambda: _handle_plan_quantization(proj, kwargs),
            "compare": lambda: _handle_compare(proj, kwargs),
        }

        handler = handlers.get(act)
        if not handler:
            return (
                f"Unknown action: '{action}'. "
                "Allowed actions: `register`, `list`, `get`, `inspect_checkpoint`, `generate_card`, `plan_quantization`, `compare`.",
                False,
            )

        try:
            return handler()
        except Exception as e:
            log.exception("Models tool error: %s", e)
            return f"Error executing models action '{action}': {e}", False

    return ToolSpec(
        name="models",
        description=(
            "Model Registry, Checkpoint Governance, Model Card Generator, and Quantization Planning. "
            "Manage trained model artifacts, generate NeurIPS/HuggingFace model cards, inspect checkpoints, "
            "and compute precision compression tradeoffs."
        ),
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["register", "list", "get", "inspect_checkpoint", "generate_card", "plan_quantization", "compare"],
                    "description": "The model registry action to execute.",
                },
                "project_id": {"type": "string", "description": "Optional project ID override."},
                "model_id": {"type": "string", "description": "Model Artifact ID."},
                "name": {"type": "string", "description": "Model name for registration."},
                "version": {"type": "string", "description": "Semantic version, e.g. 1.0.0."},
                "architecture": {"type": "string", "description": "Model architecture (e.g. Transformer, ResNet-50)."},
                "framework": {"type": "string", "description": "Framework (pytorch, safetensors, jax, onnx, gguf)."},
                "task_type": {"type": "string", "description": "Task type (causal_lm, classification, diffusion, etc.)."},
                "status": {"type": "string", "description": "Model status (draft, training, evaluated, production, archived)."},
                "description": {"type": "string", "description": "Detailed model description."},
                "parameters_count": {"type": "integer", "description": "Total parameter count."},
                "model_size_mb": {"type": "number", "description": "Model artifact size in megabytes."},
                "checkpoint_path": {"type": "string", "description": "Path to checkpoint file."},
                "base_model": {"type": "string", "description": "Base/pretrained model reference."},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Searchable tags."},
                "metrics": {"type": "object", "description": "Evaluation metrics."},
                "hyperparameters": {"type": "object", "description": "Training hyperparameters."},
                "lineage": {"type": "object", "description": "Model lineage provenance."},
                "target_precisions": {"type": "array", "items": {"type": "string"}, "description": "Quantization precisions to evaluate."},
                "model_ids": {"type": "array", "items": {"type": "string"}, "description": "List of model IDs to compare."},
                "gpu_type": {"type": "string", "description": "GPU used for training."},
                "gpu_hours": {"type": "number", "description": "GPU hours spent."},
                "author": {"type": "string", "description": "Model author/organization."},
                "license": {"type": "string", "description": "Model license."},
                "intended_use": {"type": "string", "description": "Intended application and domain."},
                "limitations": {"type": "string", "description": "Known limitations or bias."},
                "evaluation_notes": {"type": "string", "description": "Additional evaluation notes."},
            },
            "required": ["action"],
        },
        handler=_execute,
    )
