"""Tests for individual benchmark tasks in OpenMLR."""

import pytest

from openmlr.eval.metrics import HypothesisMetric
from openmlr.eval.tasks import (
    FUSED_SOFTMAX_DROPOUT_TASK,
    RESNET18_CIFAR10_TASK,
    VIT_PATCH_DROPOUT_HYPOTHESIS_TASK,
    HypothesisDiscoveryTask,
    PaperMetadata,
    PaperReproductionTask,
    ResearchProblemContext,
    TaskCategory,
    TaskStatus,
    get_benchmark_task,
    list_benchmark_tasks,
    register_benchmark_task,
)


class TestPaperReproductionTask:
    @pytest.mark.asyncio
    async def test_reproduction_evaluation_success_with_dict(self):
        task = RESNET18_CIFAR10_TASK
        agent_output = {"accuracy": 0.929, "test_loss": 0.315}
        result = await task.evaluate(agent_output)

        assert result.success is True
        assert result.status == TaskStatus.COMPLETED
        assert result.score > 0.9
        assert "accuracy" in result.metrics
        assert result.metrics["accuracy"]["is_successful"] is True

    @pytest.mark.asyncio
    async def test_reproduction_evaluation_from_string_logs(self):
        task = RESNET18_CIFAR10_TASK
        logs = """
        [Epoch 100/100] Training Complete.
        Evaluating on Test Set...
        test_loss: 0.322
        accuracy: 0.931
        """
        result = await task.evaluate(logs)
        assert result.success is True
        assert result.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_reproduction_evaluation_failure_missing_metrics(self):
        task = RESNET18_CIFAR10_TASK
        result = await task.evaluate("Invalid output with no metrics")
        assert result.success is False
        assert result.status == TaskStatus.FAILED
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_reproduction_evaluation_error_handling(self):
        task = RESNET18_CIFAR10_TASK
        result = await task.evaluate({"error": "CUDA OOM in training loop"})
        assert result.success is False
        assert result.status == TaskStatus.ERROR
        assert result.error_message is not None
        assert "CUDA OOM" in result.error_message


class TestKernelOptimizationTask:
    @pytest.mark.asyncio
    async def test_optimization_evaluation_success(self):
        task = FUSED_SOFTMAX_DROPOUT_TASK
        # baseline is 12.4ms, target speedup is 1.5x -> 6.2ms is 2.0x speedup
        agent_output = {
            "optimized_latency_ms": 6.2,
            "numerical_correctness": True,
            "max_relative_numerical_error": 1e-5,
            "optimized_memory_mb": 450.0,
        }
        result = await task.evaluate(agent_output)
        assert result.success is True
        assert result.status == TaskStatus.COMPLETED
        assert result.metrics["speedup_ratio"] == pytest.approx(2.0, rel=1e-2)
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_optimization_fails_on_numerical_inaccuracy(self):
        task = FUSED_SOFTMAX_DROPOUT_TASK
        agent_output = {
            "optimized_latency_ms": 4.0,  # fast but incorrect
            "numerical_correctness": False,
        }
        result = await task.evaluate(agent_output)
        assert result.success is False
        assert result.status == TaskStatus.FAILED
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_optimization_fails_below_speedup_target(self):
        task = FUSED_SOFTMAX_DROPOUT_TASK
        agent_output = {
            "optimized_latency_ms": 11.0,  # ~1.12x speedup (< 1.5x)
            "numerical_correctness": True,
        }
        result = await task.evaluate(agent_output)
        assert result.success is False
        assert result.status == TaskStatus.FAILED


class TestHypothesisDiscoveryTask:
    @pytest.mark.asyncio
    async def test_heuristic_hypothesis_evaluation(self):
        task = VIT_PATCH_DROPOUT_HYPOTHESIS_TASK
        agent_output = {
            "hypothesis": "We propose stochastic spatial patch dropping to regularize ViT attention and reduce computational variance.",
            "rationale": "Because uniform background patches carry high redundancy, dropping 30% of patches acts as effective representation regularization and speeds up gradient convergence.",
            "proposed_experiments": [
                "Baseline ViT-B/16 on ImageNet-1K with full tokens",
                "Ablation study varying patch drop rate from 10% to 50%",
                "Measure top1_accuracy, throughput_img_per_sec, and peak_vram_gb",
            ],
        }
        result = await task.evaluate(agent_output)
        assert result.status == TaskStatus.COMPLETED
        assert result.success is True
        assert result.score >= 0.70

    @pytest.mark.asyncio
    async def test_custom_evaluator_fn(self):
        problem = ResearchProblemContext(
            problem_statement="Test statement",
            dataset="CIFAR-10",
            current_baseline_method="CNN",
        )
        task = HypothesisDiscoveryTask.create(
            task_id="custom_hyp_task",
            name="Custom Hyp",
            description="Custom",
            problem=problem,
        )
        task.evaluator_fn = lambda d: HypothesisMetric(
            novelty_score=0.95,
            soundness_score=0.90,
            testability_score=0.90,
            clarity_score=0.95,
        )
        result = await task.evaluate({"hypothesis": "Custom idea"})
        assert result.success is True
        assert result.score > 0.90


class TestTaskRegistry:
    def test_registry_lookups_and_filters(self):
        task = get_benchmark_task("reproduction_resnet18_cifar10")
        assert task is not None
        assert task.category == TaskCategory.REPRODUCTION

        repro_tasks = list_benchmark_tasks(category=TaskCategory.REPRODUCTION)
        assert len(repro_tasks) >= 2

        opt_tasks = list_benchmark_tasks(category=TaskCategory.OPTIMIZATION)
        assert len(opt_tasks) >= 2

        hyp_tasks = list_benchmark_tasks(category=TaskCategory.HYPOTHESIS)
        assert len(hyp_tasks) >= 2

    def test_register_custom_task(self):
        custom_task = PaperReproductionTask.create(
            task_id="custom_unique_task",
            name="Unique Custom Task",
            description="A custom benchmark task",
            paper=PaperMetadata(title="Test", arxiv_id="1234.5678"),
            target_metrics={"accuracy": 0.99},
        )
        register_benchmark_task(custom_task)
        fetched = get_benchmark_task("custom_unique_task")
        assert fetched is not None
        assert fetched.name == "Unique Custom Task"
