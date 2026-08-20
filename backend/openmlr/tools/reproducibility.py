"""Agent tool for Reproducibility Auditing, Determinism verification, and Conference Compliance."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

from ..agent.types import ToolSpec
from ..services.reproducibility_auditor import ReproducibilityAuditorService
from ..services.reproducibility_types import (
    AuditCodebaseRequest,
    ChecklistVenue,
    GenerateAppendixRequest,
    GenerateDockerfileRequest,
)

log = logging.getLogger("openmlr.tools.reproducibility")


def _resolve_project_id(explicit_proj: str | None, getter: Callable[[], str | None] | None) -> str:
    if explicit_proj and explicit_proj.strip():
        return explicit_proj.strip()
    if getter:
        val = getter()
        if val and val.strip():
            return val.strip()
    return "default"


def _handle_audit(proj: str, kwargs: dict[str, Any]) -> tuple[str, bool]:
    target_path = kwargs.get("target_path", ".")
    venue_str = kwargs.get("venue", "neurips").lower()
    try:
        venue = ChecklistVenue(venue_str)
    except ValueError:
        venue = ChecklistVenue.NEURIPS

    snippets = kwargs.get("code_snippets")
    req = AuditCodebaseRequest(
        target_path=target_path,
        venue=venue,
        code_snippets=snippets if isinstance(snippets, dict) else None,
    )
    report = ReproducibilityAuditorService.audit_codebase(req, proj)
    result = {
        "status": "success",
        "report_id": report.id,
        "overall_score": report.overall_score,
        "grade": report.grade,
        "venue": report.venue.value,
        "categories": [c.model_dump() for c in report.categories],
        "checklist_summary": {
            "total": len(report.checklist),
            "passed": sum(1 for i in report.checklist if i.status.value == "pass"),
            "warnings": sum(1 for i in report.checklist if i.status.value == "warn"),
            "failed": sum(1 for i in report.checklist if i.status.value == "fail"),
        },
        "detected_frameworks": report.detected_frameworks,
        "badge_markdown": report.badge_markdown,
        "latex_appendix": (
            report.latex_appendix[:500] + "..." if len(report.latex_appendix) > 500 else report.latex_appendix
        ),
    }
    return json.dumps(result, indent=2), True


def _handle_generate_dockerfile(kwargs: dict[str, Any]) -> tuple[str, bool]:
    req_docker = GenerateDockerfileRequest(
        framework=kwargs.get("framework", "pytorch"),
        cuda_version=kwargs.get("cuda_version", "12.1.0"),
        python_version=kwargs.get("python_version", "3.11"),
        entrypoint_cmd=kwargs.get("entrypoint_cmd", "python train.py"),
        requirements=kwargs.get("requirements", []),
    )
    dockerfile = ReproducibilityAuditorService.generate_dockerfile(req_docker)
    return json.dumps({"status": "success", "dockerfile": dockerfile}, indent=2), True


def _handle_generate_appendix(proj: str, kwargs: dict[str, Any]) -> tuple[str, bool]:
    report_id = kwargs.get("report_id")
    report = ReproducibilityAuditorService.get_report(report_id, proj) if report_id else None
    req_app = GenerateAppendixRequest(
        report_id=report_id,
        paper_title=kwargs.get("paper_title", "Reproducible ML Study"),
        hardware_specs=kwargs.get("hardware_specs", "NVIDIA A100-SXM4-80GB (1 GPU)"),
        random_seeds=kwargs.get("random_seeds", [42, 1337, 2026]),
        dataset_url=kwargs.get("dataset_url", "https://huggingface.co/datasets"),
        code_url=kwargs.get("code_url", "https://github.com"),
    )
    appendix = ReproducibilityAuditorService.generate_latex_appendix(req_app, report)
    return json.dumps({"status": "success", "latex_appendix": appendix}, indent=2), True


def _handle_fix_determinism(kwargs: dict[str, Any]) -> tuple[str, bool]:
    framework = kwargs.get("framework", "pytorch")
    seed = int(kwargs.get("seed", 42))
    strict = bool(kwargs.get("strict_mode", True))
    snippet = ReproducibilityAuditorService.generate_determinism_snippet(framework, seed, strict)
    return json.dumps({"status": "success", "determinism_snippet": snippet}, indent=2), True


def _handle_list(proj: str) -> tuple[str, bool]:
    reports = ReproducibilityAuditorService.list_reports(proj)
    return (
        json.dumps(
            {
                "status": "success",
                "count": len(reports),
                "reports": [
                    {
                        "id": r.id,
                        "created_at": r.created_at,
                        "overall_score": r.overall_score,
                        "grade": r.grade,
                        "venue": r.venue.value,
                    }
                    for r in reports
                ],
            },
            indent=2,
        ),
        True,
    )


def create_reproducibility_tool(
    get_project_context: Callable[[], str | None] | None = None,
) -> ToolSpec:
    """Create the reproducibility agent tool."""

    async def _execute(**kwargs: Any) -> tuple[str, bool]:
        action = kwargs.get("action", "audit")
        proj = _resolve_project_id(kwargs.get("project_id"), get_project_context)

        try:
            if action == "audit":
                return _handle_audit(proj, kwargs)
            elif action == "generate_dockerfile":
                return _handle_generate_dockerfile(kwargs)
            elif action == "generate_appendix":
                return _handle_generate_appendix(proj, kwargs)
            elif action == "fix_determinism":
                return _handle_fix_determinism(kwargs)
            elif action == "list_reports" or action == "list":
                return _handle_list(proj)
            return f"Unknown action: '{action}'. Allowed: audit, generate_dockerfile, generate_appendix, fix_determinism, list_reports.", False
        except Exception as e:
            log.exception("Reproducibility tool error: %s", e)
            return f"Error executing reproducibility action '{action}': {e}", False

    return ToolSpec(
        name="reproducibility",
        description=(
            "Reproducibility Auditor & Artifact Governance Tool. "
            "Audit ML codebases for scientific determinism, pinned dependencies, hardware requirements, "
            "and conference checklist compliance (NeurIPS / ICML / ICLR / CVPR). "
            "Actions: `audit`, `generate_dockerfile`, `generate_appendix`, `fix_determinism`, `list_reports`."
        ),
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["audit", "generate_dockerfile", "generate_appendix", "fix_determinism", "list_reports"],
                    "description": "Action to perform.",
                },
                "project_id": {"type": "string", "description": "Optional project ID override."},
                "target_path": {"type": "string", "description": "Path to codebase or files to audit."},
                "venue": {
                    "type": "string",
                    "enum": ["neurips", "icml", "iclr", "cvpr", "general"],
                    "description": "Target conference rubric.",
                },
                "code_snippets": {
                    "type": "object",
                    "description": "Optional in-memory mapping of filename to code strings to audit directly.",
                },
                "framework": {"type": "string", "description": "Target ML framework: pytorch, jax, tensorflow."},
                "seed": {"type": "integer", "description": "Random seed integer for determinism fixes."},
                "strict_mode": {"type": "boolean", "description": "Enable strict deterministic algorithms."},
                "paper_title": {"type": "string", "description": "Title of research paper for appendix."},
                "hardware_specs": {"type": "string", "description": "Hardware specs for LaTeX statement."},
                "requirements": {"type": "array", "items": {"type": "string"}, "description": "Python packages for Dockerfile."},
            },
            "required": ["action"],
        },
        handler=_execute,
    )
