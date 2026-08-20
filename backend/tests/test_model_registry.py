"""Tests for Model Registry Service, Model Card Generator, Checkpoint Inspection, and Quantization."""

import pytest

from openmlr.services.model_card_generator import (
    estimate_carbon_footprint,
)
from openmlr.services.model_registry import ModelRegistryService
from openmlr.services.model_types import (
    GenerateModelCardRequest,
    InspectCheckpointRequest,
    RegisterModelRequest,
    UpdateModelRequest,
)


@pytest.fixture(autouse=True)
def clean_registry():
    ModelRegistryService._models_store.clear()
    yield
    ModelRegistryService._models_store.clear()


def test_register_and_get_model():
    req = RegisterModelRequest(
        name="Llama-3-8B-OpenMLR",
        version="1.0.0",
        architecture="LLaMA-3",
        framework="safetensors",
        task_type="causal_lm",
        status="evaluated",
        description="Fine-tuned research model for theorem proving.",
        parameters_count=8_000_000_000,
        model_size_mb=16000.0,
        checkpoint_path="/checkpoints/llama3_8b.safetensors",
        tags=["research", "reasoning", "llm"],
        metrics={"val_loss": 1.12, "gsm8k_acc": 0.78},
        hyperparameters={"lr": 2e-5, "batch_size": 64, "warmup_steps": 100},
    )
    artifact = ModelRegistryService.register_model("proj_1", req)
    assert artifact.id.startswith("model_")
    assert artifact.name == "Llama-3-8B-OpenMLR"
    assert artifact.parameters_count == 8_000_000_000
    assert artifact.metrics["gsm8k_acc"] == 0.78

    retrieved = ModelRegistryService.get_model("proj_1", artifact.id)
    assert retrieved is not None
    assert retrieved.id == artifact.id
    assert retrieved.architecture == "LLaMA-3"


def test_list_and_filter_models():
    req1 = RegisterModelRequest(name="Model-A", framework="pytorch", task_type="classification", tags=["vision"])
    req2 = RegisterModelRequest(name="Model-B", framework="safetensors", task_type="causal_lm", tags=["nlp"])
    req3 = RegisterModelRequest(name="Model-C", framework="onnx", task_type="classification", tags=["vision"])

    ModelRegistryService.register_model("proj_filter", req1)
    ModelRegistryService.register_model("proj_filter", req2)
    ModelRegistryService.register_model("proj_filter", req3)

    all_models = ModelRegistryService.list_models("proj_filter")
    assert len(all_models) == 3

    vision_models = ModelRegistryService.list_models("proj_filter", tag="vision")
    assert len(vision_models) == 2

    nlp_models = ModelRegistryService.list_models("proj_filter", task_type="causal_lm")
    assert len(nlp_models) == 1
    assert nlp_models[0].name == "Model-B"


def test_update_and_delete_model():
    req = RegisterModelRequest(name="Model-To-Update", status="training")
    artifact = ModelRegistryService.register_model("proj_update", req)

    update_req = UpdateModelRequest(
        status="production",
        metrics={"accuracy": 0.95},
        description="Production candidate",
    )
    updated = ModelRegistryService.update_model("proj_update", artifact.id, update_req)
    assert updated is not None
    assert updated.status == "production"
    assert updated.metrics["accuracy"] == 0.95
    assert updated.description == "Production candidate"

    deleted = ModelRegistryService.delete_model("proj_update", artifact.id)
    assert deleted is True
    assert ModelRegistryService.get_model("proj_update", artifact.id) is None


def test_inspect_checkpoint():
    req = InspectCheckpointRequest(
        checkpoint_path="model.safetensors",
        parameters_count=7_000_000_000,
        model_size_mb=14000.0,
        framework="safetensors",
    )
    inspection = ModelRegistryService.inspect_checkpoint(req)
    assert inspection.file_format == "safetensors"
    assert inspection.total_parameters == 7_000_000_000
    assert inspection.estimated_vram_fp16_mb > 0
    assert inspection.estimated_vram_int4_mb < inspection.estimated_vram_fp16_mb


def test_plan_quantization():
    req = RegisterModelRequest(
        name="Mistral-7B",
        parameters_count=7_000_000_000,
        model_size_mb=14000.0,
    )
    artifact = ModelRegistryService.register_model("proj_quant", req)

    plans = ModelRegistryService.plan_quantization(artifact, ["fp16", "int8", "int4", "fp8"])
    assert len(plans) == 4
    precisions = [p.target_precision for p in plans]
    assert "FP16" in precisions
    assert "INT4" in precisions

    int4_plan = next(p for p in plans if p.target_precision == "INT4")
    assert int4_plan.compression_ratio > 5.0
    assert int4_plan.expected_latency_speedup > 2.0


def test_model_card_generator_and_carbon():
    req = RegisterModelRequest(
        name="GPT-Nano-Ablation",
        version="2.1.0",
        architecture="Transformer",
        parameters_count=125_000_000,
        model_size_mb=500.0,
        metrics={"val_loss": 2.45, "hellaswag": 0.42},
        hyperparameters={"lr": 6e-4, "n_layer": 12, "n_head": 12},
    )
    artifact = ModelRegistryService.register_model("proj_card", req)

    card_req = GenerateModelCardRequest(
        author="Silas Autonomous Agent",
        license="MIT",
        intended_use="Language modeling ablation benchmark",
        limitations="Small parameter capacity, limited world knowledge.",
        gpu_type="NVIDIA A100",
        gpu_hours=48.0,
    )
    card = ModelRegistryService.generate_model_card("proj_card", artifact.id, card_req)
    assert card is not None
    assert card.model_name == "GPT-Nano-Ablation"
    assert "GPT-Nano-Ablation" in card.markdown
    assert "\\begin{table}" in card.latex
    assert "@misc{" in card.bibtex
    assert card.co2_emissions_kg > 0

    carbon = estimate_carbon_footprint("NVIDIA H100", 10.0)
    assert carbon > 0


def test_compare_models():
    m1 = ModelRegistryService.register_model(
        "proj_comp",
        RegisterModelRequest(
            name="Baseline-Model",
            version="1.0.0",
            parameters_count=100_000_000,
            model_size_mb=400.0,
            metrics={"val_loss": 2.8, "accuracy": 0.70},
        ),
    )
    m2 = ModelRegistryService.register_model(
        "proj_comp",
        RegisterModelRequest(
            name="Novel-Attention-Model",
            version="1.1.0",
            parameters_count=105_000_000,
            model_size_mb=420.0,
            metrics={"val_loss": 2.1, "accuracy": 0.85},
        ),
    )

    comp = ModelRegistryService.compare_models("proj_comp", [m1.id, m2.id])
    assert "compared_models" in comp
    assert len(comp["compared_models"]) == 2
    assert comp["recommended_model_id"] == m2.id
    assert "Novel-Attention-Model" in comp["recommendation_reason"]
