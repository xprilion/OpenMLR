"""Tests for sweeps agent tool."""

import json
from pathlib import Path

import pytest

from openmlr.tools.sweeps import create_sweeps_tool


@pytest.mark.asyncio
async def test_sweeps_tool_lifecycle(tmp_path: Path):
    tool = create_sweeps_tool(get_project_id=lambda: "test_proj", base_dir=tmp_path / "sweeps")
    handler = tool.handler
    assert handler is not None

    # 1. Create sweep
    create_res, ok = await handler(
        action="create_sweep",
        name="Agent ResNet Sweep",
        method="random",
        objective_metric="val_loss",
        goal="minimize",
        parameters={
            "lr": {"param_type": "loguniform", "min_val": 1e-4, "max_val": 1e-2},
            "batch_size": {"param_type": "choice", "choices": [32, 64]},
        },
        max_trials=3,
    )
    assert ok is True
    assert "Agent ResNet Sweep" in create_res

    # 2. List sweeps
    list_res, ok = await handler(action="list_sweeps")
    assert ok is True
    assert "Agent ResNet Sweep" in list_res

    # Extract sweep_id from list or create
    # 3. Suggest trial
    # First get sweep id from listing
    from openmlr.services.sweep_engine import SweepEngine
    engine = SweepEngine(base_dir=tmp_path / "sweeps")
    sweeps = engine.list_sweeps("test_proj")
    assert len(sweeps) == 1
    sweep_id = sweeps[0].sweep_id

    suggest_res, ok = await handler(action="suggest_trial", sweep_id=sweep_id)
    assert ok is True
    assert "Suggested Next Trial" in suggest_res

    # 4. Record trial
    sweep = engine.get_sweep("test_proj", sweep_id)
    assert sweep is not None
    trial_id = sweep.trials[0].trial_id

    record_res, ok = await handler(
        action="record_trial",
        sweep_id=sweep_id,
        trial_id=trial_id,
        metrics={"val_loss": 0.31, "accuracy": 0.89},
        status="completed",
    )
    assert ok is True
    assert "recorded" in record_res

    # 5. Prune check
    prune_res, ok = await handler(
        action="prune_check",
        sweep_id=sweep_id,
        trial_id=trial_id,
        current_step=5,
        current_metric_val=0.31,
    )
    assert ok is True
    assert "Prune evaluation" in prune_res

    # 6. Analyze
    analyze_res, ok = await handler(action="analyze_sweep", sweep_id=sweep_id)
    assert ok is True
    analysis_data = json.loads(analyze_res)
    assert analysis_data["completed_trials"] == 1
    assert analysis_data["best_metric_value"] == 0.31

    # 7. Export report
    export_res, ok = await handler(action="export_report", sweep_id=sweep_id)
    assert ok is True
    assert "Hyperparameter Optimization Report" in export_res
