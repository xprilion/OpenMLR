"""Tests for SweepEngine (hyperparameter optimization, sampling, pruning, analysis)."""

from pathlib import Path

import pytest

from openmlr.services.sweep_engine import (
    EarlyStoppingConfig,
    ParameterSpec,
    SweepEngine,
)


@pytest.fixture
def sweep_engine(tmp_path: Path):
    return SweepEngine(base_dir=tmp_path / "sweeps")


def test_create_and_get_sweep(sweep_engine: SweepEngine):
    params = {
        "learning_rate": ParameterSpec(name="learning_rate", param_type="loguniform", min_val=1e-5, max_val=1e-2),
        "batch_size": ParameterSpec(name="batch_size", param_type="choice", choices=[16, 32, 64]),
        "epochs": ParameterSpec(name="epochs", param_type="int_uniform", min_val=5, max_val=20, step=5),
    }

    sweep = sweep_engine.create_sweep(
        project_id="proj_1",
        name="Transformer LR & Batch Sweep",
        method="random",
        objective_metric="val_loss",
        goal="minimize",
        parameters=params,
        max_trials=5,
    )

    assert sweep.sweep_id.startswith("swp_")
    assert sweep.name == "Transformer LR & Batch Sweep"
    assert len(sweep.parameters) == 3
    assert sweep.status == "active"

    loaded = sweep_engine.get_sweep("proj_1", sweep.sweep_id)
    assert loaded is not None
    assert loaded.name == sweep.name
    assert loaded.objective_metric == "val_loss"


def test_list_and_delete_sweeps(sweep_engine: SweepEngine):
    s1 = sweep_engine.create_sweep(
        project_id="proj_test",
        name="Sweep 1",
        method="grid",
        objective_metric="accuracy",
        goal="maximize",
        parameters={"lr": {"param_type": "choice", "choices": [0.01, 0.001]}},
    )
    s2 = sweep_engine.create_sweep(
        project_id="proj_test",
        name="Sweep 2",
        method="random",
        objective_metric="val_loss",
        goal="minimize",
        parameters={"dropout": {"param_type": "uniform", "min_val": 0.1, "max_val": 0.5}},
    )

    sweeps = sweep_engine.list_sweeps("proj_test")
    assert len(sweeps) == 2

    assert sweep_engine.delete_sweep("proj_test", s1.sweep_id) is True
    sweeps_after = sweep_engine.list_sweeps("proj_test")
    assert len(sweeps_after) == 1
    assert sweeps_after[0].sweep_id == s2.sweep_id


def test_suggest_grid_trials(sweep_engine: SweepEngine):
    params = {
        "lr": ParameterSpec(name="lr", param_type="choice", choices=[0.01, 0.001]),
        "optimizer": ParameterSpec(name="optimizer", param_type="categorical", choices=["adam", "sgd"]),
    }
    sweep = sweep_engine.create_sweep(
        project_id="proj_grid",
        name="Grid Test",
        method="grid",
        objective_metric="val_loss",
        goal="minimize",
        parameters=params,
        max_trials=4,
    )

    t1 = sweep_engine.suggest_trial("proj_grid", sweep.sweep_id)
    assert t1 is not None
    assert t1.trial_number == 1
    assert "lr" in t1.parameters
    assert "optimizer" in t1.parameters

    t2 = sweep_engine.suggest_trial("proj_grid", sweep.sweep_id)
    t3 = sweep_engine.suggest_trial("proj_grid", sweep.sweep_id)
    t4 = sweep_engine.suggest_trial("proj_grid", sweep.sweep_id)
    assert t4 is not None

    # Max trials reached
    t5 = sweep_engine.suggest_trial("proj_grid", sweep.sweep_id)
    assert t5 is None


