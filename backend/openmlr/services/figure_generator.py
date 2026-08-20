"""Publication Figure Generator service for paper plots, scripts, and LaTeX TikZ figures."""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

from .figure_types import (
    FigureArtifact,
    GenerateFigureRequest,
    MultiPanelLayoutRequest,
)

logger = logging.getLogger("openmlr.services.figure_generator")

# Palette color definitions
PALETTES = {
    "colorblind": ["#377eb8", "#ff7f00", "#4daf4a", "#f781bf", "#a65628", "#984ea3"],
    "viridis": ["#440154", "#3b528b", "#21908d", "#5dc963", "#fde725"],
    "muted": ["#4878d0", "#ee854a", "#6acc65", "#d65f5f", "#956cb4", "#8c613c"],
    "deep": ["#4c72b0", "#dd8452", "#55a868", "#c44e52", "#8172b3", "#937860"],
    "tableau": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"],
}

# In-memory figure store per project (in-memory + fallback)
_PROJECT_FIGURES: dict[str, dict[str, FigureArtifact]] = {}


def _generate_python_script(req: GenerateFigureRequest) -> str:
    """Generate clean, standalone Matplotlib/Seaborn Python script for reproducibility."""
    colors = PALETTES.get(req.palette.value, PALETTES["colorblind"])
    data_json = json.dumps(req.series_data, indent=4)
    cats_json = json.dumps(req.categories)
    matrix_json = json.dumps(req.values_matrix)

    return f"""#!/usr/bin/env python3
\"\"\"Publication-grade plot generator: {req.title}\"\"\"

import matplotlib.pyplot as plt
import numpy as np

# Set standard publication styling
plt.rcParams.update({{
    'font.size': 10,
    'font.family': 'sans-serif',
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 9,
    'figure.titlesize': 13,
    'figure.dpi': 300,
    'savefig.bbox': 'tight',
}})

colors = {colors}
series_data = {data_json}
categories = {cats_json}
values_matrix = {matrix_json}

fig, ax = plt.subplots(figsize=({req.width_inches}, {req.height_inches}))

# Plot logic based on plot_type
if "{req.plot_type.value}" == "loss_curve":
    for idx, (s_name, points) in enumerate(series_data.items()):
        xs = [p['x'] for p in points]
        ys = [p['y'] for p in points]
        c = colors[idx % len(colors)]
        ax.plot(xs, ys, label=s_name, color=c, linewidth=2)
        if any('y_err' in p and p['y_err'] is not None for p in points):
            errs = [p.get('y_err', 0.0) or 0.0 for p in points]
            ax.fill_between(xs, np.array(ys) - np.array(errs), np.array(ys) + np.array(errs), color=c, alpha=0.15)
    ax.set_xlabel("{req.x_label}")
    ax.set_ylabel("{req.y_label}")
    ax.legend(frameon=True)
    ax.grid(True, linestyle='--', alpha=0.5)

elif "{req.plot_type.value}" == "ablation_bar":
    if categories and series_data:
        x_indices = np.arange(len(categories))
        num_series = len(series_data)
        bar_width = 0.8 / max(num_series, 1)
        for idx, (s_name, points) in enumerate(series_data.items()):
            ys = [p['y'] for p in points]
            c = colors[idx % len(colors)]
            offset = (idx - num_series / 2 + 0.5) * bar_width
            ax.bar(x_indices + offset, ys, bar_width, label=s_name, color=c)
        ax.set_xticks(x_indices)
        ax.set_xticklabels(categories, rotation=20, ha='right')
        ax.set_ylabel("{req.y_label}")
        ax.legend(frameon=True)
        ax.grid(axis='y', linestyle='--', alpha=0.5)

elif "{req.plot_type.value}" == "pareto_frontier":
    for idx, (s_name, points) in enumerate(series_data.items()):
        xs = [p['x'] for p in points]
        ys = [p['y'] for p in points]
        c = colors[idx % len(colors)]
        ax.scatter(xs, ys, label=s_name, color=c, s=50, alpha=0.85)
    ax.set_xlabel("{req.x_label}")
    ax.set_ylabel("{req.y_label}")
    ax.legend(frameon=True)
    ax.grid(True, linestyle='--', alpha=0.5)

elif "{req.plot_type.value}" in ("confusion_matrix", "heatmap"):
    if values_matrix:
        im = ax.imshow(values_matrix, cmap='Blues', aspect='auto')
        fig.colorbar(im, ax=ax)
        if categories:
            ax.set_xticks(range(len(categories)))
            ax.set_yticks(range(len(categories)))
            ax.set_xticklabels(categories, rotation=45, ha='right')
            ax.set_yticklabels(categories)

ax.set_title("{req.title}")
plt.tight_layout()
plt.savefig("figure.pdf", dpi=300)
plt.savefig("figure.png", dpi=300)
print("Saved figure.pdf and figure.png successfully.")
"""


