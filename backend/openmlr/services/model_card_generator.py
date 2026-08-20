"""Model Card and Artifact documentation generator adhering to NeurIPS/HuggingFace standards."""

from __future__ import annotations

from typing import Any
from .model_types import ModelArtifact, ModelCardContent

# GPU TDP in Watts for carbon estimation
GPU_TDP_MAP = {
    "nvidia a100": 400.0,
    "nvidia h100": 700.0,
    "nvidia l40s": 350.0,
    "nvidia rtx 4090": 450.0,
    "nvidia rtx 3090": 350.0,
    "nvidia v100": 300.0,
    "nvidia t4": 70.0,
    "google tpu v4": 250.0,
    "apple m3 max": 60.0,
}
DEFAULT_PUE = 1.2  # Datacenter Power Usage Effectiveness
CARBON_INTENSITY_KG_PER_KWH = 0.385  # Global grid average carbon intensity in kg CO2eq / kWh


def estimate_carbon_footprint(gpu_type: str, gpu_hours: float) -> float:
    """Estimate CO2 equivalent emissions in kilograms."""
    lower_gpu = gpu_type.lower()
    power_watts = 350.0
    for key, val in GPU_TDP_MAP.items():
        if key in lower_gpu:
            power_watts = val
            break
    total_kwh = (power_watts * gpu_hours * DEFAULT_PUE) / 1000.0
    return round(total_kwh * CARBON_INTENSITY_KG_PER_KWH, 2)


def generate_bibtex_entry(model: ModelArtifact, author: str) -> str:
    """Generate a clean BibTeX citation for the model artifact."""
    tag = model.name.lower().replace(" ", "_").replace("-", "_")
    return (
        f"@misc{{{tag}_{model.version},\n"
        f"  title = {{{model.name} (v{model.version}): Autonomous Research Model Artifact}},\n"
        f"  author = {{{author}}},\n"
        f"  year = {{2026}},\n"
        f"  publisher = {{OpenMLR Autonomous Research Platform}},\n"
        f"  howpublished = {{\\url{{https://openmlr.local/models/{model.id}}}}}\n"
        f"}}"
    )


def generate_latex_card(model: ModelArtifact, author: str, co2_kg: float) -> str:
    """Generate a LaTeX table/section snippet for academic manuscripts."""
    metrics_str = " & ".join(f"{k} = {v:.4f}" if isinstance(v, float) else f"{k} = {v}" for k, v in model.metrics.items()) or "N/A"
    return (
        "\\begin{table}[h]\n"
        "\\centering\n"
        "\\small\n"
        "\\begin{tabular}{ll}\n"
        "\\toprule\n"
        "\\textbf{Model Property} & \\textbf{Specification} \\\\\n"
        "\\midrule\n"
        f"Model Name & {model.name} (v{model.version}) \\\\\n"
        f"Architecture & {model.architecture} \\\\\n"
        f"Framework & {model.framework.capitalize()} \\\\\n"
        f"Task Type & {model.task_type.replace('_', ' ').capitalize()} \\\\\n"
        f"Parameter Count & {model.parameters_count:,} parameters \\\\\n"
        f"Artifact Size & {model.model_size_mb:.1f} MB \\\\\n"
        f"Primary Metrics & {metrics_str} \\\\\n"
        f"Estimated Carbon & {co2_kg:.2f} kg $\\text{{CO}}_2\\text{{eq}}$ \\\\\n"
        "\\bottomrule\n"
        "\\end{tabular}\n"
        f"\\caption{{Model Card and Artifact Specifications for {model.name}.}}\n"
        f"\\label{{tab:model_card_{model.id}}}\n"
        "\\end{table}"
    )


def generate_markdown_card(
    model: ModelArtifact,
    author: str,
    license_str: str,
    intended_use: str,
    limitations: str,
    evaluation_notes: str,
    gpu_type: str,
    gpu_hours: float,
    co2_kg: float,
) -> str:
    """Generate standard Markdown model card."""
    metrics_rows = "\n".join(
        f"| `{k}` | `{v:.4f}` |" if isinstance(v, float) else f"| `{k}` | `{v}` |"
        for k, v in model.metrics.items()
    ) or "| Metric | None recorded |"

    hparams_rows = "\n".join(
        f"| `{k}` | `{v}` |" for k, v in model.hyperparameters.items()
    ) or "| Hyperparameter | None specified |"

    tags_str = ", ".join(f"`{t}`" for t in model.tags) or "`research`"

    return f"""# Model Card: {model.name} (v{model.version})

## Model Details
- **Model Name:** {model.name}
- **Version:** {model.version}
- **Architecture:** {model.architecture}
- **Framework:** {model.framework}
- **Task Type:** {model.task_type}
- **Status:** {model.status}
- **Author / Lead:** {author}
- **License:** {license_str}
- **Tags:** {tags_str}
- **Created Date:** {model.created_at}

## Description & Summary
{model.description or "Autonomous model artifact trained and evaluated via OpenMLR research pipeline."}

## Intended Use
{intended_use or "Scientific research, academic benchmarking, ablation verification, and reproducible autonomous machine learning."}

## Model Architecture & Capacity
- **Total Parameters:** {model.parameters_count:,}
- **Artifact Disk Size:** {model.model_size_mb:.2f} MB
- **Checkpoint Reference:** `{model.checkpoint_path or "N/A"}`
- **Base Model Foundation:** `{model.base_model or "Trained from scratch"}`

## Hyperparameters & Training Configuration
| Parameter | Value |
| :--- | :--- |
{hparams_rows}

## Quantitative Evaluation Results
| Metric Name | Value |
| :--- | :--- |
{metrics_rows}

{evaluation_notes}

## Limitations & Ethical Considerations
{limitations or "This model is intended strictly for research purposes. Out-of-distribution inputs may degrade performance. Verify downstream safety alignments before real-world deployment."}

## Environmental Impact & Carbon Estimation
- **Hardware Utilized:** {gpu_type}
- **Compute Time:** {gpu_hours:.1f} GPU hours
- **Estimated Carbon Emissions:** **{co2_kg:.2f} kg CO2eq** (PUE: {DEFAULT_PUE}, Grid Intensity: {CARBON_INTENSITY_KG_PER_KWH} kg/kWh)

## Citation
```bibtex
{generate_bibtex_entry(model, author)}
```
"""


def build_model_card(
    model: ModelArtifact,
    author: str = "OpenMLR Research Agent",
    license_str: str = "Apache-2.0",
    intended_use: str = "",
    limitations: str = "",
    evaluation_notes: str = "",
    gpu_type: str = "NVIDIA A100-SXM4-80GB",
    gpu_hours: float = 24.0,
) -> ModelCardContent:
    """Build complete multi-format model card artifact."""
    co2_kg = estimate_carbon_footprint(gpu_type, gpu_hours)
    bibtex = generate_bibtex_entry(model, author)
    latex = generate_latex_card(model, author, co2_kg)
    md = generate_markdown_card(
        model=model,
        author=author,
        license_str=license_str,
        intended_use=intended_use,
        limitations=limitations,
        evaluation_notes=evaluation_notes,
        gpu_type=gpu_type,
        gpu_hours=gpu_hours,
        co2_kg=co2_kg,
    )
    return ModelCardContent(
        model_name=model.name,
        version=model.version,
        markdown=md,
        latex=latex,
        bibtex=bibtex,
        co2_emissions_kg=co2_kg,
        summary={
            "parameters": model.parameters_count,
            "size_mb": model.model_size_mb,
            "architecture": model.architecture,
            "framework": model.framework,
            "co2_kg": co2_kg,
        },
    )
