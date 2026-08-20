"""Unit tests for the Publication Figure Generator service."""

import pytest
from openmlr.services.figure_generator import FigureGeneratorService
from openmlr.services.figure_types import (
    GenerateFigureRequest,
    MultiPanelLayoutRequest,
    PlotType,
    StyleTheme,
    ColorPalette,
)


def test_generate_loss_curve_figure():
    req = GenerateFigureRequest(
        title="Training Loss Comparison",
        caption="Training loss across 10k steps for baseline vs. ours.",
        plot_type=PlotType.LOSS_CURVE,
        style_theme=StyleTheme.NEURIPS,
        palette=ColorPalette.COLORBLIND,
        x_label="Step",
        y_label="Loss",
        series_data={
            "Baseline": [{"x": 100, "y": 2.5, "y_err": 0.1}, {"x": 200, "y": 1.8, "y_err": 0.08}],
            "Ours (MoE)": [{"x": 100, "y": 2.1, "y_err": 0.05}, {"x": 200, "y": 1.2, "y_err": 0.04}],
        },
        generate_tikz=True,
    )
    artifact = FigureGeneratorService.generate_figure("proj_test", req)
    assert artifact.id.startswith("fig_")
    assert artifact.title == "Training Loss Comparison"
    assert "plt.subplots" in artifact.python_script
    assert "\\begin{figure}" in artifact.latex_snippet
    assert "\\begin{tikzpicture}" in artifact.tikz_code
    assert "<svg" in artifact.svg_preview


def test_generate_ablation_bar_figure():
    req = GenerateFigureRequest(
        title="Ablation on GSM8K",
        caption="Accuracy across ablations.",
        plot_type=PlotType.ABLATION_BAR,
        style_theme=StyleTheme.ICML,
        palette=ColorPalette.VIRIDIS,
        categories=["Full Model", "No LoRA+", "No Warmup"],
        series_data={
            "Accuracy (%)": [{"x": "Full Model", "y": 78.4}, {"x": "No LoRA+", "y": 74.2}, {"x": "No Warmup", "y": 71.0}]
        },
    )
    artifact = FigureGeneratorService.generate_figure("proj_test", req)
    assert artifact.plot_type == PlotType.ABLATION_BAR
    assert "ax.bar" in artifact.python_script


def test_list_and_delete_figures():
    req = GenerateFigureRequest(
        title="Figure A",
        series_data={"S1": [{"x": 1, "y": 2}]},
    )
    art = FigureGeneratorService.generate_figure("proj_crud", req)
    figs = FigureGeneratorService.list_figures("proj_crud")
    assert len(figs) >= 1
    found = FigureGeneratorService.get_figure("proj_crud", art.id)
    assert found is not None
    assert found.title == "Figure A"

    success = FigureGeneratorService.delete_figure("proj_crud", art.id)
    assert success is True
    assert FigureGeneratorService.get_figure("proj_crud", art.id) is None


def test_create_multipanel_layout():
    req1 = GenerateFigureRequest(
        title="Loss Convergence",
        series_data={"S": [{"x": 1, "y": 1}]},
    )
    req2 = GenerateFigureRequest(
        title="Throughput vs. Memory",
        series_data={"S": [{"x": 1, "y": 1}]},
    )
    f1 = FigureGeneratorService.generate_figure("proj_multi", req1)
    f2 = FigureGeneratorService.generate_figure("proj_multi", req2)

    multi_req = MultiPanelLayoutRequest(
        title="Overall Benchmark Summary",
        caption="Ablation overview.",
        figure_ids=[f1.id, f2.id],
        columns=2,
        subcaptions={f1.id: "(a) Loss", f2.id: "(b) Throughput"},
    )
    res = FigureGeneratorService.create_multipanel_layout("proj_multi", multi_req)
    assert res["figure_count"] == 2
    assert "\\begin{figure*}" in res["latex_code"]
    assert "\\begin{subfigure}" in res["latex_code"]
