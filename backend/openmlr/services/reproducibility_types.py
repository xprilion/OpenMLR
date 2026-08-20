"""Data models and types for the Reproducibility Auditor & Artifact Governance Service."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ChecklistVenue(str, Enum):
    NEURIPS = "neurips"
    ICML = "icml"
    ICLR = "iclr"
    CVPR = "cvpr"
    GENERAL = "general"


class CheckStatus(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"


class CheckSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CheckCategory(str, Enum):
    DETERMINISM = "determinism"
    ENVIRONMENT = "environment"
    HARDWARE = "hardware"
    DATASET = "dataset"
    HYPERPARAMETERS = "hyperparameters"
    CHECKPOINTS = "checkpoints"


class CheckItem(BaseModel):
    id: str = Field(..., description="Unique check identifier")
    category: CheckCategory = Field(..., description="Audit category")
    title: str = Field(..., description="Brief title of check")
    description: str = Field(..., description="Detailed description")
    status: CheckStatus = Field(..., description="Status result")
    severity: CheckSeverity = Field(default=CheckSeverity.MEDIUM, description="Severity if failing")
    details: str = Field(default="", description="Findings and context")
    remediation: str = Field(default="", description="Suggested fix or code snippet")


class CategoryScore(BaseModel):
    category: CheckCategory = Field(..., description="Category")
    score: float = Field(..., description="Score 0 to 100")
    passed_checks: int = Field(..., description="Number of passing checks")
    total_checks: int = Field(..., description="Total checks evaluated")
    status: CheckStatus = Field(default=CheckStatus.PASS, description="Overall category status")


class ReproducibilityAuditReport(BaseModel):
    id: str = Field(..., description="Unique audit report identifier")
    project_id: str | None = Field(default=None, description="Associated project ID")
    created_at: str = Field(..., description="ISO timestamp")
    overall_score: float = Field(..., description="Overall reproducibility score (0-100)")
    grade: str = Field(..., description="Letter grade (A+, A, B, C, F)")
    venue: ChecklistVenue = Field(default=ChecklistVenue.NEURIPS, description="Evaluation rubric venue")
    categories: list[CategoryScore] = Field(default_factory=list, description="Category scores")
    checklist: list[CheckItem] = Field(default_factory=list, description="Detailed checklist items")
    detected_frameworks: list[str] = Field(default_factory=list, description="Detected ML frameworks")
    seeds_detected: dict[str, int | str] = Field(default_factory=dict, description="Discovered seeds")
    cuda_requirements: dict[str, Any] = Field(default_factory=dict, description="Hardware & CUDA requirements")
    dockerfile_recipe: str = Field(default="", description="Reproducible Dockerfile")
    conda_recipe: str = Field(default="", description="Reproducible environment.yml")
    latex_appendix: str = Field(default="", description="LaTeX Reproducibility Statement")
    badge_markdown: str = Field(default="", description="Markdown badge string")
    badge_svg: str = Field(default="", description="SVG badge markup")


class AuditCodebaseRequest(BaseModel):
    target_path: str = Field(default=".", description="Target workspace or directory path to audit")
    venue: ChecklistVenue = Field(default=ChecklistVenue.NEURIPS, description="Conference standard to evaluate")
    framework_hint: str | None = Field(default=None, description="Optional framework hint (pytorch, jax, etc.)")
    code_snippets: dict[str, str] | None = Field(default=None, description="Optional in-memory code snippets")


class GenerateDockerfileRequest(BaseModel):
    framework: str = Field(default="pytorch", description="ML framework: pytorch, jax, tensorflow, scikit-learn")
    cuda_version: str = Field(default="12.1.0", description="CUDA base image version")
    python_version: str = Field(default="3.11", description="Python runtime version")
    entrypoint_cmd: str = Field(default="python train.py", description="Main training entrypoint")
    requirements: list[str] = Field(default_factory=list, description="Pinned Python packages")


class GenerateAppendixRequest(BaseModel):
    report_id: str | None = Field(default=None, description="Optional report ID to base appendix on")
    paper_title: str = Field(default="Reproducible Machine Learning Study", description="Paper title")
    authors: str = Field(default="Autonomous Research Agent", description="Authors")
    hardware_specs: str = Field(default="NVIDIA A100-SXM4-80GB (1 GPU), 8 CPU cores, 64GB RAM", description="Hardware")
    random_seeds: list[int] = Field(default_factory=lambda: [42, 1337, 2026], description="Seeds tested")
    dataset_url: str = Field(default="https://huggingface.co/datasets/...", description="Dataset repository")
    code_url: str = Field(default="https://github.com/...", description="Code repository")


class FixDeterminismRequest(BaseModel):
    framework: str = Field(default="pytorch", description="Target framework: pytorch, jax, tensorflow")
    seed: int = Field(default=42, description="Target random seed")
    strict_mode: bool = Field(default=True, description="Enable torch.use_deterministic_algorithms")
