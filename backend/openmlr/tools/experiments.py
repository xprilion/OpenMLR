"""Experiments tool — ML experiment tracking and run management for the AI research agent.

Allows the autonomous research agent to:
- Create new experiment runs with hyperparameters, architecture details, and compute targets
- Log metric curves (train/val loss, learning rate, GPU utilization, throughput)
- Record model checkpoint artifacts and evaluation scores
- Inspect run statuses, latest metrics, and execution progress
- Compare multiple runs across ablation studies and hyperparameter sweeps
- Complete or fail runs with outcome summaries and findings
"""

from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from typing import Any

from ..agent.types import ToolSpec
from ..services.experiment_tracker import ExperimentTracker

log = logging.getLogger(__name__)

# Context variable for per-request experiment tracker & project UUID
_experiment_tracker_var: ContextVar[ExperimentTracker | None] = ContextVar(
    "experiment_tracker", default=None
)
_project_uuid_var: ContextVar[str | None] = ContextVar("experiment_project_uuid", default=None)

_default_tracker = ExperimentTracker()


def set_experiment_context(
    tracker: ExperimentTracker | None, project_uuid: str | None = None
) -> None:
    """Set the active experiment tracker and project UUID for the current async context."""
    _experiment_tracker_var.set(tracker)
    _project_uuid_var.set(project_uuid)


def _get_active_tracker() -> ExperimentTracker:
    """Get the active tracker for the current async context, falling back to default."""
    return _experiment_tracker_var.get() or _default_tracker


def _parse_dict_or_json(val: Any) -> dict[str, Any]:
    """Parse dict or JSON string into a dict."""
    if isinstance(val, dict):
        return val
    if isinstance(val, str) and val.strip():
        try:
            parsed = json.loads(val)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return {"raw": val}
    return {}


def _parse_list_or_csv(val: Any) -> list[str]:
    """Parse list or comma-separated string into a list of trimmed strings."""
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    if isinstance(val, str) and val.strip():
        if val.strip().startswith("[") and val.strip().endswith("]"):
            try:
                parsed = json.loads(val)
                if isinstance(parsed, list):
                    return [str(x).strip() for x in parsed if str(x).strip()]
            except Exception:
                pass
        return [x.strip() for x in val.split(",") if x.strip()]
    return []


