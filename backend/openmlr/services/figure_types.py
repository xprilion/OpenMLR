"""Data models and types for the Publication Figure Studio."""

from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class PlotType(str, Enum):
    """Supported scientific plot types."""
    LOSS_CURVE = "loss_curve"
    ABLATION_BAR = "ablation_bar"
    PARETO_FRONTIER = "pareto_frontier"
    CONFUSION_MATRIX = "confusion_matrix"
    RADAR_BENCHMARK = "radar_benchmark"
    HEATMAP = "heatmap"


class StyleTheme(str, Enum):
    """Conference styling presets."""
    NEURIPS = "neurips"
    ICML = "icml"
    ICLR = "iclr"
    CVPR = "cvpr"
    DARK = "dark"


class ColorPalette(str, Enum):
    """Colorblind-safe and academic palettes."""
    COLORBLIND = "colorblind"
    VIRIDIS = "viridis"
    MUTED = "muted"
    DEEP = "deep"
    TABLEAU = "tableau"


class FigureDataPoint(BaseModel):
    """Generic 2D/3D data point."""
    x: float | str
    y: float
    y_err: float | None = None
    series: str = "default"
    metadata: dict[str, Any] = Field(default_factory=dict)


class GenerateFigureRequest(BaseModel):
    """Request payload for generating a publication figure."""
    title: str = Field(..., description="Figure title")
    caption: str = Field("", description="LaTeX paper caption")
    plot_type: PlotType = Field(PlotType.LOSS_CURVE, description="Type of plot")
    style_theme: StyleTheme = Field(StyleTheme.NEURIPS, description="Conference theme standard")
    palette: ColorPalette = Field(ColorPalette.COLORBLIND, description="Color palette")
    x_label: str = Field("Step", description="X-axis label")
    y_label: str = Field("Loss", description="Y-axis label")
    series_data: dict[str, list[dict[str, Any]]] = Field(
        default_factory=dict,
        description="Named series data mapping (e.g. {'Baseline': [{'x': 1, 'y': 2.4}], 'Ours': [...]})"
    )
    categories: list[str] = Field(default_factory=list, description="Categorical labels for bar/radar/heatmap")
    values_matrix: list[list[float]] = Field(default_factory=list, description="2D matrix for heatmap/confusion matrix")
    width_inches: float = Field(6.0, description="Figure width in inches for LaTeX")
    height_inches: float = Field(4.0, description="Figure height in inches for LaTeX")
    generate_tikz: bool = Field(True, description="Whether to also generate standalone TikZ / PGFPlots code")


class MultiPanelLayoutRequest(BaseModel):
    """Request payload for generating a multi-panel subfigure grid."""
    title: str = Field(..., description="Overall figure title")
    caption: str = Field(..., description="Combined multi-panel LaTeX caption")
    figure_ids: list[str] = Field(..., description="IDs of figures to include in subfigure grid")
    columns: int = Field(2, description="Number of columns in subfigure grid (1, 2, 3)")
    subcaptions: dict[str, str] = Field(default_factory=dict, description="Subcaption per figure ID")


class FigureArtifact(BaseModel):
    """Stored figure artifact with scripts and LaTeX snippets."""
    id: str
    project_id: str
    title: str
    caption: str
    plot_type: PlotType
    style_theme: StyleTheme
    palette: ColorPalette
    python_script: str
    latex_snippet: str
    tikz_code: str
    svg_preview: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()
