"""Base definitions and abstract contracts for OpenMLR benchmark tasks."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskCategory(str, Enum):
    """Categories of ML research benchmark tasks."""

    REPRODUCTION = "reproduction"
    OPTIMIZATION = "optimization"
    HYPOTHESIS = "hypothesis"
    END_TO_END = "end_to_end"


class TaskDifficulty(str, Enum):
    """Task complexity level."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class TaskStatus(str, Enum):
    """Execution status of a benchmark task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class TaskConfig:
    """Static configuration describing a benchmark task."""

    id: str
    name: str
    description: str
    category: TaskCategory
    difficulty: TaskDifficulty = TaskDifficulty.MEDIUM
    timeout_seconds: float = 300.0
    tags: list[str] = field(default_factory=list)
    dataset: str = ""
    domain: str = "Machine Learning"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "difficulty": self.difficulty.value,
            "timeout_seconds": self.timeout_seconds,
            "tags": self.tags,
            "dataset": self.dataset,
            "domain": self.domain,
            "metadata": self.metadata,
        }


@dataclass
class TaskResult:
    """Execution and evaluation result for a benchmark task."""

    task_id: str
    category: TaskCategory
    status: TaskStatus
    success: bool
    metrics: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0  # Normalized 0.0 - 1.0 score
    execution_time_s: float = 0.0
    error_message: str | None = None
    artifact_paths: list[str] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    raw_output: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "category": self.category.value,
            "status": self.status.value,
            "success": self.success,
            "score": round(self.score, 4),
            "metrics": self.metrics,
            "execution_time_s": round(self.execution_time_s, 3),
            "error_message": self.error_message,
            "artifact_paths": self.artifact_paths,
            "diagnostics": self.diagnostics,
        }


class BenchmarkTaskBase(abc.ABC):
    """Abstract base class for all benchmark tasks."""

    def __init__(self, config: TaskConfig) -> None:
        self.config = config

    @property
    def id(self) -> str:
        return self.config.id

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def category(self) -> TaskCategory:
        return self.config.category

    @abc.abstractmethod
    async def evaluate(self, agent_output: Any) -> TaskResult:
        """Evaluate agent output / run against task criteria."""
        raise NotImplementedError

    def create_error_result(self, error_message: str, execution_time_s: float = 0.0) -> TaskResult:
        """Helper to create standard error result."""
        return TaskResult(
            task_id=self.id,
            category=self.category,
            status=TaskStatus.ERROR,
            success=False,
            score=0.0,
            execution_time_s=execution_time_s,
            error_message=error_message,
        )

    def create_timeout_result(self, timeout_s: float) -> TaskResult:
        """Helper to create standard timeout result."""
        return TaskResult(
            task_id=self.id,
            category=self.category,
            status=TaskStatus.TIMEOUT,
            success=False,
            score=0.0,
            execution_time_s=timeout_s,
            error_message=f"Task execution exceeded timeout limit of {timeout_s}s",
        )

    def to_dict(self) -> dict[str, Any]:
        return self.config.to_dict()
