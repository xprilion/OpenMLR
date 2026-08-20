"""Core Benchmark Harness for OpenMLR ML Agent Evaluation.

Orchestrates systematic benchmark execution across paper reproduction,
kernel optimization, and scientific hypothesis discovery suites.
"""

from __future__ import annotations

import asyncio
import datetime
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .metrics import BenchmarkAggregateSummary
from .tasks import (
    COT_SELF_CONSISTENCY_HYPOTHESIS_TASK,
    FLASH_ATTENTION_SIMPLIFIED_TASK,
    FUSED_SOFTMAX_DROPOUT_TASK,
    LAYER_NORM_KERNEL_TASK,
    NANOGPT_SHAKESPEARE_TASK,
    RESNET18_CIFAR10_TASK,
    VIT_PATCH_DROPOUT_HYPOTHESIS_TASK,
    BenchmarkTaskBase,
    TaskCategory,
    TaskResult,
    TaskStatus,
)

logger = logging.getLogger("openmlr.eval.harness")


@dataclass
class BenchmarkSuite:
    """A curated collection of benchmark tasks for evaluation."""

    name: str
    description: str
    version: str = "1.0.0"
    tasks: list[BenchmarkTaskBase] = field(default_factory=list)

    def add_task(self, task: BenchmarkTaskBase) -> None:
        self.tasks.append(task)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "total_tasks": len(self.tasks),
            "tasks": [t.to_dict() for t in self.tasks],
        }


# Standard Benchmark Suites
StandardReproductionSuite = BenchmarkSuite(
    name="Standard Paper Reproduction Suite",
    description="Evaluates empirical accuracy reproduction on ResNet-18 and NanoGPT.",
    tasks=[RESNET18_CIFAR10_TASK, NANOGPT_SHAKESPEARE_TASK],
)

StandardOptimizationSuite = BenchmarkSuite(
    name="Standard Kernel Optimization Suite",
    description="Evaluates kernel acceleration on Fused Softmax/Dropout and FlashAttention.",
    tasks=[FUSED_SOFTMAX_DROPOUT_TASK, FLASH_ATTENTION_SIMPLIFIED_TASK, LAYER_NORM_KERNEL_TASK],
)

StandardHypothesisSuite = BenchmarkSuite(
    name="Standard Scientific Hypothesis Suite",
    description="Evaluates autonomous formulation of novel ablation hypotheses.",
    tasks=[VIT_PATCH_DROPOUT_HYPOTHESIS_TASK, COT_SELF_CONSISTENCY_HYPOTHESIS_TASK],
)

FullOpenMLRBenchmarkSuite = BenchmarkSuite(
    name="OpenMLR Comprehensive Research Harness Suite",
    description="Full evaluation suite encompassing reproduction, optimization, and hypothesis discovery.",
    tasks=[
        RESNET18_CIFAR10_TASK,
        NANOGPT_SHAKESPEARE_TASK,
        FUSED_SOFTMAX_DROPOUT_TASK,
        FLASH_ATTENTION_SIMPLIFIED_TASK,
        LAYER_NORM_KERNEL_TASK,
        VIT_PATCH_DROPOUT_HYPOTHESIS_TASK,
        COT_SELF_CONSISTENCY_HYPOTHESIS_TASK,
    ],
)


@dataclass
class BenchmarkReport:
    """Comprehensive report summarizing benchmark suite execution."""

    suite_name: str
    timestamp: str
    summary: BenchmarkAggregateSummary
    results: list[TaskResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "suite_name": self.suite_name,
            "timestamp": self.timestamp,
            "summary": self.summary.to_dict(),
            "results": [r.to_dict() for r in self.results],
            "metadata": self.metadata,
        }

    def to_markdown(self) -> str:
        """Generate a clean GitHub/Markdown formatted scorecard."""
        s = self.summary
        md = [
            f"# OpenMLR Agent Benchmark Scorecard: {self.suite_name}",
            f"\n*Executed at: {self.timestamp}*\n",
            "## 📊 Executive Summary\n",
            "| Metric | Result |",
            "| :--- | :--- |",
            f"| **Overall Pass Rate** | **{s.pass_rate * 100.0:.1f}%** ({s.passed_tasks}/{s.total_tasks} tasks) |",
            f"| **Total Execution Time** | {s.total_execution_time_s:.2f}s |",
            f"| **Mean Task Latency** | {s.mean_task_latency_s:.2f}s |",
        ]
        if s.speedup_ratios:
            md.append(f"| **Average Kernel Speedup** | **{s.mean_speedup:.2f}x** |")
        if s.reproduction_percentage_errors:
            md.append(f"| **Mean Reproduction Error (MAPE)** | {s.mean_reproduction_mape:.2f}% |")
        if s.hypothesis_scores:
            md.append(f"| **Mean Hypothesis Score** | {s.mean_hypothesis_score:.2f} / 1.00 |")

        md.append("\n## 📋 Detailed Task Breakdown\n")
        md.append("| Task ID | Category | Status | Score | Duration | Key Metrics |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- |")

        for r in self.results:
            status_emoji = "✅ PASS" if r.success else "❌ FAIL"
            if r.status == TaskStatus.ERROR:
                status_emoji = "⚠️ ERROR"
            elif r.status == TaskStatus.TIMEOUT:
                status_emoji = "⏱️ TIMEOUT"

            metric_str = ""
            if r.category == TaskCategory.OPTIMIZATION and "speedup_ratio" in r.metrics:
                metric_str = f"Speedup: {r.metrics['speedup_ratio']}x"
            elif r.category == TaskCategory.HYPOTHESIS and "composite_score" in r.metrics:
                metric_str = f"Quality: {r.metrics['composite_score']:.2f}"
            elif r.category == TaskCategory.REPRODUCTION:
                metric_str = f"Passed metrics: {r.diagnostics.get('metrics_passed', 0)}/{r.diagnostics.get('metrics_evaluated', 0)}"

            md.append(
                f"| `{r.task_id}` | {r.category.value} | {status_emoji} | "
                f"{r.score:.2f} | {r.execution_time_s:.2f}s | {metric_str} |"
            )

        return "\n".join(md)


