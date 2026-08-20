"""Evaluation metrics and statistical aggregation for OpenMLR agent benchmarks.

Provides precision metric calculations for paper reproduction deltas,
kernel speedup ratios, hypothesis rubric scoring, and aggregated benchmark suites.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MetricType(str, Enum):
    """Types of evaluation metrics in OpenMLR benchmarks."""

    REPRODUCTION_DELTA = "reproduction_delta"
    SPEEDUP_RATIO = "speedup_ratio"
    MEMORY_RATIO = "memory_ratio"
    HYPOTHESIS_NOVELTY = "hypothesis_novelty"
    HYPOTHESIS_QUALITY = "hypothesis_quality"
    ACCURACY = "accuracy"
    LOSS = "loss"
    MAPE = "mape"
    EXECUTION_TIME = "execution_time"


@dataclass
class MetricTolerance:
    """Tolerance boundaries for reproduction and performance validation."""

    relative_tolerance: float = 0.05  # Default: within 5% relative error
    absolute_tolerance: float = 0.02
    min_threshold: float | None = None
    max_threshold: float | None = None

    def is_within_tolerance(self, target: float, actual: float) -> bool:
        """Check if an actual value is within tolerance of the target."""
        if math.isclose(target, 0.0, abs_tol=1e-9):
            return abs(actual) <= self.absolute_tolerance
        rel_diff = abs(actual - target) / abs(target)
        if rel_diff <= self.relative_tolerance:
            return True
        return abs(actual - target) <= self.absolute_tolerance


@dataclass
class ReproductionMetric:
    """Evaluates how closely an agent's run reproduced reported paper metrics."""

    metric_name: str
    reported_value: float
    reproduced_value: float
    tolerance: MetricTolerance = field(default_factory=MetricTolerance)
    lower_is_better: bool = False

    @property
    def absolute_delta(self) -> float:
        return abs(self.reproduced_value - self.reported_value)

    @property
    def relative_delta(self) -> float:
        if math.isclose(self.reported_value, 0.0, abs_tol=1e-9):
            return abs(self.reproduced_value)
        return abs(self.reproduced_value - self.reported_value) / abs(self.reported_value)

    @property
    def percentage_error(self) -> float:
        return self.relative_delta * 100.0

    @property
    def is_successful(self) -> bool:
        # If target has directional preference (e.g. higher accuracy or lower loss is even better)
        if self.lower_is_better and self.reproduced_value < self.reported_value:
            return True
        if not self.lower_is_better and self.reproduced_value > self.reported_value:
            return True
        return self.tolerance.is_within_tolerance(self.reported_value, self.reproduced_value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "reported_value": self.reported_value,
            "reproduced_value": self.reproduced_value,
            "absolute_delta": round(self.absolute_delta, 6),
            "relative_delta": round(self.relative_delta, 6),
            "percentage_error": round(self.percentage_error, 2),
            "is_successful": self.is_successful,
            "lower_is_better": self.lower_is_better,
        }


@dataclass
class SpeedupMetric:
    """Evaluates kernel / model optimization performance improvements."""

    baseline_latency_ms: float
    optimized_latency_ms: float
    target_speedup: float = 1.5
    baseline_memory_mb: float | None = None
    optimized_memory_mb: float | None = None
    numerical_correctness_passed: bool = True
    max_relative_numerical_error: float = 0.0

    @property
    def speedup_ratio(self) -> float:
        if self.optimized_latency_ms <= 0.0:
            return 0.0
        return self.baseline_latency_ms / self.optimized_latency_ms

    @property
    def latency_reduction_pct(self) -> float:
        if self.baseline_latency_ms <= 0.0:
            return 0.0
        return max(0.0, (1.0 - (self.optimized_latency_ms / self.baseline_latency_ms)) * 100.0)

    @property
    def memory_reduction_ratio(self) -> float | None:
        if self.baseline_memory_mb and self.optimized_memory_mb and self.optimized_memory_mb > 0:
            return self.baseline_memory_mb / self.optimized_memory_mb
        return None

    @property
    def is_successful(self) -> bool:
        if not self.numerical_correctness_passed:
            return False
        return self.speedup_ratio >= self.target_speedup

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline_latency_ms": round(self.baseline_latency_ms, 4),
            "optimized_latency_ms": round(self.optimized_latency_ms, 4),
            "speedup_ratio": round(self.speedup_ratio, 3),
            "target_speedup": self.target_speedup,
            "latency_reduction_pct": round(self.latency_reduction_pct, 2),
            "memory_reduction_ratio": round(self.memory_reduction_ratio, 3)
            if self.memory_reduction_ratio is not None
            else None,
            "numerical_correctness_passed": self.numerical_correctness_passed,
            "max_relative_numerical_error": self.max_relative_numerical_error,
            "is_successful": self.is_successful,
        }


