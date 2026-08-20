"""Unit tests for the Ablation Agent Tool."""

import json

import pytest

from openmlr.tools.ablation import create_ablation_tool


@pytest.mark.asyncio
async def test_ablation_tool_lifecycle():
    tool = create_ablation_tool(get_project_context=lambda: "proj_tool_test")
    assert tool.name == "ablation"
    assert tool.handler is not None

    # 1. Create study
    raw_res, ok = await tool.handler(
        action="create_study",
        title="Optimizer Ablation Study",
        primary_metric="val_loss",
        higher_is_better=False,
        baseline_variant_name="AdamW+Cosine",
    )
    assert ok is True
    res = json.loads(raw_res)
    assert res["status"] == "success"
    study_id = res["study"]["id"]

    # 2. Record Baseline runs
    raw_b, ok_b = await tool.handler(
        action="record_variant_runs",
        study_id=study_id,
        variant_name="AdamW+Cosine",
        variant_type="baseline",
        metrics={"val_loss": [1.42, 1.41, 1.43, 1.40, 1.42]},
    )
    assert ok_b is True

    # 3. Record Ablation runs
    raw_v, ok_v = await tool.handler(
        action="record_variant_runs",
        study_id=study_id,
        variant_name="SGD+Constant",
        variant_type="ablation",
        removed_components=["Cosine Annealing", "AdamW Moments"],
        metrics={"val_loss": [1.95, 1.98, 1.92, 1.96, 1.94]},
    )
    assert ok_v is True

    # 4. Analyze significance
    raw_a, ok_a = await tool.handler(
        action="analyze_significance",
        study_id=study_id,
    )
    assert ok_a is True
    res_a = json.loads(raw_a)
    assert len(res_a["study"]["component_impacts"]) >= 1

    # 5. Generate LaTeX Table
    raw_l, ok_l = await tool.handler(
        action="generate_latex_table",
        study_id=study_id,
    )
    assert ok_l is True
    res_l = json.loads(raw_l)
    assert "\\begin{table}" in res_l["latex_table"]

    # 6. List and Get
    raw_list, ok_list = await tool.handler(action="list_studies")
    assert ok_list is True
    assert json.loads(raw_list)["count"] >= 1

    raw_get, ok_get = await tool.handler(action="get_study", study_id=study_id)
    assert ok_get is True
    assert json.loads(raw_get)["study"]["id"] == study_id
