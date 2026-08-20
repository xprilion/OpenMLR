"""Tests for the OpenMLR benchmark harness and suite execution."""

import asyncio
from pathlib import Path

import pytest

from openmlr.eval.benchmark_harness import (
    BenchmarkHarness,
    FullOpenMLRBenchmarkSuite,
    StandardHypothesisSuite,
    StandardOptimizationSuite,
    StandardReproductionSuite,
)
from openmlr.eval.tasks import (
    RESNET18_CIFAR10_TASK,
    BenchmarkTaskBase,
    TaskCategory,
    TaskStatus,
)


class TestBenchmarkHarness:
    @pytest.mark.asyncio
    async def test_run_single_task_success(self):
        harness = BenchmarkHarness()

        async def mock_agent_runner(task: BenchmarkTaskBase):
            if task.category == TaskCategory.REPRODUCTION:
                return {"accuracy": 0.930, "test_loss": 0.320}
            return {}

        result = await harness.run_single_task(RESNET18_CIFAR10_TASK, mock_agent_runner)
        assert result.success is True
        assert result.status == TaskStatus.COMPLETED
        assert result.score >= 0.95

    @pytest.mark.asyncio
    async def test_run_single_task_timeout(self):
        harness = BenchmarkHarness(default_timeout_seconds=0.1)
        RESNET18_CIFAR10_TASK.config.timeout_seconds = 0.1

        async def hanging_agent_runner(task: BenchmarkTaskBase):
            await asyncio.sleep(1.0)
            return {"accuracy": 0.930}

        result = await harness.run_single_task(RESNET18_CIFAR10_TASK, hanging_agent_runner)
        assert result.success is False
        assert result.status == TaskStatus.TIMEOUT

    @pytest.mark.asyncio
    async def test_run_single_task_handles_exception(self):
        harness = BenchmarkHarness()

        async def crashing_agent_runner(task: BenchmarkTaskBase):
            raise RuntimeError("Unexpected agent crash during execution")

        result = await harness.run_single_task(RESNET18_CIFAR10_TASK, crashing_agent_runner)
        assert result.success is False
        assert result.status == TaskStatus.ERROR
        assert result.error_message is not None
        assert "Unexpected agent crash" in result.error_message

    @pytest.mark.asyncio
    async def test_run_suite_and_aggregate_summary(self):
        harness = BenchmarkHarness()
        suite = StandardOptimizationSuite

        async def mock_opt_agent(task: BenchmarkTaskBase):
            if task.id == "optimization_fused_softmax_dropout":
                return {"optimized_latency_ms": 6.0, "numerical_correctness": True}
            elif task.id == "optimization_flash_attention_tiling":
                return {"optimized_latency_ms": 14.0, "numerical_correctness": True}
            elif task.id == "optimization_fused_layernorm":
                return {"optimized_latency_ms": 4.5, "numerical_correctness": True}
            return {}

        report = await harness.run_suite(suite, mock_opt_agent, max_concurrency=2)
        assert report.suite_name == suite.name
        assert len(report.results) == len(suite.tasks)
        assert report.summary.total_tasks == 3
        assert report.summary.passed_tasks == 3
        assert report.summary.pass_rate == 1.0
        assert report.summary.mean_speedup > 1.5

    @pytest.mark.asyncio
    async def test_export_report_json_and_markdown(self, tmp_path: Path):
        harness = BenchmarkHarness()
        suite = StandardReproductionSuite

        async def mock_agent(task: BenchmarkTaskBase):
            return {"accuracy": 0.925, "test_loss": 0.320, "val_loss": 1.46, "train_loss": 1.15}

        report = await harness.run_suite(suite, mock_agent)

        json_file = tmp_path / "report.json"
        md_file = tmp_path / "report.md"

        json_data = harness.export_report_json(report, json_file)
        md_text = harness.export_report_markdown(report, md_file)

        assert json_file.exists()
        assert md_file.exists()
        assert json_data["summary"]["total_tasks"] == 2
        assert "# OpenMLR Agent Benchmark Scorecard" in md_text
        assert "Executive Summary" in md_text


class TestStandardSuites:
    def test_suites_structure(self):
        assert len(StandardReproductionSuite.tasks) >= 2
        assert len(StandardOptimizationSuite.tasks) >= 3
        assert len(StandardHypothesisSuite.tasks) >= 2
        assert len(FullOpenMLRBenchmarkSuite.tasks) >= 7

        suite_dict = FullOpenMLRBenchmarkSuite.to_dict()
        assert suite_dict["total_tasks"] == len(FullOpenMLRBenchmarkSuite.tasks)
