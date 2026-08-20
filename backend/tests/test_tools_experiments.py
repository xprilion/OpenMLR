"""Tests for experiments tool (openmlr/tools/experiments.py)."""

import json
from pathlib import Path

import pytest

from openmlr.agent.types import ToolSpec
from openmlr.services.experiment_tracker import ExperimentTracker
from openmlr.tools.experiments import (
    _handle_experiments,
    create_experiments_tool,
    set_experiment_context,
)
from openmlr.tools.workspace_tools import set_workspace_context
from openmlr.workspace.knowledge import KnowledgeGraph


@pytest.fixture
def clean_tracker(tmp_path: Path):
    tracker = ExperimentTracker(storage_dir=tmp_path / "experiments")
    set_experiment_context(tracker, project_uuid="proj-test-123")
    yield tracker
    set_experiment_context(None, None)


class TestExperimentsToolSpec:
    def test_creates_tool_spec(self):
        tool = create_experiments_tool()
        assert isinstance(tool, ToolSpec)
        assert tool.name == "experiments"
        assert tool.handler is not None
        assert "create_run" in tool.description
        assert "log_metrics" in tool.description
        assert "record_checkpoint" in tool.description
        assert "compare_runs" in tool.description
        assert "operation" in tool.parameters["properties"]


class TestExperimentsToolCreateRun:
    async def test_create_run_success(self, clean_tracker):
        out, success = await _handle_experiments(
            operation="create_run",
            name="Attention-Optimization-v1",
            description="Testing FlashAttention v2 vs baseline",
            hyperparameters={"lr": 0.0003, "batch_size": 32, "layers": 12},
            compute_target="Modal A100",
            tags=["transformer", "attention", "speedup"],
            total_steps=500,
            total_epochs=5,
        )
        assert success is True
        data = json.loads(out)
        assert data["name"] == "Attention-Optimization-v1"
        assert data["compute_target"] == "Modal A100"
        assert data["total_steps"] == 500
        assert data["hyperparameters"]["lr"] == 0.0003
        assert "run_id" in data

    async def test_create_run_missing_name(self, clean_tracker):
        out, success = await _handle_experiments(operation="create_run", name="")
        assert success is False
        assert "name" in out.lower()

    async def test_create_run_json_strings(self, clean_tracker):
        out, success = await _handle_experiments(
            operation="create_run",
            name="JSON-String-Run",
            hyperparameters='{"lr": 0.001, "optimizer": "AdamW"}',
            tags="llm, bert, fine-tune",
        )
        assert success is True
        data = json.loads(out)
        assert data["hyperparameters"]["optimizer"] == "AdamW"


class TestExperimentsToolLogMetrics:
    async def test_log_metrics_success(self, clean_tracker):
        # Create run first
        create_out, _ = await _handle_experiments(operation="create_run", name="Metrics-Run")
        run_id = json.loads(create_out)["run_id"]

        # Log step 10
        out1, success1 = await _handle_experiments(
            operation="log_metrics",
            run_id=run_id,
            step=10,
            epoch=1,
            metrics={"train_loss": 3.42, "val_loss": 3.51, "learning_rate": 0.0003},
        )
        assert success1 is True
        data1 = json.loads(out1)
        assert data1["current_step"] == 10
        assert data1["best_val_loss"] == 3.51

        # Log step 20 with better val loss
        out2, success2 = await _handle_experiments(
            operation="log_metrics",
            run_id=run_id,
            step=20,
            epoch=1,
            metrics='{"train_loss": 2.85, "val_loss": 2.91}',
        )
        assert success2 is True
        data2 = json.loads(out2)
        assert data2["best_val_loss"] == 2.91

    async def test_log_metrics_missing_run_id_or_empty(self, clean_tracker):
        out, success = await _handle_experiments(operation="log_metrics", run_id="", metrics={"val_loss": 1.0})
        assert success is False
        assert "run_id" in out

        out2, success2 = await _handle_experiments(operation="log_metrics", run_id="nonexistent", metrics={})
        assert success2 is False

    async def test_log_metrics_nonexistent_run(self, clean_tracker):
        out, success = await _handle_experiments(
            operation="log_metrics",
            run_id="run-fake-999",
            step=1,
            metrics={"train_loss": 2.0},
        )
        assert success is False
        assert "not found" in out.lower()


class TestExperimentsToolCheckpoints:
    async def test_record_checkpoint_success(self, clean_tracker):
        create_out, _ = await _handle_experiments(operation="create_run", name="Checkpoint-Run")
        run_id = json.loads(create_out)["run_id"]

        out, success = await _handle_experiments(
            operation="record_checkpoint",
            run_id=run_id,
            checkpoint_name="best_model.pt",
            path="checkpoints/best_model.pt",
            file_size_mb=420.5,
            step=250,
            epoch=2,
            metrics={"val_loss": 1.84, "accuracy": 0.892},
        )
        assert success is True
        data = json.loads(out)
        assert data["total_checkpoints"] == 1
        assert data["checkpoint"]["name"] == "best_model.pt"
        assert data["checkpoint"]["metrics"]["accuracy"] == 0.892


