"""Tests for Models Agent Tool Spec & Actions."""

import pytest
from openmlr.tools.models import create_models_tool
from openmlr.services.model_registry import ModelRegistryService


@pytest.fixture(autouse=True)
def clean_registry():
    ModelRegistryService._models_store.clear()
    yield
    ModelRegistryService._models_store.clear()


@pytest.mark.asyncio
async def test_tool_register_and_list():
    tool = create_models_tool()
    assert tool.handler is not None
    res, ok = await tool.handler(
        action="register",
        project_id="test_proj",
        name="BERT-Base-OpenMLR",
        version="1.0.0",
        architecture="Encoder",
        framework="pytorch",
        parameters_count=110_000_000,
        model_size_mb=440.0,
        metrics={"f1": 0.89},
    )
    assert ok is True
    assert "registered successfully" in res
    assert "BERT-Base-OpenMLR" in res

    # List models
    list_res, list_ok = await tool.handler(action="list", project_id="test_proj")
    assert list_ok is True
    assert "BERT-Base-OpenMLR" in list_res


@pytest.mark.asyncio
async def test_tool_checkpoint_inspection():
    tool = create_models_tool()
    assert tool.handler is not None
    res, ok = await tool.handler(
        action="inspect_checkpoint",
        checkpoint_path="weights.safetensors",
        parameters_count=7_000_000_000,
    )
    assert ok is True
    assert "Checkpoint Inspection Report" in res
    assert "Estimated VRAM" in res


@pytest.mark.asyncio
async def test_tool_generate_card_and_quant():
    tool = create_models_tool()
    assert tool.handler is not None
    # Register first
    await tool.handler(
        action="register",
        project_id="p_tool",
        name="ViT-Base-224",
        parameters_count=86_000_000,
        metrics={"top1_acc": 0.84},
    )
    models = ModelRegistryService.list_models("p_tool")
    mid = models[0].id

    # Generate card
    card_res, card_ok = await tool.handler(
        action="generate_card",
        project_id="p_tool",
        model_id=mid,
        author="Silas",
    )
    assert card_ok is True
    assert "# Model Card: ViT-Base-224" in card_res

    # Quantization planning
    quant_res, quant_ok = await tool.handler(
        action="plan_quantization",
        project_id="p_tool",
        model_id=mid,
        target_precisions=["fp16", "int8", "int4"],
    )
    assert quant_ok is True
    assert "INT4" in quant_res


@pytest.mark.asyncio
async def test_tool_compare():
    tool = create_models_tool()
    assert tool.handler is not None
    await tool.handler(action="register", project_id="p_comp", name="Model-1", metrics={"accuracy": 0.80})
    await tool.handler(action="register", project_id="p_comp", name="Model-2", metrics={"accuracy": 0.90})

    models = ModelRegistryService.list_models("p_comp")
    res, ok = await tool.handler(
        action="compare",
        project_id="p_comp",
        model_ids=[models[0].id, models[1].id],
    )
    assert ok is True
    assert "Model Comparison Analysis" in res
