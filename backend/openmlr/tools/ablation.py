"""Agent tool for Ablation Studies, Statistical Significance Testing, and Publication Tables."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

from ..agent.types import ToolSpec
from ..services.ablation_engine import ablation_engine
from ..services.ablation_types import (
    CorrectionMethod,
    HypothesisTestType,
    VariantType,
)

log = logging.getLogger("openmlr.tools.ablation")


def _resolve_project_id(explicit_proj: str | None, getter: Callable[[], str | None] | None) -> str | None:
    if explicit_proj and explicit_proj.strip():
        return explicit_proj.strip()
    if getter:
        val = getter()
        if val and val.strip():
            return val.strip()
    return None


def _handle_create_study(proj: str | None, kwargs: dict[str, Any]) -> tuple[str, bool]:
    title = kwargs.get("title", "Ablation Study")
    study_id = kwargs.get("study_id")
    desc = kwargs.get("description", "")
    primary_metric = kwargs.get("primary_metric", "accuracy")
    higher_is_better = kwargs.get("higher_is_better", True)
    baseline_variant_name = kwargs.get("baseline_variant_name", "Full Model")
    baseline_desc = kwargs.get("baseline_description", "Proposed full architecture")

    study = ablation_engine.create_study(
        study_id=study_id,
        title=title,
        description=desc,
        project_id=proj,
        primary_metric=primary_metric,
        higher_is_better=higher_is_better,
        baseline_variant_name=baseline_variant_name,
        baseline_description=baseline_desc,
    )
    return json.dumps({"status": "success", "study": study.model_dump()}, indent=2), True


def _handle_record_variant_runs(kwargs: dict[str, Any]) -> tuple[str, bool]:
    study_id = kwargs.get("study_id")
    if not study_id:
        return "Missing 'study_id' in record_variant_runs.", False

    variant_name = kwargs.get("variant_name")
    if not variant_name:
        return "Missing 'variant_name' in record_variant_runs.", False

    metrics = kwargs.get("metrics", {})
    if not metrics or not isinstance(metrics, dict):
        return "Missing or invalid 'metrics' dictionary mapping metric name to list of numeric values.", False

    variant_type_str = kwargs.get("variant_type", "ablation").lower()
    try:
        variant_type = VariantType(variant_type_str)
    except ValueError:
        variant_type = VariantType.ABLATION

    res = ablation_engine.record_variant_runs(
        study_id=study_id,
        variant_name=variant_name,
        metrics=metrics,
        variant_type=variant_type,
        description=kwargs.get("description", ""),
        removed_components=kwargs.get("removed_components", []),
        added_components=kwargs.get("added_components", []),
        run_ids=kwargs.get("run_ids", []),
    )
    return json.dumps({"status": "success", "variant": res.model_dump()}, indent=2), True


def _handle_analyze_significance(kwargs: dict[str, Any]) -> tuple[str, bool]:
    study_id = kwargs.get("study_id")
    if not study_id:
        return "Missing 'study_id' for analyze_significance.", False

    corr_method_str = kwargs.get("correction_method", "holm_bonferroni").lower()
    try:
        corr_method = CorrectionMethod(corr_method_str)
    except ValueError:
        corr_method = CorrectionMethod.HOLM_BONFERRONI

    test_type_str = kwargs.get("test_type", "welch_t").lower()
    try:
        test_type = HypothesisTestType(test_type_str)
    except ValueError:
        test_type = HypothesisTestType.WELCH_T

    study = ablation_engine.analyze_study(
        study_id=study_id,
        correction_method=corr_method,
        test_type=test_type,
    )
    return json.dumps({"status": "success", "study": study.model_dump()}, indent=2), True


def _handle_generate_latex_table(kwargs: dict[str, Any]) -> tuple[str, bool]:
    study_id = kwargs.get("study_id")
    if not study_id:
        return "Missing 'study_id' for generate_latex_table.", False

    metrics = kwargs.get("metrics")
    inc_stars = kwargs.get("include_significance_stars", True)
    caption = kwargs.get("caption", "Ablation study on component contributions.")
    label = kwargs.get("label", "tab:ablation_study")

    latex_code = ablation_engine.generate_latex_table(
        study_id=study_id,
        metrics=metrics,
        include_significance_stars=inc_stars,
        caption=caption,
        label=label,
    )
    return json.dumps({"status": "success", "latex_table": latex_code}, indent=2), True


def _handle_get_study(kwargs: dict[str, Any]) -> tuple[str, bool]:
    study_id = kwargs.get("study_id")
    if not study_id:
        return "Missing 'study_id'.", False
    study = ablation_engine.get_study(study_id)
    if not study:
        return f"Study '{study_id}' not found.", False
    return json.dumps({"status": "success", "study": study.model_dump()}, indent=2), True


def _handle_list_studies(proj: str | None) -> tuple[str, bool]:
    studies = ablation_engine.list_studies(proj)
    return json.dumps(
        {
            "status": "success",
            "count": len(studies),
            "studies": [
                {
                    "id": s.id,
                    "title": s.title,
                    "primary_metric": s.primary_metric,
                    "variants_count": len(s.variants),
                    "created_at": s.created_at,
                }
                for s in studies
            ],
        },
        indent=2,
    ), True


def create_ablation_tool(
    get_project_context: Callable[[], str | None] | None = None,
) -> ToolSpec:
    """Create the ablation and statistical significance agent tool."""

    async def _execute(**kwargs: Any) -> tuple[str, bool]:
        action = kwargs.get("action", "list_studies")
        proj = _resolve_project_id(kwargs.get("project_id"), get_project_context)

        try:
            if action == "create_study":
                return _handle_create_study(proj, kwargs)
            elif action == "record_variant_runs":
                return _handle_record_variant_runs(kwargs)
            elif action == "analyze_significance":
                return _handle_analyze_significance(kwargs)
            elif action == "generate_latex_table":
                return _handle_generate_latex_table(kwargs)
            elif action == "get_study":
                return _handle_get_study(kwargs)
            elif action in ("list_studies", "list"):
                return _handle_list_studies(proj)
            return (
                f"Unknown action: '{action}'. Allowed: create_study, record_variant_runs, "
                f"analyze_significance, generate_latex_table, get_study, list_studies.",
                False,
            )
        except Exception as e:
            log.exception("Ablation tool error: %s", e)
            return f"Error executing ablation action '{action}': {e}", False

    return ToolSpec(
        name="ablation",
        description=(
            "Ablation Studies & Statistical Significance Testing Engine. "
            "Design controlled ablation studies, aggregate multi-seed performance runs, perform hypothesis testing "
            "(Welch's t-test, Cohen's d, bootstrap 95% CI, Holm-Bonferroni correction), rank component impacts, "
            "and render camera-ready LaTeX publication tables. "
            "Actions: `create_study`, `record_variant_runs`, `analyze_significance`, `generate_latex_table`, `get_study`, `list_studies`."
        ),
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "create_study",
                        "record_variant_runs",
                        "analyze_significance",
                        "generate_latex_table",
                        "get_study",
                        "list_studies",
                    ],
                    "description": "Action to perform.",
                },
                "study_id": {"type": "string", "description": "Study identifier."},
                "project_id": {"type": "string", "description": "Optional project identifier."},
                "title": {"type": "string", "description": "Title of the ablation study."},
                "description": {"type": "string", "description": "Study description / motivation."},
                "primary_metric": {"type": "string", "description": "Primary evaluation metric (e.g. accuracy, perplexity, f1)."},
                "higher_is_better": {"type": "boolean", "description": "Whether higher metric value is better."},
                "baseline_variant_name": {"type": "string", "description": "Name of full proposed architecture."},
                "variant_name": {"type": "string", "description": "Name of ablated or modified variant."},
                "variant_type": {
                    "type": "string",
                    "enum": ["baseline", "ablation", "addition", "modification"],
                    "description": "Category of variant.",
                },
                "removed_components": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of omitted components/techniques in this ablation.",
                },
                "added_components": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of added components in this variant.",
                },
                "metrics": {
                    "type": "object",
                    "description": "Mapping from metric names to lists of multi-seed floating point values.",
                },
                "correction_method": {
                    "type": "string",
                    "enum": ["holm_bonferroni", "benjamini_hochberg", "none"],
                    "description": "Multiple testing correction.",
                },
                "test_type": {
                    "type": "string",
                    "enum": ["welch_t", "student_t", "mann_whitney", "bootstrap"],
                    "description": "Hypothesis test type.",
                },
                "include_significance_stars": {"type": "boolean", "description": "Include ***, **, * annotations in LaTeX table."},
                "caption": {"type": "string", "description": "Table caption for LaTeX output."},
                "label": {"type": "string", "description": "LaTeX label for \\ref{}."},
            },
            "required": ["action"],
        },
        handler=_execute,
    )