def _accumulate_category_metrics(summary: BenchmarkAggregateSummary, r: TaskResult) -> None:
    """Extract category-specific metrics from a task result into summary."""
    if r.category == TaskCategory.OPTIMIZATION and "speedup_ratio" in r.metrics:
        summary.speedup_ratios.append(r.metrics["speedup_ratio"])
    elif r.category == TaskCategory.HYPOTHESIS and "composite_score" in r.metrics:
        summary.hypothesis_scores.append(r.metrics["composite_score"])
    elif r.category == TaskCategory.REPRODUCTION:
        for m_val in r.metrics.values():
            if isinstance(m_val, dict) and "percentage_error" in m_val:
                summary.reproduction_percentage_errors.append(m_val["percentage_error"])


class BenchmarkHarness:
    """Harness for orchestrating agent evaluation benchmarks."""

    def __init__(self, default_timeout_seconds: float = 300.0) -> None:
        self.default_timeout_seconds = default_timeout_seconds

    async def run_single_task(
        self,
        task: BenchmarkTaskBase,
        agent_runner: Callable[[BenchmarkTaskBase], Awaitable[Any]],
    ) -> TaskResult:
        """Run a single benchmark task with timeout and error handling."""
        timeout_s = task.config.timeout_seconds or self.default_timeout_seconds
        start_time = asyncio.get_event_loop().time()
        try:
            # Execute agent runner wrapped in asyncio timeout
            agent_raw_output = await asyncio.wait_for(
                agent_runner(task),
                timeout=timeout_s,
            )
            # Evaluate output against benchmark task criteria
            result = await task.evaluate(agent_raw_output)
            return result
        except TimeoutError:
            logger.warning("Task %s timed out after %ss", task.id, timeout_s)
            return task.create_timeout_result(timeout_s)
        except Exception as e:
            logger.exception("Error executing task %s: %s", task.id, e)
            duration = asyncio.get_event_loop().time() - start_time
            return task.create_error_result(str(e), execution_time_s=duration)

    async def run_suite(
        self,
        suite: BenchmarkSuite,
        agent_runner: Callable[[BenchmarkTaskBase], Awaitable[Any]],
        max_concurrency: int = 4,
    ) -> BenchmarkReport:
        """Execute all tasks in a benchmark suite with bounded concurrency."""
        start_time = asyncio.get_event_loop().time()
        semaphore = asyncio.Semaphore(max_concurrency)

        async def _bounded_run(task: BenchmarkTaskBase) -> TaskResult:
            async with semaphore:
                return await self.run_single_task(task, agent_runner)

        tasks_coroutines = [_bounded_run(t) for t in suite.tasks]
        results: list[TaskResult] = await asyncio.gather(*tasks_coroutines)
        total_time_s = asyncio.get_event_loop().time() - start_time

        # Compile aggregate summary
        summary = BenchmarkAggregateSummary(
            total_tasks=len(results),
            passed_tasks=sum(1 for r in results if r.success),
            failed_tasks=sum(1 for r in results if not r.success and r.status in (TaskStatus.FAILED, TaskStatus.TIMEOUT)),
            errored_tasks=sum(1 for r in results if r.status == TaskStatus.ERROR),
            total_execution_time_s=total_time_s,
            task_latencies_s=[r.execution_time_s for r in results],
        )

        for r in results:
            _accumulate_category_metrics(summary, r)

        return BenchmarkReport(
            suite_name=suite.name,
            timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
            summary=summary,
            results=results,
            metadata={"version": suite.version, "tasks_count": len(suite.tasks)},
        )

    def export_report_json(self, report: BenchmarkReport, filepath: str | Path | None = None) -> dict[str, Any]:
        """Export benchmark report to JSON dictionary and optional file."""
        data = report.to_dict()
        if filepath:
            p = Path(filepath)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data

    def export_report_markdown(self, report: BenchmarkReport, filepath: str | Path | None = None) -> str:
        """Export benchmark report to markdown text and optional file."""
        md = report.to_markdown()
        if filepath:
            p = Path(filepath)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(md, encoding="utf-8")
        return md