class TestExperimentsToolGetRun:
    async def test_get_run_details(self, clean_tracker):
        create_out, _ = await _handle_experiments(
            operation="create_run",
            name="Inspect-Run",
            description="Testing retrieval",
            hyperparameters={"weight_decay": 0.01},
        )
        run_id = json.loads(create_out)["run_id"]

        await _handle_experiments(
            operation="log_metrics",
            run_id=run_id,
            step=50,
            metrics={"train_loss": 1.2, "val_loss": 1.4},
        )

        out, success = await _handle_experiments(operation="get_run", run_id=run_id)
        assert success is True
        data = json.loads(out)
        assert data["run_id"] == run_id
        assert data["name"] == "Inspect-Run"
        assert data["latest_metrics"]["train_loss"] == 1.2
        assert data["latest_metrics"]["val_loss"] == 1.4


class TestExperimentsToolListAndCompare:
    async def test_list_and_compare_runs(self, clean_tracker):
        # Create Run A
        out_a, _ = await _handle_experiments(
            operation="create_run",
            name="Model-Baseline",
            hyperparameters={"lr": 0.001, "arch": "standard"},
            tags=["baseline"],
        )
        id_a = json.loads(out_a)["run_id"]
        await _handle_experiments(
            operation="log_metrics",
            run_id=id_a,
            step=100,
            metrics={"train_loss": 1.5, "val_loss": 1.6},
        )

        # Create Run B
        out_b, _ = await _handle_experiments(
            operation="create_run",
            name="Model-Modified",
            hyperparameters={"lr": 0.0003, "arch": "improved"},
            tags=["modified"],
        )
        id_b = json.loads(out_b)["run_id"]
        await _handle_experiments(
            operation="log_metrics",
            run_id=id_b,
            step=100,
            metrics={"train_loss": 1.1, "val_loss": 1.2},
        )

        # List runs
        list_out, list_ok = await _handle_experiments(operation="list_runs")
        assert list_ok is True
        list_data = json.loads(list_out)
        assert list_data["total_runs"] >= 2

        # Compare runs
        cmp_out, cmp_ok = await _handle_experiments(
            operation="compare_runs",
            run_ids=f"{id_a}, {id_b}",
        )
        assert cmp_ok is True
        cmp_data = json.loads(cmp_out)
        assert id_a in cmp_data["metrics_summary"]
        assert id_b in cmp_data["metrics_summary"]
        assert cmp_data["hyperparameters_comparison"]["arch"][id_a] == "standard"
        assert cmp_data["hyperparameters_comparison"]["arch"][id_b] == "improved"


class TestExperimentsToolCompleteRun:
    async def test_complete_run(self, clean_tracker):
        create_out, _ = await _handle_experiments(operation="create_run", name="To-Complete")
        run_id = json.loads(create_out)["run_id"]

        out, success = await _handle_experiments(
            operation="complete_run",
            run_id=run_id,
            status="completed",
            best_val_loss=1.15,
            reason="Finished all 500 steps with convergence",
        )
        assert success is True
        data = json.loads(out)
        assert data["status"] == "completed"
        assert data["best_val_loss"] == 1.15


class TestExperimentsToolInvalidOperation:
    async def test_invalid_op(self, clean_tracker):
        out, success = await _handle_experiments(operation="unknown_op")
        assert success is False
        assert "Unknown experiments operation" in out


class TestKnowledgeGraphIntegration:
    async def test_auto_registers_in_knowledge_graph(self, clean_tracker, tmp_path: Path):
        set_workspace_context(str(tmp_path))

        out, success = await _handle_experiments(
            operation="create_run",
            name="KG-Tracked-Experiment",
            hyperparameters={"batch_size": 64},
        )
        assert success is True
        run_id = json.loads(out)["run_id"]

        # Verify entity exists in knowledge graph
        kg = KnowledgeGraph(str(tmp_path))
        entity = kg.get_entity(f"exp_{run_id}")
        assert entity is not None
        assert entity["label"] == "KG-Tracked-Experiment"
        assert entity["type"] == "experiment"

        # Complete and check update
        await _handle_experiments(
            operation="complete_run",
            run_id=run_id,
            status="completed",
            best_val_loss=0.88,
        )
        kg_updated = KnowledgeGraph(str(tmp_path))
        updated_entity = kg_updated.get_entity(f"exp_{run_id}")
        assert updated_entity is not None
        assert updated_entity["status"] == "completed"
        assert updated_entity["best_val_loss"] == 0.88

        set_workspace_context(None)
