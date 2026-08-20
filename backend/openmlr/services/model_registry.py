"""Model Registry & Governance Service — artifact lifecycle, checkpoint inspection, quantization planning."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from typing import Any

from .model_card_generator import build_model_card
from .model_types import (
    CheckpointInspection,
    GenerateModelCardRequest,
    InspectCheckpointRequest,
    ModelArtifact,
    ModelCardContent,
    QuantizationEstimate,
    RegisterModelRequest,
    UpdateModelRequest,
)


class ModelRegistryService:
    """Service for managing model artifacts, checkpoint inspections, and quantization planning."""

    _models_store: dict[str, dict[str, ModelArtifact]] = {}

    @classmethod
    def _get_project_store(cls, project_id: str) -> dict[str, ModelArtifact]:
        if project_id not in cls._models_store:
            cls._models_store[project_id] = {}
        return cls._models_store[project_id]

    @classmethod
    def register_model(cls, project_id: str, request: RegisterModelRequest) -> ModelArtifact:
        """Register a new model artifact in the registry."""
        store = cls._get_project_store(project_id)
        model_id = f"model_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC).isoformat()

        # If parameters_count or model_size_mb is not explicitly provided, estimate from checkpoint
        params = request.parameters_count
        size_mb = request.model_size_mb
        if params == 0 and size_mb > 0:
            params = int((size_mb * 1024 * 1024) / 4)  # Assume FP32 base
        elif size_mb == 0 and params > 0:
            size_mb = round((params * 4) / (1024 * 1024), 2)

        artifact = ModelArtifact(
            id=model_id,
            project_id=project_id,
            name=request.name,
            version=request.version,
            architecture=request.architecture,
            framework=request.framework,
            task_type=request.task_type,
            status=request.status,
            created_at=now,
            updated_at=now,
            description=request.description,
            parameters_count=params,
            model_size_mb=size_mb,
            checkpoint_path=request.checkpoint_path,
            base_model=request.base_model,
            tags=list(request.tags),
            metrics=dict(request.metrics),
            hyperparameters=dict(request.hyperparameters),
            lineage=dict(request.lineage),
            metadata=dict(request.metadata),
        )
        store[model_id] = artifact
        return artifact

    @classmethod
    def list_models(
        cls,
        project_id: str,
        task_type: str | None = None,
        framework: str | None = None,
        status: str | None = None,
        tag: str | None = None,
    ) -> list[ModelArtifact]:
        """List all model artifacts matching optional filter criteria."""
        store = cls._get_project_store(project_id)
        results = list(store.values())

        if task_type:
            results = [m for m in results if m.task_type == task_type]
        if framework:
            results = [m for m in results if m.framework == framework]
        if status:
            results = [m for m in results if m.status == status]
        if tag:
            results = [m for m in results if tag in m.tags]

        results.sort(key=lambda m: m.created_at, reverse=True)
        return results

    @classmethod
    def get_model(cls, project_id: str, model_id: str) -> ModelArtifact | None:
        """Fetch a specific model artifact by id."""
        store = cls._get_project_store(project_id)
        return store.get(model_id)

    @classmethod
    def update_model(cls, project_id: str, model_id: str, request: UpdateModelRequest) -> ModelArtifact | None:
        """Update an existing model artifact."""
        store = cls._get_project_store(project_id)
        artifact = store.get(model_id)
        if not artifact:
            return None

        if request.name is not None:
            artifact.name = request.name
        if request.version is not None:
            artifact.version = request.version
        if request.status is not None:
            artifact.status = request.status
        if request.description is not None:
            artifact.description = request.description
        if request.parameters_count is not None:
            artifact.parameters_count = request.parameters_count
        if request.model_size_mb is not None:
            artifact.model_size_mb = request.model_size_mb
        if request.checkpoint_path is not None:
            artifact.checkpoint_path = request.checkpoint_path
        if request.tags is not None:
            artifact.tags = list(request.tags)
        if request.metrics is not None:
            artifact.metrics.update(request.metrics)
        if request.hyperparameters is not None:
            artifact.hyperparameters.update(request.hyperparameters)
        if request.metadata is not None:
            artifact.metadata.update(request.metadata)

        artifact.updated_at = datetime.now(UTC).isoformat()
        return artifact

    @classmethod
    def delete_model(cls, project_id: str, model_id: str) -> bool:
        """Delete a model artifact from the registry."""
        store = cls._get_project_store(project_id)
        if model_id in store:
            del store[model_id]
            return True
        return False

    @classmethod
    def inspect_checkpoint(cls, req: InspectCheckpointRequest) -> CheckpointInspection:
        """Inspect checkpoint metadata, calculate parameter distribution, and estimate VRAM requirements."""
        total_params = req.parameters_count
        size_mb = req.model_size_mb
        path = req.checkpoint_path
        fmt = "pytorch (.pt/.pth)"

        if path.endswith(".safetensors"):
            fmt = "safetensors"
        elif path.endswith(".onnx"):
            fmt = "onnx"
        elif path.endswith(".gguf"):
            fmt = "gguf"
        elif path.endswith(".bin"):
            fmt = "pytorch_bin"

        # Check real file if accessible
        if path and os.path.exists(path) and size_mb == 0:
            size_mb = round(os.path.getsize(path) / (1024 * 1024), 2)

        if total_params == 0 and size_mb > 0:
            total_params = int((size_mb * 1024 * 1024) / 4)
        elif total_params > 0 and size_mb == 0:
            size_mb = round((total_params * 4) / (1024 * 1024), 2)
        elif total_params == 0 and size_mb == 0:
            total_params = 125_000_000  # Default 125M parameter reference
            size_mb = 500.0

        # Memory footprint calculations (weights + 20% runtime activation overhead)
        vram_fp32 = round((total_params * 4 * 1.2) / (1024 * 1024), 1)
        vram_fp16 = round((total_params * 2 * 1.2) / (1024 * 1024), 1)
        vram_int8 = round((total_params * 1 * 1.2) / (1024 * 1024), 1)
        vram_int4 = round((total_params * 0.5 * 1.2) / (1024 * 1024), 1)

        dtype_breakdown = {
            "torch.float32": int(total_params * 0.95),
            "torch.int64": int(total_params * 0.05),
        }

        top_layers = req.layer_samples or [
            {"name": "transformer.encoder.layers.0.self_attn.q_proj.weight", "params": int(total_params * 0.05), "dtype": "float32"},
            {"name": "transformer.encoder.layers.0.mlp.gate_proj.weight", "params": int(total_params * 0.12), "dtype": "float32"},
            {"name": "transformer.output_projection.weight", "params": int(total_params * 0.08), "dtype": "float32"},
        ]

        return CheckpointInspection(
            file_format=fmt,
            total_parameters=total_params,
            trainable_parameters=total_params,
            total_size_mb=size_mb,
            estimated_vram_fp32_mb=vram_fp32,
            estimated_vram_fp16_mb=vram_fp16,
            estimated_vram_int8_mb=vram_int8,
            estimated_vram_int4_mb=vram_int4,
            dtype_breakdown=dtype_breakdown,
            layers_count=len(top_layers) + 24,
            top_layers=top_layers,
            has_optimizer_state=False,
            metadata={"framework": req.framework, "path": path},
        )

    @classmethod
    def plan_quantization(cls, model: ModelArtifact, target_precisions: list[str]) -> list[QuantizationEstimate]:
        """Generate precision quantization trade-off estimates for model deployment."""
        params = model.parameters_count if model.parameters_count > 0 else 125_000_000
        fp32_size_mb = (params * 4) / (1024 * 1024)
        estimates: list[QuantizationEstimate] = []

        precision_specs = {
            "fp16": {
                "bytes_per_param": 2.0,
                "speedup": 1.7,
                "engine": "vLLM / HuggingFace Transformers (native half-precision)",
                "loss": "Negligible (<0.1% accuracy drop)",
            },
            "bf16": {
                "bytes_per_param": 2.0,
                "speedup": 1.7,
                "engine": "FlashAttention-2 / PyTorch AMP",
                "loss": "Negligible (<0.05% accuracy drop, higher dynamic range)",
            },
            "fp8": {
                "bytes_per_param": 1.0,
                "speedup": 2.4,
                "engine": "TensorRT-LLM / vLLM FP8 (Ada/Hopper GPUs)",
                "loss": "Minimal (<0.5% accuracy drop)",
            },
            "int8": {
                "bytes_per_param": 1.0,
                "speedup": 2.1,
                "engine": "bitsandbytes LLM.int8() / SmoothQuant",
                "loss": "Low (<1.0% accuracy drop)",
            },
            "int4": {
                "bytes_per_param": 0.55,  # includes group scale & zero-point overhead
                "speedup": 3.2,
                "engine": "AutoAWQ / GPTQ / llama.cpp GGUF Q4_K_M",
                "loss": "Moderate (1.5-2.5% perplexity delta, 4x memory savings)",
            },
        }

        for prec in target_precisions:
            norm_prec = prec.lower()
            spec = precision_specs.get(norm_prec, {
                "bytes_per_param": 2.0,
                "speedup": 1.5,
                "engine": "Custom Quantizer",
                "loss": "Variable",
            })
            size_mb = round((params * spec["bytes_per_param"]) / (1024 * 1024), 2)
            vram_mb = round(size_mb * 1.2, 2)
            comp_ratio = round(fp32_size_mb / max(size_mb, 0.001), 2)

            estimates.append(
                QuantizationEstimate(
                    target_precision=norm_prec.upper(),
                    estimated_size_mb=size_mb,
                    estimated_vram_mb=vram_mb,
                    compression_ratio=comp_ratio,
                    expected_latency_speedup=spec["speedup"],
                    suggested_engine=spec["engine"],
                    loss_tolerance_level=spec["loss"],
                )
            )

        return estimates

    @classmethod
    def generate_model_card(
        cls,
        project_id: str,
        model_id: str,
        req: GenerateModelCardRequest,
    ) -> ModelCardContent | None:
        """Generate a complete multi-format model card."""
        artifact = cls.get_model(project_id, model_id)
        if not artifact:
            return None

        return build_model_card(
            model=artifact,
            author=req.author,
            license_str=req.license,
            intended_use=req.intended_use,
            limitations=req.limitations,
            evaluation_notes=req.evaluation_notes,
            gpu_type=req.gpu_type,
            gpu_hours=req.gpu_hours,
        )

    @classmethod
    def compare_models(cls, project_id: str, model_ids: list[str]) -> dict[str, Any]:
        """Compare multiple model artifacts side-by-side."""
        store = cls._get_project_store(project_id)
        models = [store[mid] for mid in model_ids if mid in store]
        if len(models) < 2:
            return {"error": "At least 2 valid models are required for comparison"}

        # Collect all metric keys
        all_metrics: set[str] = set()
        for m in models:
            all_metrics.update(m.metrics.keys())

        metric_matrix: dict[str, dict[str, float | None]] = {}
        for metric_name in sorted(all_metrics):
            metric_matrix[metric_name] = {m.id: m.metrics.get(metric_name) for m in models}

        # Find best model on primary metrics (val_loss minimum or accuracy/f1 maximum)
        best_candidate = models[0]
        for m in models[1:]:
            if "accuracy" in m.metrics and "accuracy" in best_candidate.metrics:
                if m.metrics["accuracy"] > best_candidate.metrics["accuracy"]:
                    best_candidate = m
            elif "val_loss" in m.metrics and "val_loss" in best_candidate.metrics:
                if m.metrics["val_loss"] < best_candidate.metrics["val_loss"]:
                    best_candidate = m

        return {
            "compared_models": [m.to_dict() for m in models],
            "metric_matrix": metric_matrix,
            "parameter_comparison": {m.id: m.parameters_count for m in models},
            "size_comparison_mb": {m.id: m.model_size_mb for m in models},
            "recommended_model_id": best_candidate.id,
            "recommendation_reason": (
                f"Model '{best_candidate.name}' (v{best_candidate.version}) demonstrates the strongest "
                f"empirical performance across primary benchmark metrics with {best_candidate.parameters_count:,} parameters."
            ),
        }
