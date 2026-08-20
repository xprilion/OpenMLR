"""Unit tests for the Reproducibility Agent Tool."""

import json

import pytest

from openmlr.tools.reproducibility import create_reproducibility_tool


@pytest.mark.asyncio
async def test_reproducibility_tool_audit():
    tool = create_reproducibility_tool(get_project_context=lambda: "proj_unit")
    assert tool.name == "reproducibility"
    assert tool.handler is not None

    code_snippets = {
        "main.py": "import torch\ntorch.manual_seed(42)\ntorch.backends.cudnn.deterministic = True\ntorch.save({}, 'model.pt')",
        "requirements.txt": "torch==2.1.0\n",
    }
    raw_res, ok = await tool.handler(
        action="audit",
        code_snippets=code_snippets,
        venue="neurips",
    )
    assert ok is True
    res = json.loads(raw_res)
    assert res["status"] == "success"
    assert "report_id" in res
    assert res["overall_score"] > 50.0
    assert "grade" in res
    assert "checklist_summary" in res


@pytest.mark.asyncio
async def test_reproducibility_tool_generate_dockerfile():
    tool = create_reproducibility_tool()
    assert tool.handler is not None
    raw_res, ok = await tool.handler(
        action="generate_dockerfile",
        framework="pytorch",
        cuda_version="12.2.0",
        requirements=["torch==2.2.0", "numpy==1.26.0"],
    )
    assert ok is True
    res = json.loads(raw_res)
    assert res["status"] == "success"
    assert "FROM nvidia/cuda:12.2.0" in res["dockerfile"]
    assert "torch==2.2.0" in res["dockerfile"]


@pytest.mark.asyncio
async def test_reproducibility_tool_fix_determinism():
    tool = create_reproducibility_tool()
    assert tool.handler is not None
    raw_res, ok = await tool.handler(
        action="fix_determinism",
        framework="pytorch",
        seed=1337,
    )
    assert ok is True
    res = json.loads(raw_res)
    assert res["status"] == "success"
    assert "torch.manual_seed(seed)" in res["determinism_snippet"]
    assert "set_seed(1337)" in res["determinism_snippet"]


@pytest.mark.asyncio
async def test_reproducibility_tool_generate_appendix():
    tool = create_reproducibility_tool()
    assert tool.handler is not None
    raw_res, ok = await tool.handler(
        action="generate_appendix",
        paper_title="Autonomous Agent Paper",
        random_seeds=[42, 100],
    )
    assert ok is True
    res = json.loads(raw_res)
    assert res["status"] == "success"
    assert "\\section{Reproducibility Statement}" in res["latex_appendix"]


@pytest.mark.asyncio
async def test_reproducibility_tool_list_and_unknown():
    tool = create_reproducibility_tool()
    assert tool.handler is not None
    raw_res, ok = await tool.handler(action="list")
    assert ok is True
    res = json.loads(raw_res)
    assert res["status"] == "success"

    raw_err, ok_err = await tool.handler(action="invalid_action")
    assert ok_err is False
    assert "Unknown action" in raw_err