def _generate_latex_snippet(fig_id: str, req: GenerateFigureRequest) -> str:
    """Generate a clean LaTeX figure environment snippet."""
    label = f"fig:{fig_id[:8]}"
    caption = req.caption or f"{req.title}. {req.x_label} vs. {req.y_label} across model configurations."
    return (
        "\\begin{figure}[htbp]\n"
        "  \\centering\n"
        f"  \\includegraphics[width=0.85\\linewidth]{{figures/{label}.pdf}}\n"
        f"  \\caption{{{caption}}}\n"
        f"  \\label{{{label}}}\n"
        "\\end{figure}"
    )


def _generate_tikz_code(req: GenerateFigureRequest) -> str:
    """Generate pure LaTeX TikZ/PGFPlots vector graphic code."""
    colors = PALETTES.get(req.palette.value, PALETTES["colorblind"])
    lines = [
        "\\begin{tikzpicture}",
        "\\begin{axis}[",
        f"  title={{{req.title}}},",
        f"  xlabel={{{req.x_label}}},",
        f"  ylabel={{{req.y_label}}},",
        "  grid=major,",
        "  grid style={dashed,gray!30},",
        "  legend pos=north east,",
        "  legend cell align={left},",
        f"  width={req.width_inches * 1.5:.1f}cm,",
        f"  height={req.height_inches * 1.5:.1f}cm",
        "]",
    ]

    for idx, (s_name, points) in enumerate(req.series_data.items()):
        c = colors[idx % len(colors)]
        coords = " ".join(f"({p['x']},{p['y']})" for p in points)
        lines.append(f"\\addplot[color={c}, thick, mark=*] coordinates {{ {coords} }};")
        lines.append(f"\\addlegendentry{{{s_name}}}")

    lines.append("\\end{axis}")
    lines.append("\\end{tikzpicture}")
    return "\n".join(lines)


