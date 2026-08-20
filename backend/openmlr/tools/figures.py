"""Agent tool for Publication Figure Studio, Plot Generation, and LaTeX Subfigures."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable
from ..agent.types import ToolSpec
from ..services.figure_types import (
    GenerateFigureRequest,
    MultiPanelLayoutRequest,
    PlotType,
    StyleTheme,
    ColorPalette,
)
from ..services.figure_generator import FigureGeneratorService

log = logging.getLogger("openmlr.tools.figures")


def _resolve_project_id(explicit_proj: str | None, getter: Callable[[], str | None] | None) -> str:
    if explicit_proj and explicit_proj.strip():
        return explicit_proj.strip()
    if getter:
        val = getter()
        if val and val.strip():
            return val.strip()
    return "default"


def _parse_dict(val: Any) -> dict[str, Any]:
    if isinstance(val, dict):
        return val
    if isinstance(val, str) and val.strip():
        try:
            parsed = json.loads(val)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    return {}


def _handle_generate(proj: str, kwargs: dict[str, Any]) -> tuple[str, bool]:
    title = kwargs.get("title")
    if not title:
        return "Error: Field `title` is required for generating a figure.", False

    plot_type_str = kwargs.get("plot_type", "loss_curve")
    style_theme_str = kwargs.get("style_theme", "neurips")
    palette_str = kwargs.get("palette", "colorblind")

    series_data_raw = kwargs.get("series_data") or {}
    series_data = _parse_dict(series_data_raw)

    req = GenerateFigureRequest(
        title=title,
        caption=kwargs.get("caption", ""),
        plot_type=PlotType(plot_type_str) if plot_type_str in PlotType.__members__.values() else PlotType.LOSS_CURVE,
        style_theme=StyleTheme(style_theme_str) if style_theme_str in StyleTheme.__members__.values() else StyleTheme.NEURIPS,
        palette=ColorPalette(palette_str) if palette_str in ColorPalette.__members__.values() else ColorPalette.COLORBLIND,
        x_label=kwargs.get("x_label", "Step"),
        y_label=kwargs.get("y_label", "Loss"),
        series_data=series_data,
        categories=kwargs.get("categories") or [],
        width_inches=float(kwargs.get("width_inches", 6.0)),
        height_inches=float(kwargs.get("height_inches", 4.0)),
        generate_tikz=bool(kwargs.get("generate_tikz", True)),
    )
    artifact = FigureGeneratorService.generate_figure(proj, req)
    msg = (
        f"✅ Publication Figure '{artifact.title}' generated successfully!\n"
        f"- Figure ID: `{artifact.id}`\n"
        f"- Plot Type: `{artifact.plot_type.value}`\n"
        f"- Theme: `{artifact.style_theme.value}` | Palette: `{artifact.palette.value}`\n"
        f"```latex\n{artifact.latex_snippet}\n```"
    )
    return msg, True


def _handle_list(proj: str) -> tuple[str, bool]:
    figures = FigureGeneratorService.list_figures(proj)
    if not figures:
        return f"No figure artifacts found in project `{proj}`.", True
    lines = [f"Found {len(figures)} figure artifacts in project `{proj}`:"]
    for f in figures:
        lines.append(f"- **{f.title}** (`{f.id}`): {f.plot_type.value} | {f.style_theme.value}")
    return "\n".join(lines), True


def _handle_get(proj: str, kwargs: dict[str, Any]) -> tuple[str, bool]:
    fig_id = kwargs.get("figure_id")
    if not fig_id:
        return "Error: `figure_id` is required for get action.", False
    fig = FigureGeneratorService.get_figure(proj, fig_id)
    if not fig:
        return f"Error: Figure `{fig_id}` not found in project `{proj}`.", False
    msg = (
        f"### Figure Artifact: {fig.title}\n"
        f"- **ID:** `{fig.id}`\n"
        f"- **Plot Type:** {fig.plot_type.value}\n"
        f"- **Theme:** {fig.style_theme.value} ({fig.palette.value})\n\n"
        f"#### LaTeX Environment:\n```latex\n{fig.latex_snippet}\n```\n\n"
        f"#### Standalone Python Script:\n```python\n{fig.python_script}\n```"
    )
    return msg, True


def _handle_multipanel(proj: str, kwargs: dict[str, Any]) -> tuple[str, bool]:
    fig_ids = kwargs.get("figure_ids")
    if not fig_ids or len(fig_ids) < 2:
        return "Error: `figure_ids` requires at least 2 figure IDs for a multi-panel layout.", False

    req = MultiPanelLayoutRequest(
        title=kwargs.get("title", "Multi-Panel Benchmark Results"),
        caption=kwargs.get("caption", "Ablation and comparison of empirical performance."),
        figure_ids=fig_ids,
        columns=int(kwargs.get("columns", 2)),
        subcaptions=_parse_dict(kwargs.get("subcaptions")),
    )
    result = FigureGeneratorService.create_multipanel_layout(proj, req)
    if "error" in result:
        return f"Error: {result['error']}", False
    msg = (
        f"✅ Multi-Panel Subfigure Grid Created ({result['figure_count']} figures):\n"
        f"```latex\n{result['latex_code']}\n```"
    )
    return msg, True


def create_figures_tool(get_project_id: Callable[[], str | None] | None = None) -> ToolSpec:
    """Create the 'figures' agent tool spec."""

    async def _execute(action: str = "list", **kwargs: Any) -> tuple[str, bool]:
        await asyncio.sleep(0)
        proj = _resolve_project_id(kwargs.get("project_id"), get_project_id)
        act = (action or "list").lower().strip()

        handlers = {
            "generate": lambda: _handle_generate(proj, kwargs),
            "list": lambda: _handle_list(proj),
            "get": lambda: _handle_get(proj, kwargs),
            "create_multipanel": lambda: _handle_multipanel(proj, kwargs),
        }

        handler = handlers.get(act)
        if not handler:
            return (
                f"Unknown action: '{action}'. "
                "Allowed actions: `generate`, `list`, `get`, `create_multipanel`.",
                False,
            )

        try:
            return handler()
        except Exception as e:
            log.exception("Figures tool error: %s", e)
            return f"Error executing figures action '{action}': {e}", False

    return ToolSpec(
        name="figures",
        description=(
            "Publication Figure Studio and Scientific Plot Generator. "
            "Generate publication-quality vector plots (Loss curves, Ablation bars, Pareto frontiers, Confusion matrices, Heatmaps), "
            "reproducible Matplotlib Python scripts, LaTeX subfigure grids, and pure TikZ vector code."
        ),
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["generate", "list", "get", "create_multipanel"],
                    "description": "Figure action to execute.",
                },
                "project_id": {"type": "string", "description": "Optional project ID override."},
                "figure_id": {"type": "string", "description": "Figure Artifact ID."},
                "title": {"type": "string", "description": "Figure title."},
                "caption": {"type": "string", "description": "LaTeX caption."},
                "plot_type": {
                    "type": "string",
                    "enum": ["loss_curve", "ablation_bar", "pareto_frontier", "confusion_matrix", "radar_benchmark", "heatmap"],
                    "description": "Scientific plot type.",
                },
                "style_theme": {
                    "type": "string",
                    "enum": ["neurips", "icml", "iclr", "cvpr", "dark"],
                    "description": "Conference theme preset.",
                },
                "palette": {
                    "type": "string",
                    "enum": ["colorblind", "viridis", "muted", "deep", "tableau"],
                    "description": "Academic color palette.",
                },
                "x_label": {"type": "string", "description": "X-axis label."},
                "y_label": {"type": "string", "description": "Y-axis label."},
                "series_data": {"type": "object", "description": "Mapping of series name to list of {x, y, y_err} data points."},
                "categories": {"type": "array", "items": {"type": "string"}, "description": "Category labels for bar/radar."},
                "figure_ids": {"type": "array", "items": {"type": "string"}, "description": "Figure IDs for multi-panel grid."},
                "columns": {"type": "integer", "description": "Number of columns in multi-panel grid."},
            },
            "required": ["action"],
        },
        handler=_execute,
    )
