"""Paper Reproduction Benchmark Tasks for OpenMLR.

Evaluates an autonomous ML research agent's ability to reproduce published
empirical results from academic papers given a reference codebase or specification.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

from ..metrics import MetricTolerance, ReproductionMetric
from .base import (
    BenchmarkTaskBase,
    TaskCategory,
    TaskConfig,
    TaskDifficulty,
    TaskResult,
    TaskStatus,
)


@dataclass
class PaperMetadata:
    """Metadata describing the paper to be reproduced."""

    title: str
    arxiv_id: str
    authors: list[str] = field(default_factory=list)
    year: int = 2023
    reference_repo_url: str = ""
    baseline_command: str = ""


class PaperReproductionTask(BenchmarkTaskBase):
    """Benchmark task evaluating reproduction of published empirical findings."""

    def __init__(
        self,
        config: TaskConfig,
        paper: PaperMetadata,
        target_metrics: dict[str, float],
        metric_tolerances: dict[str, MetricTolerance] | None = None,
        lower_is_better_metrics: list[str] | None = None,
        starter_code: str = "",
    ) -> None:
        super().__init__(config)
        self.paper = paper
        self.target_metrics = target_metrics
        self.metric_tolerances = metric_tolerances or {}
        self.lower_is_better_metrics = lower_is_better_metrics or ["loss", "val_loss", "test_loss", "perplexity", "latency"]
        self.starter_code = starter_code

    @classmethod
    def create(
        cls,
        task_id: str,
        name: str,
        description: str,
        paper: PaperMetadata,
        target_metrics: dict[str, float],
        difficulty: TaskDifficulty = TaskDifficulty.MEDIUM,
        timeout_seconds: float = 600.0,
        dataset: str = "",
        metric_tolerances: dict[str, MetricTolerance] | None = None,
        tags: list[str] | None = None,
    ) -> PaperReproductionTask:
        config = TaskConfig(
            id=task_id,
            name=name,
            description=description,
            category=TaskCategory.REPRODUCTION,
            difficulty=difficulty,
            timeout_seconds=timeout_seconds,
            tags=tags or ["reproduction", "paper-benchmark"],
            dataset=dataset,
            domain="Empirical Deep Learning",
            metadata={
                "arxiv_id": paper.arxiv_id,
                "paper_title": paper.title,
                "target_metrics": target_metrics,
            },
        )
        return cls(
            config=config,
            paper=paper,
            target_metrics=target_metrics,
            metric_tolerances=metric_tolerances,
        )

    def extract_metrics_from_output(self, output: str | dict[str, Any]) -> dict[str, float]:
        """Extract numerical metrics from logs, JSON or stdout string."""
        if isinstance(output, dict):
            # Check if metrics are directly in the dictionary
            if "metrics" in output and isinstance(output["metrics"], dict):
                return {k: float(v) for k, v in output["metrics"].items() if isinstance(v, (int, float))}
            return {k: float(v) for k, v in output.items() if isinstance(v, (int, float))}

        extracted: dict[str, float] = {}
        # Common regex patterns for metric logging: e.g. "accuracy: 0.924", "val_loss = 0.352"
        patterns = [
            r"(?:final\s+|val\w*\s+|test\w*\s+)?([a-zA-Z0-9_-]+)\s*[:=]\s*([0-9]+\.?[0-9]*(?:[eE][-+]?[0-9]+)?)",
            r'"([a-zA-Z0-9_-]+)":\s*([0-9]+\.?[0-9]*)',
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, output, re.IGNORECASE):
                key = match.group(1).lower().strip()
                try:
                    val = float(match.group(2))
                    if key in self.target_metrics or any(m in key for m in self.target_metrics):
                        # Map to canonical target metric key if partial match
                        matched_key = next((m for m in self.target_metrics if m == key or m in key), key)
                        extracted[matched_key] = val
                except (ValueError, IndexError):
                    continue
        return extracted

    async def evaluate(self, agent_output: Any) -> TaskResult:
        """Evaluate agent output against paper targets."""
        start_time = time.time()
        try:
            if isinstance(agent_output, dict) and "error" in agent_output:
                return self.create_error_result(
                    error_message=str(agent_output["error"]),
                    execution_time_s=time.time() - start_time,
                )

            extracted_metrics = self.extract_metrics_from_output(agent_output)
            if not extracted_metrics:
                return TaskResult(
                    task_id=self.id,
                    category=self.category,
                    status=TaskStatus.FAILED,
                    success=False,
                    score=0.0,
                    execution_time_s=time.time() - start_time,
                    error_message="No matching evaluation metrics found in agent output",
                    raw_output=str(agent_output)[:2000],
                )

            metric_evaluations: dict[str, Any] = {}
            success_flags: list[bool] = []
            relative_errors: list[float] = []

            for metric_name, target_val in self.target_metrics.items():
                if metric_name in extracted_metrics:
                    actual_val = extracted_metrics[metric_name]
                    tol = self.metric_tolerances.get(metric_name, MetricTolerance(relative_tolerance=0.05))
                    lower_is_better = any(lib in metric_name.lower() for lib in self.lower_is_better_metrics)

                    eval_metric = ReproductionMetric(
                        metric_name=metric_name,
                        reported_value=target_val,
                        reproduced_value=actual_val,
                        tolerance=tol,
                        lower_is_better=lower_is_better,
                    )
                    metric_evaluations[metric_name] = eval_metric.to_dict()
                    success_flags.append(eval_metric.is_successful)
                    relative_errors.append(eval_metric.relative_delta)
                else:
                    # Missing reported metric
                    metric_evaluations[metric_name] = {
                        "reported_value": target_val,
                        "reproduced_value": None,
                        "is_successful": False,
                        "error": "Missing metric in agent output",
                    }
                    success_flags.append(False)
                    relative_errors.append(1.0)

            overall_success = all(success_flags) if success_flags else False
            avg_rel_error = sum(relative_errors) / len(relative_errors) if relative_errors else 1.0
            # Score is 1.0 minus average relative error clamped to [0, 1]
            normalized_score = max(0.0, min(1.0, 1.0 - avg_rel_error))

            return TaskResult(
                task_id=self.id,
                category=self.category,
                status=TaskStatus.COMPLETED if overall_success else TaskStatus.FAILED,
                success=overall_success,
                score=normalized_score,
                metrics=metric_evaluations,
                execution_time_s=time.time() - start_time,
                diagnostics={
                    "paper_title": self.paper.title,
                    "arxiv_id": self.paper.arxiv_id,
                    "metrics_evaluated": len(metric_evaluations),
                    "metrics_passed": sum(1 for s in success_flags if s),
                },
                raw_output=str(agent_output)[:2000],
            )
        except Exception as e:
            return self.create_error_result(str(e), execution_time_s=time.time() - start_time)


# Predefined Standard Paper Reproduction Benchmark Tasks
RESNET18_CIFAR10_TASK = PaperReproductionTask.create(
    task_id="reproduction_resnet18_cifar10",
    name="ResNet-18 CIFAR-10 Reproduction",
    description="Reproduce baseline top-1 test accuracy of ResNet-18 on CIFAR-10 dataset.",
    paper=PaperMetadata(
        title="Deep Residual Learning for Image Recognition",
        arxiv_id="1512.03385",
        authors=["Kaiming He", "Xiangyu Zhang", "Shaoqing Ren", "Jian Sun"],
        year=2015,
        baseline_command="python train_cifar.py --arch resnet18 --epochs 100",
    ),
    target_metrics={"accuracy": 0.930, "test_loss": 0.320},
    dataset="CIFAR-10",
    difficulty=TaskDifficulty.EASY,
)

NANOGPT_SHAKESPEARE_TASK = PaperReproductionTask.create(
    task_id="reproduction_nanogpt_shakespeare",
    name="NanoGPT Character-Level Shakespeare Reproduction",
    description="Train a 6-layer GPT model on Shakespeare and achieve validation loss below 1.48.",
    paper=PaperMetadata(
        title="Language Models are Unsupervised Multitask Learners",
        arxiv_id="gpt2-karpathy",
        authors=["OpenAI", "Andrej Karpathy"],
        year=2023,
        baseline_command="python train.py config/train_shakespeare_char.py",
    ),
    target_metrics={"val_loss": 1.47, "train_loss": 1.15},
    dataset="Shakespeare Char",
    difficulty=TaskDifficulty.MEDIUM,
)

BERT_SST2_TASK = PaperReproductionTask.create(
    task_id="reproduction_bert_sst2",
    name="BERT Fine-Tuning on SST-2 Benchmark",
    description="Fine-tune uncased BERT-base on SST-2 sentiment classification achieving >91.5% accuracy.",
    paper=PaperMetadata(
        title="BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
        arxiv_id="1810.04805",
        authors=["Jacob Devlin", "Ming-Wei Chang", "Kenton Lee", "Kristina Toutanova"],
        year=2018,
    ),
    target_metrics={"accuracy": 0.920, "val_loss": 0.280},
    dataset="GLUE SST-2",
    difficulty=TaskDifficulty.MEDIUM,
)
