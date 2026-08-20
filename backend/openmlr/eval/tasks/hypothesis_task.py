"""Hypothesis Discovery and Research Formulation Benchmark Tasks for OpenMLR.

Evaluates an autonomous ML agent's ability to formulate testable, novel scientific hypotheses
and experimental designs on standard ML problems and datasets.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ..metrics import HypothesisMetric
from .base import (
    BenchmarkTaskBase,
    TaskCategory,
    TaskConfig,
    TaskDifficulty,
    TaskResult,
    TaskStatus,
)


@dataclass
class ResearchProblemContext:
    """Context describing the research problem for hypothesis discovery."""

    problem_statement: str
    dataset: str
    current_baseline_method: str
    known_limitations: list[str] = field(default_factory=list)
    key_evaluation_metrics: list[str] = field(default_factory=list)


class HypothesisDiscoveryTask(BenchmarkTaskBase):
    """Benchmark task evaluating automated scientific hypothesis formulation."""

    def __init__(
        self,
        config: TaskConfig,
        problem: ResearchProblemContext,
        evaluator_fn: Callable[[dict[str, Any]], HypothesisMetric] | None = None,
    ) -> None:
        super().__init__(config)
        self.problem = problem
        self.evaluator_fn = evaluator_fn

    @classmethod
    def create(
        cls,
        task_id: str,
        name: str,
        description: str,
        problem: ResearchProblemContext,
        difficulty: TaskDifficulty = TaskDifficulty.MEDIUM,
        timeout_seconds: float = 300.0,
        tags: list[str] | None = None,
    ) -> HypothesisDiscoveryTask:
        config = TaskConfig(
            id=task_id,
            name=name,
            description=description,
            category=TaskCategory.HYPOTHESIS,
            difficulty=difficulty,
            timeout_seconds=timeout_seconds,
            tags=tags or ["hypothesis", "scientific-discovery", "ablation-design"],
            dataset=problem.dataset,
            domain="Automated Scientific Discovery",
            metadata={
                "dataset": problem.dataset,
                "baseline_method": problem.current_baseline_method,
            },
        )
        return cls(config=config, problem=problem)

    def _evaluate_heuristic_quality(self, data: dict[str, Any]) -> HypothesisMetric:
        """Heuristic rule-based quality evaluation when external LLM evaluator is not supplied."""
        hypothesis_text = data.get("hypothesis", "")
        rationale_text = data.get("rationale", "") or data.get("theoretical_rationale", "")
        experiments = data.get("proposed_experiments", []) or data.get("experiments", [])

        # 1. Clarity & Length check
        words = len(hypothesis_text.split()) + len(rationale_text.split())
        clarity_score = min(1.0, max(0.4, words / 150.0))

        # 2. Soundness / Rationale check
        soundness_keywords = ["because", "therefore", "gradient", "loss", "representation", "inductive bias", "regularization", "variance", "convergence"]
        soundness_matches = sum(1 for kw in soundness_keywords if kw in rationale_text.lower())
        soundness_score = min(1.0, max(0.3, 0.4 + 0.1 * soundness_matches))

        # 3. Testability / Actionability check
        has_ablation = any("ablat" in str(e).lower() or "baseline" in str(e).lower() for e in experiments)
        has_metric = any(m.lower() in str(experiments).lower() or m.lower() in rationale_text.lower() for m in self.problem.key_evaluation_metrics)
        testability_score = 0.5
        if experiments:
            testability_score += 0.2
        if has_ablation:
            testability_score += 0.15
        if has_metric:
            testability_score += 0.15
        testability_score = min(1.0, testability_score)

        # 4. Novelty score
        novelty_score = 0.75
        if "novel" in hypothesis_text.lower() or "propose" in hypothesis_text.lower():
            novelty_score = 0.85

        return HypothesisMetric(
            novelty_score=novelty_score,
            soundness_score=soundness_score,
            testability_score=testability_score,
            clarity_score=clarity_score,
            min_passing_score=0.70,
        )

    async def evaluate(self, agent_output: Any) -> TaskResult:
        """Evaluate agent's proposed hypothesis and experimental proposal."""
        start_time = time.time()
        try:
            if isinstance(agent_output, dict) and "error" in agent_output:
                return self.create_error_result(
                    error_message=str(agent_output["error"]),
                    execution_time_s=time.time() - start_time,
                )

            data: dict[str, Any] = {}
            if isinstance(agent_output, dict):
                data = agent_output
            elif isinstance(agent_output, str):
                data = {"hypothesis": agent_output, "rationale": agent_output}

            if not data.get("hypothesis"):
                return TaskResult(
                    task_id=self.id,
                    category=self.category,
                    status=TaskStatus.FAILED,
                    success=False,
                    score=0.0,
                    execution_time_s=time.time() - start_time,
                    error_message="Agent output does not contain a formulated hypothesis",
                    raw_output=str(agent_output)[:2000],
                )

            if self.evaluator_fn:
                metric = self.evaluator_fn(data)
            else:
                metric = self._evaluate_heuristic_quality(data)

            is_success = metric.is_successful

            return TaskResult(
                task_id=self.id,
                category=self.category,
                status=TaskStatus.COMPLETED if is_success else TaskStatus.FAILED,
                success=is_success,
                score=metric.composite_score,
                metrics=metric.to_dict(),
                execution_time_s=time.time() - start_time,
                diagnostics={
                    "dataset": self.problem.dataset,
                    "baseline_method": self.problem.current_baseline_method,
                    "composite_score": metric.composite_score,
                },
                raw_output=str(agent_output)[:2000],
            )
        except Exception as e:
            return self.create_error_result(str(e), execution_time_s=time.time() - start_time)


# Predefined Standard Hypothesis Discovery Benchmark Tasks
VIT_PATCH_DROPOUT_HYPOTHESIS_TASK = HypothesisDiscoveryTask.create(
    task_id="hypothesis_vit_patch_dropout",
    name="Vision Transformer Stochastic Patch Dropping",
    description="Formulate hypothesis for improving ViT training efficiency and robustness via structured patch masking.",
    problem=ResearchProblemContext(
        problem_statement="Standard Vision Transformers suffer from quadratic computational complexity with respect to token length during fine-tuning.",
        dataset="ImageNet-1K",
        current_baseline_method="Standard ViT-B/16 with full token attention",
        known_limitations=["High peak memory during training", "Redundancy in uniform background patches"],
        key_evaluation_metrics=["top1_accuracy", "throughput_img_per_sec", "peak_vram_gb"],
    ),
    difficulty=TaskDifficulty.MEDIUM,
)

COT_SELF_CONSISTENCY_HYPOTHESIS_TASK = HypothesisDiscoveryTask.create(
    task_id="hypothesis_cot_reasoning_verification",
    name="Chain-of-Thought Verification Mechanism",
    description="Formulate hypothesis on mitigating intermediate reasoning hallucination in multi-step mathematical reasoning.",
    problem=ResearchProblemContext(
        problem_statement="Large language models frequently generate mathematically invalid steps within Chain-of-Thought rationales without self-correction.",
        dataset="GSM8K",
        current_baseline_method="Standard Greedy CoT and Self-Consistency Majority Voting",
        known_limitations=["Majority voting cannot catch shared systematic misconceptions"],
        key_evaluation_metrics=["accuracy", "reasoning_step_precision", "sample_efficiency"],
    ),
    difficulty=TaskDifficulty.HARD,
)
