"""Benchmark task registry and exports for OpenMLR evaluation harness."""

from __future__ import annotations

from .base import (
    BenchmarkTaskBase,
    TaskCategory,
    TaskConfig,
    TaskDifficulty,
    TaskResult,
    TaskStatus,
)
from .hypothesis_task import (
    COT_SELF_CONSISTENCY_HYPOTHESIS_TASK,
    VIT_PATCH_DROPOUT_HYPOTHESIS_TASK,
    HypothesisDiscoveryTask,
    ResearchProblemContext,
)
from .optimization_task import (
    FLASH_ATTENTION_SIMPLIFIED_TASK,
    FUSED_SOFTMAX_DROPOUT_TASK,
    LAYER_NORM_KERNEL_TASK,
    KernelOptimizationTask,
    KernelSpecification,
)
from .reproduction_task import (
    BERT_SST2_TASK,
    NANOGPT_SHAKESPEARE_TASK,
    RESNET18_CIFAR10_TASK,
    PaperMetadata,
    PaperReproductionTask,
)

STANDARD_TASKS: list[BenchmarkTaskBase] = [
    RESNET18_CIFAR10_TASK,
    NANOGPT_SHAKESPEARE_TASK,
    BERT_SST2_TASK,
    FUSED_SOFTMAX_DROPOUT_TASK,
    FLASH_ATTENTION_SIMPLIFIED_TASK,
    LAYER_NORM_KERNEL_TASK,
    VIT_PATCH_DROPOUT_HYPOTHESIS_TASK,
    COT_SELF_CONSISTENCY_HYPOTHESIS_TASK,
]

TASK_REGISTRY: dict[str, BenchmarkTaskBase] = {task.id: task for task in STANDARD_TASKS}


def register_benchmark_task(task: BenchmarkTaskBase) -> None:
    """Register a custom benchmark task."""
    TASK_REGISTRY[task.id] = task


def get_benchmark_task(task_id: str) -> BenchmarkTaskBase | None:
    """Lookup a benchmark task by ID."""
    return TASK_REGISTRY.get(task_id)


def list_benchmark_tasks(
    category: TaskCategory | str | None = None,
    difficulty: TaskDifficulty | str | None = None,
    tag: str | None = None,
) -> list[BenchmarkTaskBase]:
    """List benchmark tasks filtered by category, difficulty, or tag."""
    tasks = list(TASK_REGISTRY.values())
    if category is not None:
        cat_str = category.value if isinstance(category, TaskCategory) else str(category)
        tasks = [t for t in tasks if t.category.value == cat_str]
    if difficulty is not None:
        diff_str = difficulty.value if isinstance(difficulty, TaskDifficulty) else str(difficulty)
        tasks = [t for t in tasks if t.config.difficulty.value == diff_str]
    if tag is not None:
        tasks = [t for t in tasks if tag in t.config.tags]
    return tasks


__all__ = [
    "BenchmarkTaskBase",
    "TaskCategory",
    "TaskDifficulty",
    "TaskStatus",
    "TaskConfig",
    "TaskResult",
    "PaperReproductionTask",
    "PaperMetadata",
    "KernelOptimizationTask",
    "KernelSpecification",
    "HypothesisDiscoveryTask",
    "ResearchProblemContext",
    "RESNET18_CIFAR10_TASK",
    "NANOGPT_SHAKESPEARE_TASK",
    "BERT_SST2_TASK",
    "FUSED_SOFTMAX_DROPOUT_TASK",
    "FLASH_ATTENTION_SIMPLIFIED_TASK",
    "LAYER_NORM_KERNEL_TASK",
    "VIT_PATCH_DROPOUT_HYPOTHESIS_TASK",
    "COT_SELF_CONSISTENCY_HYPOTHESIS_TASK",
    "STANDARD_TASKS",
    "TASK_REGISTRY",
    "register_benchmark_task",
    "get_benchmark_task",
    "list_benchmark_tasks",
]
