"""Unit tests for the ExperimentTracker service."""

from pathlib import Path

from openmlr.services.experiment_tracker import ExperimentTracker


def test_create_and_get_run(tmp_path: Path):
    tracker = ExperimentTracker(storage_dir=tmp_path)
    run = tracker.create_run(
        name="Attention-Layer-Sweep",
        description="Testing multi-head vs rotary embeddings",
        hyperparameters={"lr": 0.001, "batch_size": 32, "layers": 12},
        compute_target="Local H100",
        tags=["nlp", "attention"],
        total_steps=500,
        total_epochs=10,
    )

    assert run.id.startswith("run-")
    assert run.name == "Attention-Layer-Sweep"
    assert run.status == "running"
    assert run.total_steps == 500
    assert run.hyperparameters["lr"] == 0.001

    fetched = tracker.get_run(run.id)
    assert fetched is not None
    assert fetched.name == "Attention-Layer-Sweep"
    assert fetched.tags == ["nlp", "attention"]


def test_list_runs_with_filtering(tmp_path: Path):
    tracker = ExperimentTracker(storage_dir=tmp_path)
    run1 = tracker.create_run(name="Run Alpha", tags=["vision"], project_uuid="proj-123")
    run2 = tracker.create_run(name="Run Beta", tags=["nlp"], project_uuid="proj-123")
    run3 = tracker.create_run(name="Run Gamma", tags=["rl"], project_uuid="proj-999")

    tracker.update_status(run1.id, "completed")
    tracker.update_status(run2.id, "running")

    # List all for proj-123
    runs, total = tracker.list_runs(project_uuid="proj-123")
    assert total == 2
    assert len(runs) == 2

    # Filter by status
    completed_runs, count = tracker.list_runs(project_uuid="proj-123", status="completed")
    assert count == 1
    assert completed_runs[0].id == run1.id

    # Filter by search
    searched, s_count = tracker.list_runs(search="beta")
    assert s_count == 1
    assert searched[0].name == "Run Beta"


def test_log_metrics_and_best_val_loss(tmp_path: Path):
    tracker = ExperimentTracker(storage_dir=tmp_path)
    run = tracker.create_run(name="Metric Run", total_steps=100)

    tracker.log_metrics(run.id, step=10, epoch=1, metrics={"train_loss": 2.5, "val_loss": 2.8})
    tracker.log_metrics(run.id, step=20, epoch=1, metrics={"train_loss": 2.0, "val_loss": 2.3})
    tracker.log_metrics(run.id, step=30, epoch=2, metrics={"train_loss": 1.7, "val_loss": 2.4})

    updated = tracker.get_run(run.id)
    assert updated is not None
    assert updated.current_step == 30
    assert updated.current_epoch == 2
    assert updated.best_val_loss == 2.3
    assert len(updated.metrics["train_loss"]) == 3
    assert len(updated.metrics["val_loss"]) == 3
    assert updated.metrics["train_loss"][-1].value == 1.7


def test_register_checkpoint_and_logs(tmp_path: Path):
    tracker = ExperimentTracker(storage_dir=tmp_path)
    run = tracker.create_run(name="Checkpoint Run")

    tracker.append_logs(run.id, ["Epoch 1 starting", "Step 50 reached: loss=1.8"])
    cp = tracker.register_checkpoint(
        run_id=run.id,
        name="step_50.pt",
        step=50,
        epoch=1,
        path="/models/step_50.pt",
        file_size_mb=450.5,
        metrics={"val_loss": 1.8},
    )

    assert cp.name == "step_50.pt"
    assert cp.file_size_mb == 450.5

    updated = tracker.get_run(run.id)
    assert updated is not None
    assert len(updated.checkpoints) == 1
    assert len(updated.logs) == 2
    assert "Step 50 reached" in updated.logs[1]


def test_compare_runs(tmp_path: Path):
    tracker = ExperimentTracker(storage_dir=tmp_path)
    r1 = tracker.create_run(name="R1", hyperparameters={"lr": 0.01, "opt": "adam"})
    r2 = tracker.create_run(name="R2", hyperparameters={"lr": 0.001, "opt": "sgd", "momentum": 0.9})

    tracker.log_metrics(r1.id, step=10, metrics={"train_loss": 1.5, "val_loss": 1.8})
    tracker.log_metrics(r2.id, step=10, metrics={"train_loss": 1.2, "val_loss": 1.4})

    comp = tracker.compare_runs([r1.id, r2.id])
    assert len(comp["runs"]) == 2
    assert "lr" in comp["hyperparameters_comparison"]
    assert comp["hyperparameters_comparison"]["lr"][r1.id] == 0.01
    assert comp["hyperparameters_comparison"]["lr"][r2.id] == 0.001
    assert comp["metrics_summary"][r1.id]["best_val_loss"] == 1.8
    assert comp["metrics_summary"][r2.id]["best_val_loss"] == 1.4


def test_persistence_and_reload(tmp_path: Path):
    tracker1 = ExperimentTracker(storage_dir=tmp_path)
    run = tracker1.create_run(name="Persistent Run", hyperparameters={"batch_size": 64})
    tracker1.log_metrics(run.id, step=5, metrics={"train_loss": 3.1})

    # Instantiate a new tracker pointing to the same directory
    tracker2 = ExperimentTracker(storage_dir=tmp_path)
    reloaded = tracker2.get_run(run.id)
    assert reloaded is not None
    assert reloaded.name == "Persistent Run"
    assert reloaded.hyperparameters["batch_size"] == 64
    assert len(reloaded.metrics["train_loss"]) == 1


def test_delete_run(tmp_path: Path):
    tracker = ExperimentTracker(storage_dir=tmp_path)
    run = tracker.create_run(name="To Delete")
    assert tracker.get_run(run.id) is not None

    deleted = tracker.delete_run(run.id)
    assert deleted is True
    assert tracker.get_run(run.id) is None

    # Deleting again returns False
    assert tracker.delete_run(run.id) is False