def test_suggest_bayesian_optimization(sweep_engine: SweepEngine):
    params = {
        "lr": ParameterSpec(name="lr", param_type="uniform", min_val=0.0001, max_val=0.01),
        "hidden_dim": ParameterSpec(name="hidden_dim", param_type="choice", choices=[128, 256, 512]),
    }
    sweep = sweep_engine.create_sweep(
        project_id="proj_bayes",
        name="Bayes Test",
        method="bayesian",
        objective_metric="val_loss",
        goal="minimize",
        parameters=params,
        max_trials=10,
    )

    # Seed 3 trials
    for i in range(3):
        t = sweep_engine.suggest_trial("proj_bayes", sweep.sweep_id)
        assert t is not None
        sweep_engine.record_trial_result(
            project_id="proj_bayes",
            sweep_id=sweep.sweep_id,
            trial_id=t.trial_id,
            metrics={"val_loss": 0.5 - i * 0.1},
            status="completed",
        )

    # 4th trial uses Bayesian surrogate
    t4 = sweep_engine.suggest_trial("proj_bayes", sweep.sweep_id)
    assert t4 is not None
    assert "lr" in t4.parameters
    assert "hidden_dim" in t4.parameters


def test_early_stopping_pruning(sweep_engine: SweepEngine):
    es = EarlyStoppingConfig(enabled=True, min_steps=3, reduction_factor=2.0)
    params = {"lr": ParameterSpec(name="lr", param_type="choice", choices=[0.01, 0.001, 0.0001])}
    sweep = sweep_engine.create_sweep(
        project_id="proj_es",
        name="ASHA Prune Test",
        method="hyperband",
        objective_metric="val_loss",
        goal="minimize",
        parameters=params,
        early_stopping=es,
        max_trials=5,
    )

    # Seed 2 good trials with step history
    t1 = sweep_engine.suggest_trial("proj_es", sweep.sweep_id)
    assert t1 is not None
    sweep_engine.record_trial_result(
        "proj_es",
        sweep.sweep_id,
        t1.trial_id,
        metrics={"val_loss": 0.2},
        step_history=[{"step": 1, "val_loss": 0.8}, {"step": 3, "val_loss": 0.3}],
    )

    t2 = sweep_engine.suggest_trial("proj_es", sweep.sweep_id)
    assert t2 is not None
    sweep_engine.record_trial_result(
        "proj_es",
        sweep.sweep_id,
        t2.trial_id,
        metrics={"val_loss": 0.25},
        step_history=[{"step": 1, "val_loss": 0.9}, {"step": 3, "val_loss": 0.35}],
    )

    t3 = sweep_engine.suggest_trial("proj_es", sweep.sweep_id)
    assert t3 is not None

    # Step 1 is below min_steps (3), so shouldn't prune
    assert not sweep_engine.should_prune_trial("proj_es", sweep.sweep_id, t3.trial_id, 1, 1.5)

    # Step 3 with high val_loss (1.5 >> 0.3) should be pruned
    assert sweep_engine.should_prune_trial("proj_es", sweep.sweep_id, t3.trial_id, 3, 1.5)


def test_analyze_sweep_and_markdown_export(sweep_engine: SweepEngine):
    params = {
        "lr": ParameterSpec(name="lr", param_type="uniform", min_val=0.001, max_val=0.1),
        "weight_decay": ParameterSpec(name="weight_decay", param_type="uniform", min_val=1e-5, max_val=1e-3),
    }
    sweep = sweep_engine.create_sweep(
        project_id="proj_analysis",
        name="Sensitivity Analysis",
        method="random",
        objective_metric="val_loss",
        goal="minimize",
        parameters=params,
        max_trials=4,
    )

    for i in range(4):
        t = sweep_engine.suggest_trial("proj_analysis", sweep.sweep_id)
        assert t is not None
        sweep_engine.record_trial_result(
            "proj_analysis",
            sweep.sweep_id,
            t.trial_id,
            metrics={"val_loss": 0.4 - i * 0.05, "accuracy": 0.8 + i * 0.03},
            status="completed",
        )

    analysis = sweep_engine.analyze_sweep("proj_analysis", sweep.sweep_id)
    assert analysis["completed_trials"] == 4
    assert analysis["best_trial"] is not None
    assert "parameter_importance" in analysis
    assert len(analysis["pareto_frontier"]) > 0

    md = sweep_engine.export_sweep_markdown("proj_analysis", sweep.sweep_id)
    assert "Hyperparameter Optimization Report" in md
    assert "Optimal Configuration" in md
    assert "Trial History" in md
