"""Unit tests for the Reproducibility Auditor Service."""

from openmlr.services.reproducibility_auditor import ReproducibilityAuditorService
from openmlr.services.reproducibility_types import (
    AuditCodebaseRequest,
    CheckCategory,
    ChecklistVenue,
    CheckStatus,
    GenerateAppendixRequest,
    GenerateDockerfileRequest,
)


def test_determinism_snippet_generation():
    py_snippet = ReproducibilityAuditorService.generate_determinism_snippet("pytorch", seed=123, strict_mode=True)
    assert "torch.manual_seed(seed)" in py_snippet
    assert "set_seed(123)" in py_snippet
    assert "torch.backends.cudnn.deterministic = True" in py_snippet
    assert "torch.use_deterministic_algorithms(True)" in py_snippet
    assert "PYTHONHASHSEED" in py_snippet

    jax_snippet = ReproducibilityAuditorService.generate_determinism_snippet("jax", seed=999)
    assert "jax.random.PRNGKey(999)" in jax_snippet

    tf_snippet = ReproducibilityAuditorService.generate_determinism_snippet("tensorflow", seed=777)
    assert "tf.random.set_seed(777)" in tf_snippet


def test_generate_dockerfile():
    req = GenerateDockerfileRequest(
        framework="pytorch",
        cuda_version="12.1.0",
        python_version="3.11",
        entrypoint_cmd="python run_exp.py --seed 42",
        requirements=["torch==2.1.0", "transformers==4.35.0"],
    )
    dockerfile = ReproducibilityAuditorService.generate_dockerfile(req)
    assert "FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04" in dockerfile
    assert "CUBLAS_WORKSPACE_CONFIG=:4096:8" in dockerfile
    assert "torch==2.1.0" in dockerfile
    assert 'CMD ["python run_exp.py --seed 42"]' in dockerfile


def test_generate_conda_env():
    env = ReproducibilityAuditorService.generate_conda_env(
        env_name="test-env",
        python_version="3.10",
        dependencies=["pytorch=2.1.0", "torchvision=0.16.0"],
    )
    assert "name: test-env" in env
    assert "python=3.10" in env
    assert "pytorch=2.1.0" in env


def test_generate_badges():
    md = ReproducibilityAuditorService.generate_badge_markdown(96.5, "A+")
    assert "reproducibility-A+%20(96%25)-brightgreen.svg" in md

    svg = ReproducibilityAuditorService.generate_badge_svg(96.5, "A+")
    assert "<svg" in svg
    assert "A+ (96%)" in svg


def test_generate_latex_appendix():
    req = GenerateAppendixRequest(
        paper_title="Self-Correction in Autonomous ML",
        authors="Silas et al.",
        hardware_specs="8x NVIDIA H100 SXM5 80GB",
        random_seeds=[42, 100, 2026],
        dataset_url="https://huggingface.co/datasets/custom-bench",
        code_url="https://github.com/xprilion/openmlr",
    )
    latex = ReproducibilityAuditorService.generate_latex_appendix(req)
    assert "\\section{Reproducibility Statement}" in latex
    assert "\\subsection{Hardware and Execution Environment}" in latex
    assert "8x NVIDIA H100 SXM5 80GB" in latex
    assert "42, 100, 2026" in latex
    assert "https://huggingface.co/datasets/custom-bench" in latex


def test_audit_codebase_snippets_pass():
    code_snippets = {
        "train.py": """
import torch
import numpy as np
import random
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--learning_rate', type=float, default=1e-4)
    parser.add_argument('--batch_size', type=int, default=32)
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = torch.nn.Linear(10, 2).to(device)

    # Dataset splits
    train_split, val_dataset = torch.utils.data.random_split(range(100), [80, 20])

    # Checkpoint saving
    torch.save({'model': model.state_dict()}, 'checkpoint.pt')
""",
        "requirements.txt": """
torch==2.1.0
numpy==1.26.0
pyyaml==6.0.1
""",
        "Dockerfile": """
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04
COPY . /workspace
""",
    }

    req = AuditCodebaseRequest(
        target_path="mock_path",
        venue=ChecklistVenue.NEURIPS,
        code_snippets=code_snippets,
    )
    report = ReproducibilityAuditorService.audit_codebase(req, project_id="proj_test")

    assert report.id.startswith("rep_")
    assert report.overall_score >= 85.0
    assert report.grade in ("A+", "A")
    assert report.venue == ChecklistVenue.NEURIPS
    assert len(report.categories) == len(CheckCategory)

    det_cat = next(c for c in report.categories if c.category == CheckCategory.DETERMINISM)
    assert det_cat.score == 100.0
    assert det_cat.status == CheckStatus.PASS

    env_cat = next(c for c in report.categories if c.category == CheckCategory.ENVIRONMENT)
    assert env_cat.score == 100.0

    assert "PyTorch" in report.detected_frameworks
    assert report.seeds_detected.get("main_seed") in (42, "args.seed")
    assert "Reproducibility Statement" in report.latex_appendix

    # Check retrieval from store
    retrieved = ReproducibilityAuditorService.get_report(report.id, "proj_test")
    assert retrieved is not None
    assert retrieved.id == report.id

    reports = ReproducibilityAuditorService.list_reports("proj_test")
    assert len(reports) >= 1

    deleted = ReproducibilityAuditorService.delete_report(report.id, "proj_test")
    assert deleted is True
    assert ReproducibilityAuditorService.get_report(report.id, "proj_test") is None
