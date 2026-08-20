"""Kernel and Model Optimization Benchmark Tasks for OpenMLR.

Evaluates an autonomous ML research agent's ability to optimize PyTorch/Triton/CUDA
kernels or inference pipelines to achieve >1.5x speedup while preserving numerical accuracy.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ..metrics import SpeedupMetric
from .base import (
    BenchmarkTaskBase,
    TaskCategory,
    TaskConfig,
    TaskDifficulty,
    TaskResult,
    TaskStatus,
)


@dataclass
class KernelSpecification:
    """Specification of a kernel optimization task."""

    kernel_name: str
    framework: str  # pytorch, triton, cuda
    input_shapes: list[tuple[int, ...]] = field(default_factory=list)
    baseline_code: str = ""
    baseline_latency_ms: float = 10.0
    baseline_memory_mb: float | None = None
    target_speedup: float = 1.5
    atol: float = 1e-4
    rtol: float = 1e-3


class KernelOptimizationTask(BenchmarkTaskBase):
    """Benchmark task evaluating kernel or pipeline runtime acceleration."""

    def __init__(
        self,
        config: TaskConfig,
        specification: KernelSpecification,
        verify_fn: Callable[[Any, Any], tuple[bool, float]] | None = None,
    ) -> None:
        super().__init__(config)
        self.specification = specification
        self.verify_fn = verify_fn

    @classmethod
    def create(
        cls,
        task_id: str,
        name: str,
        description: str,
        specification: KernelSpecification,
        difficulty: TaskDifficulty = TaskDifficulty.MEDIUM,
        timeout_seconds: float = 300.0,
        tags: list[str] | None = None,
    ) -> KernelOptimizationTask:
        config = TaskConfig(
            id=task_id,
            name=name,
            description=description,
            category=TaskCategory.OPTIMIZATION,
            difficulty=difficulty,
            timeout_seconds=timeout_seconds,
            tags=tags or ["optimization", "kernel", "cuda", "triton", "speedup"],
            domain="High-Performance ML & Kernel Engineering",
            metadata={
                "kernel_name": specification.kernel_name,
                "framework": specification.framework,
                "baseline_latency_ms": specification.baseline_latency_ms,
                "target_speedup": specification.target_speedup,
            },
        )
        return cls(config=config, specification=specification)

    async def evaluate(self, agent_output: Any) -> TaskResult:
        """Evaluate agent's optimized kernel implementation or latency measurement."""
        start_time = time.time()
        try:
            if isinstance(agent_output, dict) and "error" in agent_output:
                return self.create_error_result(
                    error_message=str(agent_output["error"]),
                    execution_time_s=time.time() - start_time,
                )

            # Agent output can be a dict with measured latency or code/bench results
            optimized_latency_ms = None
            numerical_passed = True
            max_num_error = 0.0
            optimized_memory_mb = None

            if isinstance(agent_output, dict):
                optimized_latency_ms = agent_output.get("optimized_latency_ms") or agent_output.get("latency_ms")
                if optimized_latency_ms is None and "speedup" in agent_output:
                    speedup_reported = float(agent_output["speedup"])
                    if speedup_reported > 0:
                        optimized_latency_ms = self.specification.baseline_latency_ms / speedup_reported

                numerical_passed = agent_output.get("numerical_correctness", True)
                max_num_error = agent_output.get("max_relative_numerical_error", 0.0)
                optimized_memory_mb = agent_output.get("optimized_memory_mb")
            elif isinstance(agent_output, (int, float)):
                optimized_latency_ms = float(agent_output)

            if optimized_latency_ms is None or optimized_latency_ms <= 0:
                return TaskResult(
                    task_id=self.id,
                    category=self.category,
                    status=TaskStatus.FAILED,
                    success=False,
                    score=0.0,
                    execution_time_s=time.time() - start_time,
                    error_message="Could not extract valid optimized latency from agent output",
                    raw_output=str(agent_output)[:2000],
                )

            speedup_metric = SpeedupMetric(
                baseline_latency_ms=self.specification.baseline_latency_ms,
                optimized_latency_ms=float(optimized_latency_ms),
                target_speedup=self.specification.target_speedup,
                baseline_memory_mb=self.specification.baseline_memory_mb,
                optimized_memory_mb=optimized_memory_mb,
                numerical_correctness_passed=numerical_passed,
                max_relative_numerical_error=max_num_error,
            )

            is_success = speedup_metric.is_successful
            # Normalized score: min(1.0, speedup / target_speedup) if numerical check passed
            score = 0.0
            if numerical_passed and speedup_metric.speedup_ratio > 0:
                score = min(1.0, speedup_metric.speedup_ratio / self.specification.target_speedup)

            return TaskResult(
                task_id=self.id,
                category=self.category,
                status=TaskStatus.COMPLETED if is_success else TaskStatus.FAILED,
                success=is_success,
                score=score,
                metrics=speedup_metric.to_dict(),
                execution_time_s=time.time() - start_time,
                diagnostics={
                    "kernel_name": self.specification.kernel_name,
                    "target_speedup": self.specification.target_speedup,
                    "achieved_speedup": speedup_metric.speedup_ratio,
                    "latency_reduction_pct": speedup_metric.latency_reduction_pct,
                },
                raw_output=str(agent_output)[:2000],
            )
        except Exception as e:
            return self.create_error_result(str(e), execution_time_s=time.time() - start_time)


# Predefined Standard Kernel Optimization Benchmark Tasks
FUSED_SOFTMAX_DROPOUT_TASK = KernelOptimizationTask.create(
    task_id="optimization_fused_softmax_dropout",
    name="Fused Softmax & Dropout Attention Kernel",
    description="Implement a fused Softmax + Dropout PyTorch/Triton kernel for Transformer attention heads.",
    specification=KernelSpecification(
        kernel_name="fused_softmax_dropout",
        framework="triton",
        input_shapes=[(32, 12, 512, 512)],
        baseline_latency_ms=12.4,
        target_speedup=1.5,
    ),
    difficulty=TaskDifficulty.MEDIUM,
)

FLASH_ATTENTION_SIMPLIFIED_TASK = KernelOptimizationTask.create(
    task_id="optimization_flash_attention_tiling",
    name="Tiled FlashAttention-v2 Kernel",
    description="Implement block-tiled SRAM-friendly FlashAttention forward pass avoiding HBM round-trips.",
    specification=KernelSpecification(
        kernel_name="flash_attention_tiled",
        framework="triton",
        input_shapes=[(16, 8, 1024, 64)],
        baseline_latency_ms=28.5,
        target_speedup=1.8,
    ),
    difficulty=TaskDifficulty.HARD,
)

LAYER_NORM_KERNEL_TASK = KernelOptimizationTask.create(
    task_id="optimization_fused_layernorm",
    name="Fused LayerNorm & Residual Add Kernel",
    description="Fuse Layer Normalization and residual connection addition into a single kernel pass.",
    specification=KernelSpecification(
        kernel_name="fused_layernorm",
        framework="pytorch",
        input_shapes=[(64, 512, 768)],
        baseline_latency_ms=8.2,
        target_speedup=1.6,
    ),
    difficulty=TaskDifficulty.EASY,
)