async def _handle_experiments(
    operation: str,
    name: str = "",
    description: str = "",
    hyperparameters: Any = None,
    compute_target: str = "Local GPU",
    tags: Any = None,
    total_steps: int = 100,
    total_epochs: int = 1,
    run_id: str = "",
    metrics: Any = None,
    step: int = 0,
    epoch: int = 1,
    checkpoint_name: str = "",
    path: str = "",
    file_size_mb: float = 0.0,
    status: str = "",
    reason: str = "",
    best_val_loss: float | None = None,
    run_ids: Any = None,
    search: str = "",
    limit: int = 10,
    session=None,
    **kwargs: Any,
) -> tuple[str, bool]:
    """Handle experiment tool operations."""
    tracker = _get_active_tracker()
    project_uuid = _project_uuid_var.get()

    try:
        if operation == "create_run":
            if not name.strip():
                return "Error: 'name' is required when creating an experiment run.", False

            hp_dict = _parse_dict_or_json(hyperparameters)
            tag_list = _parse_list_or_csv(tags)

            run = tracker.create_run(
                name=name.strip(),
                description=description.strip(),
                hyperparameters=hp_dict,
                compute_target=compute_target.strip() or "Local GPU",
                tags=tag_list,
                total_steps=max(1, total_steps),
                total_epochs=max(1, total_epochs),
                project_uuid=project_uuid,
            )

            # Auto-record in knowledge graph if active workspace persistence exists
            try:
                from .workspace_tools import _knowledge_var

                kg = _knowledge_var.get()
                if kg:
                    kg.add_entity(
                        entity_id=f"exp_{run.id}",
                        entity_type="experiment",
                        label=run.name,
                        properties={
                            "run_id": run.id,
                            "compute_target": run.compute_target,
                            "hyperparameters": run.hyperparameters,
                            "status": run.status,
                        },
                    )
                    kg.save()
            except Exception as e:
                log.debug("Knowledge graph auto-entity skipped for experiment %s: %s", run.id, e)

            result = {
                "message": f"Experiment run '{run.name}' created successfully.",
                "run_id": run.id,
                "name": run.name,
                "status": run.status,
                "hyperparameters": run.hyperparameters,
                "compute_target": run.compute_target,
                "total_steps": run.total_steps,
                "total_epochs": run.total_epochs,
            }
            return json.dumps(result, indent=2), True

        elif operation == "log_metrics":
            if not run_id.strip():
                return "Error: 'run_id' is required to log metrics.", False

            run = tracker.get_run(run_id.strip())
            if not run:
                return f"Error: Experiment run '{run_id}' not found.", False

            metric_dict = _parse_dict_or_json(metrics)
            if not metric_dict:
                return "Error: 'metrics' dictionary cannot be empty.", False

            # Convert all numeric values to float
            clean_metrics: dict[str, float] = {}
            for k, v in metric_dict.items():
                try:
                    clean_metrics[k] = float(v)
                except (ValueError, TypeError):
                    continue

            updated_run = tracker.log_metrics(
                run_id=run.id,
                metrics=clean_metrics,
                step=max(0, step),
                epoch=max(1, epoch),
            )

            if not updated_run:
                return f"Failed to log metrics for run '{run_id}'.", False

            result = {
                "message": f"Metrics logged at step {step}, epoch {epoch}.",
                "run_id": updated_run.id,
                "current_step": updated_run.current_step,
                "total_steps": updated_run.total_steps,
                "logged_metrics": clean_metrics,
                "best_val_loss": updated_run.best_val_loss,
            }
            return json.dumps(result, indent=2), True

        elif operation == "record_checkpoint":
            if not run_id.strip():
                return "Error: 'run_id' is required to record a checkpoint.", False

            run = tracker.get_run(run_id.strip())
            if not run:
                return f"Error: Experiment run '{run_id}' not found.", False

            cp_name = checkpoint_name.strip() or f"checkpoint-step-{step}.pt"
            cp_path = path.strip() or f"checkpoints/{cp_name}"
            eval_metrics = _parse_dict_or_json(metrics)
            clean_eval: dict[str, float] = {}
            for k, v in eval_metrics.items():
                try:
                    clean_eval[k] = float(v)
                except (ValueError, TypeError):
                    continue

            cp = tracker.register_checkpoint(
                run_id=run.id,
                name=cp_name,
                step=max(0, step),
                epoch=max(1, epoch),
                path=cp_path,
                file_size_mb=max(0.0, float(file_size_mb)),
                metrics=clean_eval,
            )

            result = {
                "message": f"Checkpoint '{cp_name}' recorded for run '{run.id}'.",
                "run_id": run.id,
                "checkpoint": cp.to_dict(),
                "total_checkpoints": len(run.checkpoints),
            }
            return json.dumps(result, indent=2), True

        elif operation == "get_run":
            if not run_id.strip():
                return "Error: 'run_id' is required.", False

            run = tracker.get_run(run_id.strip())
            if not run:
                return f"Error: Experiment run '{run_id}' not found.", False

            # Extract latest metric values for concise view
            latest_metrics: dict[str, float] = {}
            for k, pts in run.metrics.items():
                if pts:
                    latest_metrics[k] = pts[-1].value

            result = {
                "run_id": run.id,
                "name": run.name,
                "description": run.description,
                "status": run.status,
                "started_at": run.started_at,
                "ended_at": run.ended_at,
                "duration_seconds": run.duration_seconds,
                "compute_target": run.compute_target,
                "tags": run.tags,
                "hyperparameters": run.hyperparameters,
                "current_step": run.current_step,
                "total_steps": run.total_steps,
                "current_epoch": run.current_epoch,
                "total_epochs": run.total_epochs,
                "best_val_loss": run.best_val_loss,
                "latest_metrics": latest_metrics,
                "checkpoints_count": len(run.checkpoints),
                "checkpoints": [cp.to_dict() for cp in run.checkpoints],
            }
            return json.dumps(result, indent=2), True

        elif operation == "list_runs":
            runs_list, total = tracker.list_runs(
                project_uuid=project_uuid,
                status=status if status in {"running", "completed", "failed", "paused", "idle"} else None,
                search=search.strip() or None,
                limit=max(1, min(limit, 50)),
                offset=0,
            )

            summaries = []
            for r in runs_list:
                latest_val_loss = r.metrics.get("val_loss", [])[-1].value if r.metrics.get("val_loss") else None
                summaries.append({
                    "run_id": r.id,
                    "name": r.name,
                    "status": r.status,
                    "started_at": r.started_at,
                    "progress": f"{r.current_step}/{r.total_steps} steps",
                    "best_val_loss": r.best_val_loss,
                    "latest_val_loss": latest_val_loss,
                    "tags": r.tags,
                })

            result = {
                "total_runs": total,
                "returned_count": len(summaries),
                "runs": summaries,
            }
            return json.dumps(result, indent=2), True

        elif operation == "compare_runs":
            parsed_ids = _parse_list_or_csv(run_ids)
            if not parsed_ids:
                return "Error: 'run_ids' list or comma-separated string is required to compare runs.", False

            comparison = tracker.compare_runs(parsed_ids)
            return json.dumps(comparison, indent=2), True

        elif operation == "complete_run":
            if not run_id.strip():
                return "Error: 'run_id' is required.", False

            run = tracker.get_run(run_id.strip())
            if not run:
                return f"Error: Experiment run '{run_id}' not found.", False

            final_status = "completed" if status not in {"completed", "failed"} else status
            updated_run = tracker.update_status(
                run_id=run.id,
                status=final_status,
                reason=reason.strip() or None,
            )

            if not updated_run:
                return f"Failed to update status for run '{run_id}'.", False

            if best_val_loss is not None:
                updated_run.best_val_loss = float(best_val_loss)
                tracker._persist_run(updated_run)

            # Update entity in knowledge graph if active
            try:
                from .workspace_tools import _knowledge_var

                kg = _knowledge_var.get()
                if kg:
                    kg.add_entity(
                        entity_id=f"exp_{updated_run.id}",
                        entity_type="experiment",
                        label=updated_run.name,
                        properties={
                            "run_id": updated_run.id,
                            "status": updated_run.status,
                            "best_val_loss": updated_run.best_val_loss,
                            "duration_seconds": updated_run.duration_seconds,
                        },
                    )
                    kg.save()
            except Exception as e:
                log.debug("Knowledge graph entity update skipped: %s", e)

            result = {
                "message": f"Run '{updated_run.name}' marked as {updated_run.status}.",
                "run_id": updated_run.id,
                "status": updated_run.status,
                "best_val_loss": updated_run.best_val_loss,
                "duration_seconds": updated_run.duration_seconds,
            }
            return json.dumps(result, indent=2), True

        else:
            return f"Unknown experiments operation: '{operation}'. Valid operations: create_run, log_metrics, record_checkpoint, get_run, list_runs, compare_runs, complete_run.", False

    except Exception as e:
        log.warning("Experiment tool error (%s): %s", operation, e)
        return f"Experiment operation failed: {e}", False


