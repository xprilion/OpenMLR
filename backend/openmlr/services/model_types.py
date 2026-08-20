"""Model registry and governance domain types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field

FrameworkType = Literal["pytorch", "safetensors", "jax", "onnx", "gguf", "huggingface", "tensorrt"]
TaskType = Literal[
    "causal_lm",
    "seq2seq",
    "classification",
    "object_detection",
    "segmentation",
    "diffusion",
    "embedding",
    "reinforcement_learning",
    "custom",
]
ModelStatus = Literal["draft", "training", "evaluated", "production", "archived"]
PrecisionType = Literal["fp32", "fp16", "bf16", "int8", "int4", "fp8", "mixed"]


@dataclass
class LayerSummary:
    name: str
    param_count: int
    dtype: str
    trainable: bool = True
    shape: list[int] = field(default_factory=list)


@dataclass
class CheckpointInspection:
    file_format: str
    total_parameters: int
    trainable_parameters: int
    total_size_mb: float
    estimated_vram_fp32_mb: float
    estimated_vram_fp16_mb: float
    estimated_vram_int8_mb: float
    estimated_vram_int4_mb: float
    dtype_breakdown: dict[str, int] = field(default_factory=dict)
    layers_count: int = 0
    top_layers: list[dict[str, Any]] = field(default_factory=list)
    has_optimizer_state: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class QuantizationEstimate:
    target_precision: str
    estimated_size_mb: float
    estimated_vram_mb: float
    compression_ratio: float
    expected_latency_speedup: float
    suggested_engine: str
    loss_tolerance_level: str


@dataclass
class ModelCardContent:
    model_name: str
    version: str
    markdown: str
    latex: str
    bibtex: str
    co2_emissions_kg: float
    summary: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelArtifact:
    id: str
    project_id: str
    name: str
    version: str
    architecture: str
    framework: FrameworkType
    task_type: TaskType
    status: ModelStatus
    created_at: str
    updated_at: str
    description: str = ""
    parameters_count: int = 0
    model_size_mb: float = 0.0
    checkpoint_path: str = ""
    base_model: str = ""
    tags: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    hyperparameters: dict[str, Any] = field(default_factory=dict)
    lineage: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "version": self.version,
            "architecture": self.architecture,
            "framework": self.framework,
            "task_type": self.task_type,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "description": self.description,
            "parameters_count": self.parameters_count,
            "model_size_mb": self.model_size_mb,
            "checkpoint_path": self.checkpoint_path,
            "base_model": self.base_model,
            "tags": list(self.tags),
            "metrics": dict(self.metrics),
            "hyperparameters": dict(self.hyperparameters),
            "lineage": dict(self.lineage),
            "metadata": dict(self.metadata),
        }


# Pydantic Schemas for API Requests & Responses

class RegisterModelRequest(BaseModel):
    name: str
    version: str = "1.0.0"
    architecture: str = "Transformer"
    framework: FrameworkType = "pytorch"
    task_type: TaskType = "causal_lm"
    status: ModelStatus = "evaluated"
    description: str = ""
    parameters_count: int = 0
    model_size_mb: float = 0.0
    checkpoint_path: str = ""
    base_model: str = ""
    tags: list[str] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)
    hyperparameters: dict[str, Any] = Field(default_factory=dict)
    lineage: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpdateModelRequest(BaseModel):
    name: str | None = None
    version: str | None = None
    status: ModelStatus | None = None
    description: str | None = None
    parameters_count: int | None = None
    model_size_mb: float | None = None
    checkpoint_path: str | None = None
    tags: list[str] | None = None
    metrics: dict[str, float] | None = None
    hyperparameters: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class InspectCheckpointRequest(BaseModel):
    checkpoint_path: str = Field("", max_length=500)
    parameters_count: int = Field(0, ge=0)
    model_size_mb: float = Field(0.0, ge=0.0)
    framework: str = "pytorch"
    layer_samples: list[dict[str, Any]] = Field(default_factory=list)


class GenerateModelCardRequest(BaseModel):
    include_carbon_estimate: bool = True
    author: str = "OpenMLR Research Agent"
    license: str = "Apache-2.0"
    intended_use: str = ""
    limitations: str = ""
    evaluation_notes: str = ""
    gpu_hours: float = Field(24.0, ge=0.0)
    gpu_type: str = "NVIDIA A100-SXM4-80GB"


class PlanQuantizationRequest(BaseModel):
    target_precisions: list[str] = Field(default_factory=lambda: ["fp16", "int8", "int4", "fp8"])


class CompareModelsRequest(BaseModel):
    model_ids: list[str] = Field(..., min_length=2, max_length=10)