def _generate_svg_preview(req: GenerateFigureRequest) -> str:
    """Generate an SVG string for instant client-side rendering."""
    colors = PALETTES.get(req.palette.value, PALETTES["colorblind"])
    w = 600
    h = 360
    pad_left = 60
    pad_right = 140
    pad_top = 40
    pad_bottom = 50

    plot_w = w - pad_left - pad_right
    plot_h = h - pad_top - pad_bottom

    svg_elements = [
        f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" className="w-full h-auto bg-[#09090b] rounded-lg border border-border">',
        f'<rect width="{w}" height="{h}" fill="#09090b" rx="8" />',
        f'<text x="{pad_left + plot_w / 2}" y="24" text-anchor="middle" fill="#f4f4f5" font-size="14" font-weight="600" font-family="sans-serif">{req.title}</text>',
        f'<line x1="{pad_left}" y1="{pad_top + plot_h}" x2="{pad_left + plot_w}" y2="{pad_top + plot_h}" stroke="#27272a" stroke-width="1.5" />',
        f'<line x1="{pad_left}" y1="{pad_top}" x2="{pad_left}" y2="{pad_top + plot_h}" stroke="#27272a" stroke-width="1.5" />',
        f'<text x="{pad_left + plot_w / 2}" y="{h - 12}" text-anchor="middle" fill="#a1a1aa" font-size="11" font-family="sans-serif">{req.x_label}</text>',
        f'<text x="18" y="{pad_top + plot_h / 2}" text-anchor="middle" fill="#a1a1aa" font-size="11" transform="rotate(-90 18 {pad_top + plot_h / 2})" font-family="sans-serif">{req.y_label}</text>',
    ]

    all_xs: list[float] = []
    all_ys: list[float] = []
    for points in req.series_data.values():
        for p in points:
            if isinstance(p["x"], (int, float)):
                all_xs.append(float(p["x"]))
            all_ys.append(float(p["y"]))

    min_x = min(all_xs) if all_xs else 0.0
    max_x = max(all_xs) if all_xs else 1.0
    min_y = min(all_ys) if all_ys else 0.0
    max_y = max(all_ys) if all_ys else 1.0
    if max_x == min_x:
        max_x += 1.0
    if max_y == min_y:
        max_y += 1.0

    legend_y = pad_top + 10
    for idx, (s_name, points) in enumerate(req.series_data.items()):
        c = colors[idx % len(colors)]
        svg_points = []
        for p in points:
            px_val = float(p["x"]) if isinstance(p["x"], (int, float)) else idx
            py_val = float(p["y"])
            svg_x = pad_left + ((px_val - min_x) / (max_x - min_x)) * plot_w
            svg_y = pad_top + plot_h - ((py_val - min_y) / (max_y - min_y)) * plot_h
            svg_points.append((svg_x, svg_y))

        if len(svg_points) > 1:
            poly_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in svg_points)
            svg_elements.append(f'<polyline fill="none" stroke="{c}" stroke-width="2.5" points="{poly_str}" />')

        for sx, sy in svg_points:
            svg_elements.append(f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="4" fill="{c}" />')

        # Legend entry
        lx = pad_left + plot_w + 15
        ly = legend_y + idx * 20
        svg_elements.append(f'<line x1="{lx}" y1="{ly}" x2="{lx + 16}" y2="{ly}" stroke="{c}" stroke-width="2.5" />')
        svg_elements.append(f'<circle cx="{lx + 8}" cy="{ly}" r="3" fill="{c}" />')
        svg_elements.append(f'<text x="{lx + 22}" y="{ly + 4}" fill="#f4f4f5" font-size="10" font-family="sans-serif">{s_name}</text>')

    svg_elements.append("</svg>")
    return "".join(svg_elements)


class FigureGeneratorService:
    """Service to create, store, and export publication figures and multi-panel layouts."""

    @classmethod
    def generate_figure(cls, project_id: str, request: GenerateFigureRequest) -> FigureArtifact:
        """Generate a complete figure artifact with code, LaTeX, TikZ, and SVG preview."""
        fig_id = f"fig_{uuid.uuid4().hex[:8]}"
        python_script = _generate_python_script(request)
        latex_snippet = _generate_latex_snippet(fig_id, request)
        tikz_code = _generate_tikz_code(request) if request.generate_tikz else ""
        svg_preview = _generate_svg_preview(request)

        artifact = FigureArtifact(
            id=fig_id,
            project_id=project_id,
            title=request.title,
            caption=request.caption,
            plot_type=request.plot_type,
            style_theme=request.style_theme,
            palette=request.palette,
            python_script=python_script,
            latex_snippet=latex_snippet,
            tikz_code=tikz_code,
            svg_preview=svg_preview,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

        if project_id not in _PROJECT_FIGURES:
            _PROJECT_FIGURES[project_id] = {}
        _PROJECT_FIGURES[project_id][fig_id] = artifact
        return artifact

    @classmethod
    def list_figures(cls, project_id: str) -> list[FigureArtifact]:
        """List all generated figure artifacts for a project."""
        figures_dict = _PROJECT_FIGURES.get(project_id, {})
        return list(figures_dict.values())

    @classmethod
    def get_figure(cls, project_id: str, figure_id: str) -> FigureArtifact | None:
        """Get a single figure artifact."""
        return _PROJECT_FIGURES.get(project_id, {}).get(figure_id)

    @classmethod
    def delete_figure(cls, project_id: str, figure_id: str) -> bool:
        """Delete a figure artifact."""
        if project_id in _PROJECT_FIGURES and figure_id in _PROJECT_FIGURES[project_id]:
            del _PROJECT_FIGURES[project_id][figure_id]
            return True
        return False

    @classmethod
    def create_multipanel_layout(
        cls, project_id: str, request: MultiPanelLayoutRequest
    ) -> dict[str, Any]:
        """Combine multiple figures into a multi-panel LaTeX subfigure environment."""
        figures: list[FigureArtifact] = []
        for fid in request.figure_ids:
            fig = _PROJECT_FIGURES.get(project_id, {}).get(fid)
            if fig is not None:
                figures.append(fig)

        if not figures:
            return {"error": "None of the requested figure IDs exist in this project."}

        cols = max(1, min(request.columns, 4))
        subfig_width = round(1.0 / cols - 0.03, 2)

        latex_lines = [
            "\\begin{figure*}[t]",
            "  \\centering",
        ]

        letters = ["(a)", "(b)", "(c)", "(d)", "(e)", "(f)"]
        for idx, fig in enumerate(figures):
            subcap = request.subcaptions.get(fig.id, f"{letters[idx % len(letters)]} {fig.title}")
            latex_lines.append(
                f"  \\begin{{subfigure}}{{{subfig_width}\\linewidth}}\n"
                f"    \\centering\n"
                f"    \\includegraphics[width=\\linewidth]{{figures/{fig.id}.pdf}}\n"
                f"    \\caption{{{subcap}}}\n"
                f"    \\label{{fig:{fig.id}}}\n"
                f"  \\end{{subfigure}}%"
            )
            if (idx + 1) % cols == 0 and idx + 1 < len(figures):
                latex_lines.append("  \\\\[1ex]")

        latex_lines.extend([
            f"  \\caption{{{request.caption}}}\n"
            f"  \\label{{fig:multipanel_{uuid.uuid4().hex[:6]}}}\n"
            "\\end{figure*}"
        ])

        return {
            "title": request.title,
            "caption": request.caption,
            "figure_count": len(figures),
            "latex_code": "\n".join(latex_lines),
            "included_figures": [f.to_dict() for f in figures],
        }
