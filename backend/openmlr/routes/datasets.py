"""Dataset management, profiling, validation, and split REST API routes.

Provides endpoints for inspecting data files, analyzing column statistics, validating schemas,
and generating partitioned splits for ML training workflows.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..db.models import User
from ..dependencies import get_current_user_optional
from ..services.dataset_profiler import DatasetProfiler

router = APIRouter(prefix="/api/datasets", tags=["datasets"])
logger = logging.getLogger(__name__)

DATASET_PATH_DESC = "Path to the dataset file"


def _safe_dataset_path(path_str: str) -> Path:
    """Safely validate and resolve a dataset file path, mitigating path injection risks."""
    clean = str(path_str).strip()
    if not clean or "\0" in clean or ".." in clean:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid dataset path parameter",
        )
    resolved = Path(clean).resolve()
    try:
        resolved.relative_to(resolved.anchor)
    except (ValueError, RuntimeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path traversal not allowed",
        )
    if not resolved.exists() or not resolved.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset file not found at '{path_str}'",
        )
    return resolved


def _safe_output_dir(dir_str: str) -> Path:
    """Safely validate and resolve an output directory path."""
    clean = str(dir_str).strip()
    if not clean or "\0" in clean or ".." in clean:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid output directory path parameter",
        )
    resolved = Path(clean).resolve()
    try:
        resolved.relative_to(resolved.anchor)
    except (ValueError, RuntimeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path traversal not allowed",
        )
    return resolved


class ProfileDatasetRequest(BaseModel):
    """Payload for profiling a dataset file."""

    path: str = Field(..., min_length=1, description=DATASET_PATH_DESC)
    sample_size: int = Field(default=5000, ge=10, le=100000, description="Max rows to sample")


class InspectSamplesRequest(BaseModel):
    """Payload for sampling rows from a dataset."""

    path: str = Field(..., min_length=1, description=DATASET_PATH_DESC)
    n: int = Field(default=5, ge=1, le=100, description="Number of rows to return")
    offset: int = Field(default=0, ge=0, description="Row offset")
    strategy: str = Field(default="head", description="Sampling strategy: head, random, stratified")
    label_column: str | None = Field(default=None, description="Column for stratification")


class ValidateDatasetRequest(BaseModel):
    """Payload for validating a dataset."""

    path: str = Field(..., min_length=1, description=DATASET_PATH_DESC)
    expected_columns: list[str] | None = Field(default=None, description="Required column names")
    max_null_pct: float = Field(default=20.0, ge=0.0, le=100.0, description="Max allowed null percentage")
    max_token_length: int | None = Field(default=None, ge=1, description="Max allowed text tokens")


class SplitDatasetRequest(BaseModel):
    """Payload for splitting a dataset into train/val/test partitions."""

    path: str = Field(..., min_length=1, description="Path to the source dataset file")
    output_dir: str = Field(..., min_length=1, description="Target directory for output partitions")
    train_ratio: float = Field(default=0.8, gt=0.0, lt=1.0, description="Train ratio")
    val_ratio: float = Field(default=0.1, ge=0.0, lt=1.0, description="Validation ratio")
    test_ratio: float = Field(default=0.1, ge=0.0, lt=1.0, description="Test ratio")
    stratify_column: str | None = Field(default=None, description="Column to stratify on")
    seed: int = Field(default=42, description="Random seed")


@router.post("/profile")
async def profile_dataset(
    req: ProfileDatasetRequest,
    user: User | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    """Compute comprehensive statistical profile and diagnostics for a dataset file."""
    path = _safe_dataset_path(req.path)

    try:
        profile = DatasetProfiler.profile(path, sample_size=req.sample_size)
        return {
            "success": True,
            "profile": profile.to_dict(),
        }
    except Exception as e:
        logger.exception("Failed profiling dataset '%s': %s", req.path, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error profiling dataset: {e}",
        )


@router.post("/inspect")
async def inspect_samples(
    req: InspectSamplesRequest,
    user: User | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    """Retrieve sample records from a dataset."""
    path = _safe_dataset_path(req.path)

    try:
        samples = DatasetProfiler.sample_records(
            path,
            n=req.n,
            offset=req.offset,
            strategy=req.strategy,
            label_column=req.label_column,
        )
        return {
            "success": True,
            "total_sampled": len(samples),
            "samples": samples,
        }
    except Exception as e:
        logger.exception("Failed inspecting dataset '%s': %s", req.path, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inspecting dataset: {e}",
        )


@router.post("/validate")
async def validate_dataset(
    req: ValidateDatasetRequest,
    user: User | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    """Validate dataset structure, required schema, and constraints."""
    path = _safe_dataset_path(req.path)

    try:
        result = DatasetProfiler.validate_dataset(
            path,
            expected_columns=req.expected_columns,
            max_null_pct=req.max_null_pct,
            max_token_length=req.max_token_length,
        )
        return {
            "success": True,
            "validation": result,
        }
    except Exception as e:
        logger.exception("Failed validating dataset '%s': %s", req.path, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error validating dataset: {e}",
        )


@router.post("/split")
async def split_dataset(
    req: SplitDatasetRequest,
    user: User | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    """Partition a dataset file into train/val/test splits."""
    path = _safe_dataset_path(req.path)
    out_dir = _safe_output_dir(req.output_dir)

    try:
        manifest = DatasetProfiler.split_dataset(
            path,
            output_dir=out_dir,
            train_ratio=req.train_ratio,
            val_ratio=req.val_ratio,
            test_ratio=req.test_ratio,
            stratify_column=req.stratify_column,
            seed=req.seed,
        )
        return {
            "success": True,
            "manifest": manifest,
        }
    except Exception as e:
        logger.exception("Failed splitting dataset '%s': %s", req.path, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error splitting dataset: {e}",
        )