def create_experiments_tool() -> ToolSpec:
    """Create the ToolSpec for ML experiment tracking operations."""
    return ToolSpec(
        name="experiments",
        description=(
            "Track, monitor, and compare machine learning experiment runs and training metrics.\n\n"
            "Operations:\n"
            "- create_run: Initialize a new tracked experiment run (requires 'name', optional 'hyperparameters', 'compute_target', 'tags', 'total_steps', 'total_epochs')\n"
            "- log_metrics: Log scalar training/validation metrics at a step/epoch (requires 'run_id', 'metrics' dict or JSON e.g. {'train_loss': 1.8, 'val_loss': 1.9, 'lr': 0.001}, 'step')\n"
            "- record_checkpoint: Register a model checkpoint artifact (requires 'run_id', optional 'checkpoint_name', 'path', 'file_size_mb', 'metrics')\n"
            "- get_run: Retrieve details, latest metrics, and checkpoints for a run (requires 'run_id')\n"
            "- list_runs: List all experiment runs in the current project (optional 'status', 'search', 'limit')\n"
            "- compare_runs: Side-by-side comparison of hyperparameters and loss metrics across runs (requires 'run_ids' list/CSV)\n"
            "- complete_run: Mark a run as completed or failed (requires 'run_id', optional 'status', 'best_val_loss', 'reason')"
        ),
        parameters={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": [
                        "create_run",
                        "log_metrics",
                        "record_checkpoint",
                        "get_run",
                        "list_runs",
                        "compare_runs",
                        "complete_run",
                    ],
                    "description": "The experiment tracking operation to perform.",
                },
                "name": {
                    "type": "string",
                    "description": "Descriptive name for the experiment run (for create_run).",
                },
                "description": {
                    "type": "string",
                    "description": "Scientific hypothesis or objective of the experiment run.",
                },
                "hyperparameters": {
                    "type": "object",
                    "description": "Hyperparameters dictionary or JSON string (e.g. {'lr': 1e-4, 'batch_size': 64}).",
                },
                "compute_target": {
                    "type": "string",
                    "description": "Hardware/compute target (e.g. 'Local GPU', 'Modal A100').",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags list or comma-separated string for categorization.",
                },
                "total_steps": {
                    "type": "integer",
                    "description": "Expected total training steps.",
                },
                "total_epochs": {
                    "type": "integer",
                    "description": "Expected total training epochs.",
                },
                "run_id": {
                    "type": "string",
                    "description": "Experiment run ID (for log_metrics, record_checkpoint, get_run, complete_run).",
                },
                "metrics": {
                    "type": "object",
                    "description": "Key-value metrics dictionary or JSON (e.g. {'train_loss': 0.45, 'val_loss': 0.52}).",
                },
                "step": {
                    "type": "integer",
                    "description": "Current optimization/training step.",
                },
                "epoch": {
                    "type": "integer",
                    "description": "Current training epoch.",
                },
                "checkpoint_name": {
                    "type": "string",
                    "description": "Name of the checkpoint file or artifact.",
                },
                "path": {
                    "type": "string",
                    "description": "Local or workspace file path to the checkpoint artifact.",
                },
                "file_size_mb": {
                    "type": "number",
                    "description": "File size of the checkpoint in megabytes.",
                },
                "status": {
                    "type": "string",
                    "enum": ["completed", "failed", "running", "paused", "idle"],
                    "description": "Run status for complete_run or filter for list_runs.",
                },
                "reason": {
                    "type": "string",
                    "description": "Optional notes or failure diagnosis reason.",
                },
                "best_val_loss": {
                    "type": "number",
                    "description": "Best validation loss achieved during the run.",
                },
                "run_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List or CSV string of run IDs to compare (for compare_runs).",
                },
                "search": {
                    "type": "string",
                    "description": "Search keyword for list_runs.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max runs to return (for list_runs, default 10).",
                },
            },
            "required": ["operation"],
        },
        handler=_handle_experiments,
    )
