"""REST API routes for Model Registry, Checkpoint Governance, and Model Cards."""

from __future__ import annotations

import logging
from typing import Any
from fastapi import APIRouter, HTTPException, Query, status

from ..services.model_types import (
    RegisterModelRequest,
    UpdateModelRequest,
    InspectCheckpointRequest,
    GenerateModelCardRequest,
    PlanQuantizationRequest,
    CompareModelsRequest,
)
from ..services.model_registry import ModelRegistryService

router = APIRouter(prefix="/api/model-registry", tags=["model-registry"])
logger = logging.getLogger("openmlr.routes.models")


PROJECT_ID_DESC = "Project ID"


@router.get("")
async def list_models(
    project_id: str = Query("default", description=PROJECT_ID_DESC),
    task_type: str | None = Query(None, description="Filter by task type"),
    framework: str | None = Query(None, description="Filter by framework"),
    status: str | None = Query(None, description="Filter by status"),
    tag: str | None = Query(None, description="Filter by tag"),
) -> dict[str, Any]:
    """List all registered model artifacts for a project."""
    models = ModelRegistryService.list_models(
        project_id=project_id,
        task_type=task_type,
        framework=framework,
        status=status,
        tag=tag,
    )
    return {
        "models": [m.to_dict() for m in models],
        "total_count": len(models),
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def register_model(
    request: RegisterModelRequest,
    project_id: str = Query("default", description=PROJECT_ID_DESC),
) -> dict[str, Any]:
    """Register a new model artifact."""
    artifact = ModelRegistryService.register_model(project_id, request)
    return {
        "model": artifact.to_dict(),
        "message": f"Model artifact '{artifact.name}' (v{artifact.version}) registered successfully.",
    }


@router.get("/{model_id}")
async def get_model(
    model_id: str,
    project_id: str = Query("default", description=PROJECT_ID_DESC),
) -> dict[str, Any]:
    """Get full details of a registered model artifact."""
    artifact = ModelRegistryService.get_model(project_id, model_id)
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model artifact '{model_id}' not found.",
        )
    return {"model": artifact.to_dict()}


@router.put("/{model_id}")
async def update_model(
    model_id: str,
    request: UpdateModelRequest,
    project_id: str = Query("default", description=PROJECT_ID_DESC),
) -> dict[str, Any]:
    """Update metadata and properties of a model artifact."""
    artifact = ModelRegistryService.update_model(project_id, model_id, request)
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model artifact '{model_id}' not found.",
        )
    return {
        "model": artifact.to_dict(),
        "message": f"Model artifact '{artifact.name}' updated successfully.",
    }


@router.delete("/{model_id}")
async def delete_model(
    model_id: str,
    project_id: str = Query("default", description=PROJECT_ID_DESC),
) -> dict[str, Any]:
    """Delete a model artifact from the registry."""
    success = ModelRegistryService.delete_model(project_id, model_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model artifact '{model_id}' not found.",
        )
    return {
        "success": True,
        "message": f"Model artifact '{model_id}' deleted successfully.",
    }


@router.post("/{model_id}/card")
async def generate_model_card(
    model_id: str,
    request: GenerateModelCardRequest,
    project_id: str = Query("default", description=PROJECT_ID_DESC),
) -> dict[str, Any]:
    """Generate a multi-format Model Card (Markdown, LaTeX, BibTeX, Carbon)."""
    card = ModelRegistryService.generate_model_card(project_id, model_id, request)
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model artifact '{model_id}' not found.",
        )
    return {
        "model_name": card.model_name,
        "version": card.version,
        "markdown": card.markdown,
        "latex": card.latex,
        "bibtex": card.bibtex,
        "co2_emissions_kg": card.co2_emissions_kg,
        "summary": card.summary,
    }


@router.post("/{model_id}/quantization")
async def plan_quantization(
    model_id: str,
    request: PlanQuantizationRequest,
    project_id: str = Query("default", description=PROJECT_ID_DESC),
) -> dict[str, Any]:
    """Calculate quantization trade-offs and memory savings for target precisions."""
    artifact = ModelRegistryService.get_model(project_id, model_id)
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model artifact '{model_id}' not found.",
        )
    estimates = ModelRegistryService.plan_quantization(artifact, request.target_precisions)
    return {
        "model_id": artifact.id,
        "model_name": artifact.name,
        "base_parameters": artifact.parameters_count,
        "estimates": [
            {
                "target_precision": e.target_precision,
                "estimated_size_mb": e.estimated_size_mb,
                "estimated_vram_mb": e.estimated_vram_mb,
                "compression_ratio": e.compression_ratio,
                "expected_latency_speedup": e.expected_latency_speedup,
                "suggested_engine": e.suggested_engine,
                "loss_tolerance_level": e.loss_tolerance_level,
            }
            for e in estimates
        ],
    }


@router.post("/inspect")
async def inspect_checkpoint(request: InspectCheckpointRequest) -> dict[str, Any]:
    """Inspect checkpoint structure, layer breakdown, and memory requirements."""
    inspection = ModelRegistryService.inspect_checkpoint(request)
    return {
        "file_format": inspection.file_format,
        "total_parameters": inspection.total_parameters,
        "trainable_parameters": inspection.trainable_parameters,
        "total_size_mb": inspection.total_size_mb,
        "estimated_vram_fp32_mb": inspection.estimated_vram_fp32_mb,
        "estimated_vram_fp16_mb": inspection.estimated_vram_fp16_mb,
        "estimated_vram_int8_mb": inspection.estimated_vram_int8_mb,
        "estimated_vram_int4_mb": inspection.estimated_vram_int4_mb,
        "dtype_breakdown": inspection.dtype_breakdown,
        "layers_count": inspection.layers_count,
        "top_layers": inspection.top_layers,
        "has_optimizer_state": inspection.has_optimizer_state,
        "metadata": inspection.metadata,
    }


@router.post("/compare")
async def compare_models(
    request: CompareModelsRequest,
    project_id: str = Query("default", description=PROJECT_ID_DESC),
) -> dict[str, Any]:
    """Compare multiple model artifacts side-by-side."""
    comparison = ModelRegistryService.compare_models(project_id, request.model_ids)
    if "error" in comparison:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=comparison["error"],
        )
    return comparison