@dataclass
class HypothesisMetric:
    """Evaluates quality and rigor of agent-formulated scientific hypotheses."""

    novelty_score: float  # 0.0 - 1.0
    soundness_score: float  # 0.0 - 1.0 (Theoretical rigor & plausibility)
    testability_score: float  # 0.0 - 1.0 (Actionable experimental design)
    clarity_score: float  # 0.0 - 1.0
    relevance_score: float = 1.0  # 0.0 - 1.0
    min_passing_score: float = 0.70

    @property
    def composite_score(self) -> float:
        # Weighted composite score
        weights = {
            "novelty": 0.30,
            "soundness": 0.30,
            "testability": 0.25,
            "clarity": 0.15,
        }
        score = (
            self.novelty_score * weights["novelty"]
            + self.soundness_score * weights["soundness"]
            + self.testability_score * weights["testability"]
            + self.clarity_score * weights["clarity"]
        ) * self.relevance_score
        return max(0.0, min(1.0, score))

    @property
    def is_successful(self) -> bool:
        return self.composite_score >= self.min_passing_score

    def to_dict(self) -> dict[str, Any]:
        return {
            "novelty_score": round(self.novelty_score, 3),
            "soundness_score": round(self.soundness_score, 3),
            "testability_score": round(self.testability_score, 3),
            "clarity_score": round(self.clarity_score, 3),
            "relevance_score": round(self.relevance_score, 3),
            "composite_score": round(self.composite_score, 3),
            "min_passing_score": self.min_passing_score,
            "is_successful": self.is_successful,
        }


@dataclass
class BenchmarkAggregateSummary:
    """Statistical summary of benchmark execution across multiple tasks."""

    total_tasks: int = 0
    passed_tasks: int = 0
    failed_tasks: int = 0
    errored_tasks: int = 0
    total_execution_time_s: float = 0.0
    task_latencies_s: list[float] = field(default_factory=list)
    speedup_ratios: list[float] = field(default_factory=list)
    reproduction_percentage_errors: list[float] = field(default_factory=list)
    hypothesis_scores: list[float] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return self.passed_tasks / self.total_tasks

    @property
    def mean_task_latency_s(self) -> float:
        if not self.task_latencies_s:
            return 0.0
        return sum(self.task_latencies_s) / len(self.task_latencies_s)

    @property
    def mean_speedup(self) -> float:
        if not self.speedup_ratios:
            return 0.0
        return sum(self.speedup_ratios) / len(self.speedup_ratios)

    @property
    def mean_reproduction_mape(self) -> float:
        if not self.reproduction_percentage_errors:
            return 0.0
        return sum(self.reproduction_percentage_errors) / len(self.reproduction_percentage_errors)

    @property
    def mean_hypothesis_score(self) -> float:
        if not self.hypothesis_scores:
            return 0.0
        return sum(self.hypothesis_scores) / len(self.hypothesis_scores)

    def calculate_confidence_interval(
        self, values: list[float], confidence: float = 0.95
    ) -> tuple[float, float]:
        """Compute normal/t-distribution confidence interval for a list of values."""
        if not values:
            return (0.0, 0.0)
        n = len(values)
        if n == 1:
            return (values[0], values[0])
        mean = sum(values) / n
        variance = sum((x - mean) ** 2 for x in values) / (n - 1)
        std_dev = math.sqrt(variance)
        # Approximate z-score for 95% = 1.96
        z = 1.96 if math.isclose(confidence, 0.95, abs_tol=1e-5) else 2.576
        margin = z * (std_dev / math.sqrt(n))
        return (max(0.0, mean - margin), mean + margin)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_tasks": self.total_tasks,
            "passed_tasks": self.passed_tasks,
            "failed_tasks": self.failed_tasks,
            "errored_tasks": self.errored_tasks,
            "pass_rate": round(self.pass_rate, 4),
            "pass_rate_percentage": round(self.pass_rate * 100.0, 2),
            "total_execution_time_s": round(self.total_execution_time_s, 2),
            "mean_task_latency_s": round(self.mean_task_latency_s, 3),
            "mean_speedup": round(self.mean_speedup, 3) if self.speedup_ratios else None,
            "mean_reproduction_mape": round(self.mean_reproduction_mape, 2)
            if self.reproduction_percentage_errors
            else None,
            "mean_hypothesis_score": round(self.mean_hypothesis_score, 3)
            if self.hypothesis_scores
            else None,
        }
