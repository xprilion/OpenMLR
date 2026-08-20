"""Reproducibility Auditor service for ML research artifacts, determinism, and conference checklists."""

from __future__ import annotations

import logging
import os
import re
import uuid
from datetime import UTC, datetime

from .reproducibility_templates import (
    generate_badge_markdown,
    generate_badge_svg,
    generate_latex_appendix,
)
from .reproducibility_types import (
    AuditCodebaseRequest,
    CategoryScore,
    CheckCategory,
    CheckItem,
    CheckSeverity,
    CheckStatus,
    GenerateAppendixRequest,
    GenerateDockerfileRequest,
    ReproducibilityAuditReport,
)

logger = logging.getLogger("openmlr.services.reproducibility_auditor")


class ReproducibilityAuditorService:
    """Audits ML codebases for determinism, environment pinning, hardware, and conference reproducibility."""

    _reports_store: dict[str, dict[str, ReproducibilityAuditReport]] = {}

    @classmethod
    def _get_project_store(cls, project_id: str | None) -> dict[str, ReproducibilityAuditReport]:
        pid = project_id or "default"
        if pid not in cls._reports_store:
            cls._reports_store[pid] = {}
        return cls._reports_store[pid]

    @classmethod
    def list_reports(cls, project_id: str | None = None) -> list[ReproducibilityAuditReport]:
        store = cls._get_project_store(project_id)
        return sorted(store.values(), key=lambda r: r.created_at, reverse=True)

    @classmethod
    def get_report(cls, report_id: str, project_id: str | None = None) -> ReproducibilityAuditReport | None:
        store = cls._get_project_store(project_id)
        return store.get(report_id)

    @classmethod
    def delete_report(cls, report_id: str, project_id: str | None = None) -> bool:
        store = cls._get_project_store(project_id)
        if report_id in store:
            del store[report_id]
            return True
        return False

    @classmethod
    def generate_determinism_snippet(cls, framework: str = "pytorch", seed: int = 42, strict_mode: bool = True) -> str:
        """Generate boilerplate Python snippet for 100% deterministic experiment execution."""
        fw = framework.lower()
        if fw == "jax":
            return (
                f"# JAX Deterministic Random State\n"
                f"import jax\n"
                f"import jax.numpy as jnp\n"
                f"import numpy as np\n"
                f"import os\n"
                f"import random\n\n"
                f"os.environ['PYTHONHASHSEED'] = str({seed})\n"
                f"random.seed({seed})\n"
                f"np.random.seed({seed})\n"
                f"rng_key = jax.random.PRNGKey({seed})\n"
            )
        elif fw in ("tensorflow", "tf"):
            return (
                f"# TensorFlow Deterministic Setup\n"
                f"import os\n"
                f"import random\n"
                f"import numpy as np\n"
                f"import tensorflow as tf\n\n"
                f"os.environ['PYTHONHASHSEED'] = str({seed})\n"
                f"os.environ['TF_DETERMINISTIC_OPS'] = '1'\n"
                f"random.seed({seed})\n"
                f"np.random.seed({seed})\n"
                f"tf.random.set_seed({seed})\n"
            )

        strict_call = "torch.use_deterministic_algorithms(True)" if strict_mode else "# torch.use_deterministic_algorithms(True)"
        return (
            f"# PyTorch Reproducibility & Determinism Boilerplate\n"
            f"import os\n"
            f"import random\n"
            f"import numpy as np\n"
            f"import torch\n\n"
            f"def set_seed(seed: int = {seed}) -> None:\n"
            f"    os.environ['PYTHONHASHSEED'] = str(seed)\n"
            f"    os.environ['CUBLAS_WORKSPACE_CONFIG'] = ':4096:8'\n"
            f"    random.seed(seed)\n"
            f"    np.random.seed(seed)\n"
            f"    torch.manual_seed(seed)\n"
            f"    torch.cuda.manual_seed_all(seed)\n"
            f"    torch.backends.cudnn.deterministic = True\n"
            f"    torch.backends.cudnn.benchmark = False\n"
            f"    {strict_call}\n\n"
            f"set_seed({seed})\n"
        )

    @classmethod
    def generate_dockerfile(cls, req: GenerateDockerfileRequest) -> str:
        """Generate a production-ready, reproducible Docker container definition."""
        pkgs = "\n".join([f"    {p} \\" for p in req.requirements]) if req.requirements else "    torch torchvision --index-url https://download.pytorch.org/whl/cu121 \\"
        return (
            f"# Generated Reproducible ML Research Container\n"
            f"FROM nvidia/cuda:{req.cuda_version}-runtime-ubuntu22.04\n\n"
            f"ENV DEBIAN_FRONTEND=noninteractive \\\n"
            f"    PYTHONUNBUFFERED=1 \\\n"
            f"    PYTHONHASHSEED=0 \\\n"
            f"    CUBLAS_WORKSPACE_CONFIG=:4096:8\n\n"
            f"RUN apt-get update && apt-get install -y --no-install-recommends \\\n"
            f"    python{req.python_version} \\\n"
            f"    python3-pip \\\n"
            f"    git \\\n"
            f"    curl \\\n"
            f"    && rm -rf /var/lib/apt/lists/*\n\n"
            f"WORKDIR /workspace\n"
            f"COPY . /workspace\n\n"
            f"RUN pip install --no-cache-dir --upgrade pip && \\\n"
            f"    pip install --no-cache-dir \\\n"
            f"{pkgs}\n"
            f"    pyyaml\n\n"
            f"CMD [\"{req.entrypoint_cmd}\"]\n"
        )

    @classmethod
    def generate_conda_env(cls, env_name: str = "openmlr-reproduce", python_version: str = "3.11", dependencies: list[str] | None = None) -> str:
        """Generate an environment.yml for Conda reproducibility."""
        deps = dependencies or ["pytorch", "torchvision", "pytorch-cuda=12.1", "numpy", "scipy", "pyyaml"]
        dep_lines = "\n".join([f"  - {d}" for d in deps])
        return (
            f"name: {env_name}\n"
            f"channels:\n"
            f"  - pytorch\n"
            f"  - nvidia\n"
            f"  - conda-forge\n"
            f"dependencies:\n"
            f"  - python={python_version}\n"
            f"{dep_lines}\n"
            f"  - pip:\n"
            f"    - openmlr\n"
        )

    @classmethod
    def generate_badge_markdown(cls, score: float, grade: str) -> str:
        return generate_badge_markdown(score, grade)

    @classmethod
    def generate_badge_svg(cls, score: float, grade: str) -> str:
        return generate_badge_svg(score, grade)

    @classmethod
    def generate_latex_appendix(cls, req: GenerateAppendixRequest, report: ReproducibilityAuditReport | None = None) -> str:
        return generate_latex_appendix(req, report)

    @classmethod
    def audit_codebase(
        cls,
        request: AuditCodebaseRequest,
        project_id: str | None = None,
    ) -> ReproducibilityAuditReport:
        """Perform comprehensive static analysis and reproducibility auditing on target code."""
        code_map = request.code_snippets or {}
        target_path = request.target_path

        if not code_map and os.path.exists(target_path):
            try:
                for root, _, files in os.walk(target_path):
                    for file in files:
                        if file.endswith((".py", ".txt", ".toml", ".yaml", ".yml", ".json", ".md", "Dockerfile")):
                            full_path = os.path.join(root, file)
                            rel_path = os.path.relpath(full_path, target_path)
                            if len(code_map) < 25:
                                try:
                                    with open(full_path, encoding="utf-8", errors="ignore") as f:
                                        code_map[rel_path] = f.read(50000)
                                except Exception:
                                    pass
            except Exception as e:
                logger.warning("Error reading files in %s: %s", target_path, e)

        combined_text = "\n".join(code_map.values())
        filenames = list(code_map.keys())

        # 1. Determinism Audit
        seeds_found: dict[str, int | str] = {}
        checklist: list[CheckItem] = []

        has_torch_seed = bool(re.search(r"torch\.manual_seed\([^)]+\)", combined_text))
        has_np_seed = bool(re.search(r"np\.random\.seed\([^)]+\)", combined_text))
        has_random_seed = bool(re.search(r"random\.seed\([^)]+\)", combined_text))
        has_cudnn_det = "cudnn.deterministic" in combined_text
        has_det_algo = "use_deterministic_algorithms" in combined_text or "CUBLAS_WORKSPACE_CONFIG" in combined_text

        seed_match = re.search(r"(?:manual_seed|seed)\(([^)]+)\)", combined_text)
        if seed_match:
            val_str = seed_match.group(1).strip()
            if val_str.isdigit():
                seeds_found["main_seed"] = int(val_str)
            else:
                seeds_found["main_seed"] = val_str

        if has_torch_seed or has_np_seed or has_random_seed:
            checklist.append(
                CheckItem(
                    id="det_seed_init",
                    category=CheckCategory.DETERMINISM,
                    title="Random Seed Initialization",
                    description="RNG generator is explicitly initialized with deterministic seeds.",
                    status=CheckStatus.PASS,
                    severity=CheckSeverity.CRITICAL,
                    details=f"Found explicit random seed calls ({', '.join(str(v) for v in seeds_found.values()) or 'present'}).",
                )
            )
        else:
            checklist.append(
                CheckItem(
                    id="det_seed_init",
                    category=CheckCategory.DETERMINISM,
                    title="Random Seed Initialization",
                    description="RNG generator is explicitly initialized with deterministic seeds.",
                    status=CheckStatus.FAIL,
                    severity=CheckSeverity.CRITICAL,
                    details="No explicit torch.manual_seed(), np.random.seed(), or random.seed() call detected.",
                    remediation="Add `set_seed(42)` at the beginning of training scripts.",
                )
            )

        checklist.append(
            CheckItem(
                id="det_cudnn",
                category=CheckCategory.DETERMINISM,
                title="cuDNN Determinism Flags",
                description="torch.backends.cudnn.deterministic is configured.",
                status=CheckStatus.PASS if has_cudnn_det else CheckStatus.WARN,
                severity=CheckSeverity.HIGH,
                details="torch.backends.cudnn.deterministic is enabled." if has_cudnn_det else "cuDNN algorithm selection can lead to variance.",
                remediation="Set `torch.backends.cudnn.deterministic = True` and `torch.backends.cudnn.benchmark = False`." if not has_cudnn_det else "",
            )
        )

        # 2. Environment & Dependencies Audit
        has_req_file = any("requirements" in fn or "pyproject" in fn or "environment.yml" in fn or "Pipfile" in fn for fn in filenames)
        has_pinned_deps = bool(re.search(r"[a-zA-Z0-9_\-]+==\d+", combined_text))
        has_dockerfile = any("Dockerfile" in fn or "docker-compose" in fn for fn in filenames)

        checklist.append(
            CheckItem(
                id="env_deps_manifest",
                category=CheckCategory.ENVIRONMENT,
                title="Dependency Manifest File",
                description="Project includes requirements.txt, pyproject.toml, or environment.yml.",
                status=CheckStatus.PASS if has_req_file else CheckStatus.FAIL,
                severity=CheckSeverity.CRITICAL,
                details="Found dependency configuration file." if has_req_file else "No requirements.txt or pyproject.toml detected.",
                remediation="Generate locked dependencies using `pip freeze > requirements.txt` or `uv export`." if not has_req_file else "",
            )
        )

        checklist.append(
            CheckItem(
                id="env_pinned_versions",
                category=CheckCategory.ENVIRONMENT,
                title="Exact Package Pinning",
                description="Package versions are strictly pinned with `==` to avoid breaking changes.",
                status=CheckStatus.PASS if has_pinned_deps else CheckStatus.WARN,
                severity=CheckSeverity.HIGH,
                details="Found pinned package dependencies (e.g. torch==2.x)." if has_pinned_deps else "Dependencies appear unpinned.",
                remediation="Pin exact versions for all dependencies using `==`." if not has_pinned_deps else "",
            )
        )

        checklist.append(
            CheckItem(
                id="env_container_recipe",
                category=CheckCategory.ENVIRONMENT,
                title="Containerization / Docker Recipe",
                description="Dockerfile is provided for isolated reproduction.",
                status=CheckStatus.PASS if has_dockerfile else CheckStatus.WARN,
                severity=CheckSeverity.MEDIUM,
                details="Found Dockerfile in workspace." if has_dockerfile else "No container recipe detected.",
                remediation="Use OpenMLR's generate_dockerfile action to build a reproducible container image." if not has_dockerfile else "",
            )
        )

        # 3. Hardware & Compute
        has_cuda_check = "cuda.is_available()" in combined_text or "cuda:0" in combined_text or "to(device)" in combined_text
        checklist.append(
            CheckItem(
                id="hw_device_agnostic",
                category=CheckCategory.HARDWARE,
                title="Device Selection & Hardware Portability",
                description="Code dynamically identifies compute device (CUDA / MPS / CPU).",
                status=CheckStatus.PASS if has_cuda_check else CheckStatus.WARN,
                severity=CheckSeverity.HIGH,
                details="Dynamic device checking identified." if has_cuda_check else "No dynamic device selection found.",
                remediation="Use `device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')`." if not has_cuda_check else "",
            )
        )

        # 4. Dataset & Splits
        has_splits = any(k in combined_text.lower() for k in ["train_test_split", "train_split", "val_dataset", "test_loader", "random_split"])
        checklist.append(
            CheckItem(
                id="data_splits_spec",
                category=CheckCategory.DATASET,
                title="Evaluation Partition Separation",
                description="Training, validation, and test datasets are partitioned without leakage.",
                status=CheckStatus.PASS if has_splits else CheckStatus.WARN,
                severity=CheckSeverity.CRITICAL,
                details="Train/val/test split logic present." if has_splits else "Explicit partition splitting not detected.",
                remediation="Ensure train, validation, and test splits are strictly separated." if not has_splits else "",
            )
        )

        # 5. Hyperparameters & Logging
        has_hparams = any(k in combined_text.lower() for k in ["argparse", "hydra", "click", "learning_rate", "batch_size", "config.yaml"])
        checklist.append(
            CheckItem(
                id="hp_config_logging",
                category=CheckCategory.HYPERPARAMETERS,
                title="Hyperparameter Specification",
                description="Training hyperparameters are configurable via CLI args or config files.",
                status=CheckStatus.PASS if has_hparams else CheckStatus.WARN,
                severity=CheckSeverity.HIGH,
                details="Hyperparameter configuration pattern found." if has_hparams else "Hyperparameters might be hardcoded.",
                remediation="Expose learning rate, batch size, and epoch count via argparse or config YAML." if not has_hparams else "",
            )
        )

        # 6. Checkpoints & Model Artifacts
        has_checkpointing = "torch.save" in combined_text or "save_pretrained" in combined_text or "checkpoint" in combined_text.lower()
        checklist.append(
            CheckItem(
                id="ckpt_state_save",
                category=CheckCategory.CHECKPOINTS,
                title="Model & Optimizer State Checkpointing",
                description="Saves model weights and training state for post-training validation.",
                status=CheckStatus.PASS if has_checkpointing else CheckStatus.WARN,
                severity=CheckSeverity.HIGH,
                details="Checkpoint persistence logic detected." if has_checkpointing else "No checkpoint saving calls found.",
                remediation="Save model and optimizer state dictionaries periodically using `torch.save()`." if not has_checkpointing else "",
            )
        )

        # Calculate category scores
        categories_dict: dict[CheckCategory, list[CheckItem]] = {}
        for item in checklist:
            categories_dict.setdefault(item.category, []).append(item)

        categories_scores: list[CategoryScore] = []
        total_score_sum = 0.0

        for cat in CheckCategory:
            items = categories_dict.get(cat, [])
            if not items:
                categories_scores.append(CategoryScore(category=cat, score=100.0, passed_checks=1, total_checks=1, status=CheckStatus.PASS))
                total_score_sum += 100.0
                continue

            passed = sum(1 for i in items if i.status == CheckStatus.PASS)
            warns = sum(1 for i in items if i.status == CheckStatus.WARN)
            score = max(0.0, min(100.0, ((passed * 1.0) + (warns * 0.6)) / len(items) * 100.0))
            if score >= 80:
                cat_status = CheckStatus.PASS
            elif score >= 60:
                cat_status = CheckStatus.WARN
            else:
                cat_status = CheckStatus.FAIL

            categories_scores.append(
                CategoryScore(
                    category=cat,
                    score=round(score, 1),
                    passed_checks=passed,
                    total_checks=len(items),
                    status=cat_status,
                )
            )
            total_score_sum += score

        overall_score = round(total_score_sum / len(CheckCategory), 1)
        if overall_score >= 95:
            grade = "A+"
        elif overall_score >= 85:
            grade = "A"
        elif overall_score >= 70:
            grade = "B"
        elif overall_score >= 50:
            grade = "C"
        else:
            grade = "F"

        detected_frameworks = []
        if "torch" in combined_text:
            detected_frameworks.append("PyTorch")
        if "jax" in combined_text:
            detected_frameworks.append("JAX")
        if "tensorflow" in combined_text or "keras" in combined_text:
            detected_frameworks.append("TensorFlow")
        if "transformers" in combined_text or "datasets" in combined_text:
            detected_frameworks.append("HuggingFace")
        if not detected_frameworks:
            detected_frameworks.append(request.framework_hint or "Python ML")

        report_id = f"rep_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC).isoformat()

        report = ReproducibilityAuditReport(
            id=report_id,
            project_id=project_id,
            created_at=now,
            overall_score=overall_score,
            grade=grade,
            venue=request.venue,
            categories=categories_scores,
            checklist=checklist,
            detected_frameworks=detected_frameworks,
            seeds_detected=seeds_found,
            cuda_requirements={"cuda_version": "12.1", "memory_mb": 8192, "deterministic_required": has_det_algo},
            dockerfile_recipe=cls.generate_dockerfile(GenerateDockerfileRequest()),
            conda_recipe=cls.generate_conda_env(),
            badge_markdown=cls.generate_badge_markdown(overall_score, grade),
            badge_svg=cls.generate_badge_svg(overall_score, grade),
        )
        report.latex_appendix = cls.generate_latex_appendix(GenerateAppendixRequest(report_id=report_id), report)

        store = cls._get_project_store(project_id)
        store[report_id] = report
        return report
