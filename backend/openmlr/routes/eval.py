"""Evaluation and benchmark harness API routes.

Provides endpoints for inspecting benchmark suites, evaluating research agent outputs,
and running reproducible ML evaluation benchmarks across tasks.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..eval.benchmark_harness import (
    BenchmarkHarness,
    FullOpenMLRBenchmarkSuite,
    StandardHypothesisSuite,
    StandardOptimizationSuite,
    StandardReproductionSuite,
)
from ..eval.tasks import (
    BenchmarkTaskBase,
    HypothesisDiscoveryTask,
    KernelOptimizationTask,
    KernelSpecification,
    PaperMetadata,
    PaperReproductionTask,
    TaskDifficulty,
    get_benchmark_task,
    list_benchmark_tasks,
    register_benchmark_task,
)

router = APIRouter(prefix="/api/eval", tags=["eval"])
logger = logging.getLogger(__name__)

SUITES = {
    "reproduction": StandardReproductionSuite,
    "optimization": StandardOptimizationSuite,
    "hypothesis": StandardHypothesisSuite,
    "full": FullOpenMLRBenchmarkSuite,
}


class EvaluateTaskRequest(BaseModel):
    """Payload for evaluating an agent output against a benchmark task."""

    agent_output: Any = Field(..., description="Agent raw output or extracted metrics dictionary")


class RunSuiteRequest(BaseModel):
    """Payload for executing a benchmark suite."""

    suite_name: str = Field(default="reproduction", description="reproduction, optimization, hypothesis, full")
    max_concurrency: int = Field(default=4, ge=1, le=16, description="Maximum concurrent tasks")
    simulated_outputs: dict[str, Any] | None = Field(
        default=None, description="Optional map of task_id to simulated agent output for offline evaluation"
    )


class CustomReproductionTaskRequest(BaseModel):
    """Payload for registering a custom paper reproduction benchmark task."""

    task_id: str = Field(..., min_length=3)
    name: str = Field(..., min_length=3)
    description: str = Field(..., min_length=10)
    paper_title: str = Field(..., min_length=3)
    arxiv_id: str = Field(default="")
    target_metrics: dict[str, float] = Field(..., min_length=1)
    dataset_name: str = Field(default="custom")
    difficulty: str = Field(default="medium")
    timeout_seconds: float = Field(default=600.0, ge=10.0)


class CustomOptimizationTaskRequest(BaseModel):
    """Payload for registering a custom kernel optimization task."""

    task_id: str = Field(..., min_length=3)
    name: str = Field(..., min_length=3)
    description: str = Field(..., min_length=10)
    kernel_name: str = Field(..., min_length=2)
    framework: str = Field(default="triton")
    baseline_latency_ms: float = Field(..., gt=0)
    target_speedup: float = Field(default=1.5, gt=1.0)
    difficulty: str = Field(default="medium")
    timeout_seconds: float = Field(default=300.0, ge=10.0)


@router.get("/suites")
async def list_suites() -> dict[str, Any]:
    """List all available benchmark suites and their member tasks."""
    return {
        "suites": [
            {
                "id": key,
                "name": suite.name,
                "description": suite.description,
                "version": suite.version,
                "task_count": len(suite.tasks),
                "tasks": [
                    {
                        "id": t.id,
                        "name": t.name,
                        "category": t.category.value,
                        "difficulty": t.config.difficulty.value,
                        "description": t.config.description,
                    }
                    for t in suite.tasks
                ],
            }
            for key, suite in SUITES.items()
        ]
    }


@router.get("/tasks")
async def list_tasks(
    category: str | None = Query(default=None, description="Filter by category (reproduction, optimization, hypothesis)")
) -> dict[str, Any]:
    """List all registered benchmark tasks with optional category filter."""
    tasks = list_benchmark_tasks()
    if category:
        tasks = [t for t in tasks if t.category.value == category]

    return {
        "tasks": [
            {
                "id": t.id,
                "name": t.name,
                "category": t.category.value,
                "difficulty": t.config.difficulty.value,
                "description": t.config.description,
                "tags": t.config.tags,
                "domain": t.config.domain,
                "timeout_seconds": t.config.timeout_seconds,
            }
            for t in tasks
        ]
    }


@router.get("/tasks/{task_id}")
async def get_task_details(task_id: str) -> dict[str, Any]:
    """Get full details and specification of a specific benchmark task."""
    task = get_benchmark_task(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task '{task_id}' not found")

    details: dict[str, Any] = {
        "id": task.id,
        "name": task.name,
        "category": task.category.value,
        "difficulty": task.config.difficulty.value,
        "description": task.config.description,
        "config": task.config.to_dict(),
    }

    if isinstance(task, PaperReproductionTask):
        details["paper"] = asdict(task.paper)
        details["target_metrics"] = task.target_metrics
    elif isinstance(task, KernelOptimizationTask):
        details["specification"] = asdict(task.specification)
    elif isinstance(task, HypothesisDiscoveryTask):
        details["problem"] = asdict(task.problem)

    return details


@router.post("/tasks/{task_id}/evaluate")
async def evaluate_task_endpoint(task_id: str, req: EvaluateTaskRequest) -> dict[str, Any]:
    """Evaluate an agent's output against a benchmark task and return metrics."""
    task = get_benchmark_task(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task '{task_id}' not found")

    try:
        result = await task.evaluate(req.agent_output)
        return result.to_dict()
    except Exception as e:
        logger.exception("Error evaluating task %s: %s", task_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task evaluation failed: {str(e)}",
        ) from e


@router.post("/run")
async def run_benchmark_suite_endpoint(req: RunSuiteRequest) -> dict[str, Any]:
    """Execute a benchmark suite with provided or simulated outputs."""
    suite = SUITES.get(req.suite_name)
    if not suite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown suite '{req.suite_name}'. Valid: {list(SUITES.keys())}",
        )

    harness = BenchmarkHarness()

    # Agent runner resolving outputs from simulated map or fallback
    async def agent_runner(task: BenchmarkTaskBase) -> Any:
        if req.simulated_outputs and task.id in req.simulated_outputs:
            return req.simulated_outputs[task.id]
        if isinstance(task, PaperReproductionTask):
            # Default simulated reproduction with slight variance
            return {k: v * 0.99 for k, v in task.target_metrics.items()}
        if isinstance(task, KernelOptimizationTask):
            # Default simulated speedup
            return {
                "optimized_latency_ms": task.specification.baseline_latency_ms / (task.specification.target_speedup * 1.05),
                "numerical_correctness": True,
            }
        if isinstance(task, HypothesisDiscoveryTask):
            return {
                "hypothesis_statement": f"Simulated testable hypothesis for {task.name}",
                "novelty_score": 0.85,
                "feasibility_score": 0.90,
                "testability_score": 0.95,
            }
        return {}

    try:
        report = await harness.run_suite(suite, agent_runner, max_concurrency=req.max_concurrency)
        report_dict = harness.export_report_json(report)
        report_dict["markdown_summary"] = harness.export_report_markdown(report)
        return report_dict
    except Exception as e:
        logger.exception("Error running benchmark suite: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Benchmark execution failed: {str(e)}",
        ) from e


