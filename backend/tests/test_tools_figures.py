"""Unit tests for the Figures agent tool."""

import pytest

from openmlr.tools.figures import create_figures_tool


@pytest.mark.asyncio
async def test_figures_tool_execution():
    tool = create_figures_tool(get_project_id=lambda: "proj_tool")
    assert tool.name == "figures"
    assert tool.handler is not None

    # Action: generate
    res, ok = await tool.handler(
        action="generate",
        title="Learning Rate Sensitivity",
        caption="Loss under various learning rates.",
        plot_type="loss_curve",
        style_theme="iclr",
        palette="tableau",
        x_label="Learning Rate",
        y_label="Validation Loss",
        series_data={
            "Run 1": [{"x": 1e-4, "y": 2.1}, {"x": 3e-4, "y": 1.4}, {"x": 1e-3, "y": 1.9}]
        },
    )
    assert ok is True
    assert "Learning Rate Sensitivity" in res
    assert "Figure ID:" in res

    # Action: list
    res_list, ok_list = await tool.handler(action="list")
    assert ok_list is True
    assert "Found" in res_list

    # Extract ID
    fig_id = None
    for line in res_list.splitlines():
        if "Learning Rate Sensitivity" in line and "`fig_" in line:
            start = line.find("`fig_") + 1
            end = line.find("`", start)
            fig_id = line[start:end]
            break

    assert fig_id is not None

    # Action: get
    res_get, ok_get = await tool.handler(action="get", figure_id=fig_id)
    assert ok_get is True
    assert "Learning Rate Sensitivity" in res_get

    # Action: create_multipanel with 1 ID fails validation (needs >=2)
    res_err, ok_err = await tool.handler(action="create_multipanel", figure_ids=[fig_id])
    assert ok_err is False
    assert "requires at least 2 figure IDs" in res_err

    # Action: create_multipanel with 2 IDs
    res_multi, ok_multi = await tool.handler(action="create_multipanel", figure_ids=[fig_id, fig_id])
    assert ok_multi is True
    assert "Multi-Panel Subfigure Grid Created" in res_multi