@router.post("/custom-task/reproduction")
async def register_custom_reproduction_task(req: CustomReproductionTaskRequest) -> dict[str, Any]:
    """Register a custom reproduction benchmark task."""
    try:
        difficulty_enum = TaskDifficulty(req.difficulty.lower())
    except ValueError:
        difficulty_enum = TaskDifficulty.MEDIUM

    metadata = PaperMetadata(
        title=req.paper_title,
        arxiv_id=req.arxiv_id,
    )
    task = PaperReproductionTask.create(
        task_id=req.task_id,
        name=req.name,
        description=req.description,
        paper=metadata,
        target_metrics=req.target_metrics,
        dataset=req.dataset_name,
        difficulty=difficulty_enum,
        timeout_seconds=req.timeout_seconds,
    )
    register_benchmark_task(task)
    return {
        "status": "registered",
        "task_id": task.id,
        "category": task.category.value,
        "name": task.name,
    }


@router.post("/custom-task/optimization")
async def register_custom_optimization_task(req: CustomOptimizationTaskRequest) -> dict[str, Any]:
    """Register a custom kernel optimization benchmark task."""
    try:
        difficulty_enum = TaskDifficulty(req.difficulty.lower())
    except ValueError:
        difficulty_enum = TaskDifficulty.MEDIUM

    spec = KernelSpecification(
        kernel_name=req.kernel_name,
        framework=req.framework,
        baseline_latency_ms=req.baseline_latency_ms,
        target_speedup=req.target_speedup,
    )
    task = KernelOptimizationTask.create(
        task_id=req.task_id,
        name=req.name,
        description=req.description,
        specification=spec,
        difficulty=difficulty_enum,
        timeout_seconds=req.timeout_seconds,
    )
    register_benchmark_task(task)
    return {
        "status": "registered",
        "task_id": task.id,
        "category": task.category.value,
        "name": task.name,
    }
