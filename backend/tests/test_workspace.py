"""Tests for workspace persistence and knowledge graph."""

import json
import os
import tempfile

import pytest

from openmlr.workspace.knowledge import KnowledgeGraph
from openmlr.workspace.persistence import WorkspacePersistence

pytestmark = pytest.mark.asyncio


@pytest.fixture
def workspace_dir():
    """Create a temporary workspace directory with standard structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create standard subdirs
        for subdir in [
            "code",
            "data",
            "models",
            "outputs",
            "papers",
            "research",
            "research/searches",
            "research/notes",
            "research/citations",
            "logs",
            "logs/tool_failures",
            "logs/compute",
            "logs/experiments",
            "venvs",
            ".project-meta",
            ".project-meta/plans",
        ]:
            os.makedirs(os.path.join(tmpdir, subdir), exist_ok=True)
        yield tmpdir


# ── Knowledge Graph ──────────────────────────────────────


class TestKnowledgeGraph:
    def test_init_empty(self, workspace_dir):
        kg = KnowledgeGraph(workspace_dir)
        assert kg.node_count == 0
        assert kg.edge_count == 0

    def test_add_entity(self, workspace_dir):
        kg = KnowledgeGraph(workspace_dir)
        is_new = kg.add_entity("paper-1", "paper", "Attention Is All You Need")
        assert is_new is True
        assert kg.node_count == 1

    def test_add_entity_update(self, workspace_dir):
        kg = KnowledgeGraph(workspace_dir)
        kg.add_entity("paper-1", "paper", "Original Label")
        is_new = kg.add_entity("paper-1", "paper", "Updated Label")
        assert is_new is False
        assert kg.node_count == 1

        entity = kg.get_entity("paper-1")
        assert entity["label"] == "Updated Label"

    def test_add_entity_with_properties(self, workspace_dir):
        kg = KnowledgeGraph(workspace_dir)
        kg.add_entity(
            "paper-1",
            "paper",
            "Test Paper",
            properties={
                "year": 2017,
                "abstract": "We propose a new architecture...",
            },
        )
        entity = kg.get_entity("paper-1")
        assert entity["year"] == 2017
        assert "architecture" in entity["abstract"]

    def test_get_nonexistent_entity(self, workspace_dir):
        kg = KnowledgeGraph(workspace_dir)
        assert kg.get_entity("nope") is None

    def test_find_entities_by_type(self, workspace_dir):
        kg = KnowledgeGraph(workspace_dir)
        kg.add_entity("p1", "paper", "Paper 1")
        kg.add_entity("p2", "paper", "Paper 2")
        kg.add_entity("m1", "method", "Method 1")

        papers = kg.find_entities("paper")
        assert len(papers) == 2

        methods = kg.find_entities("method")
        assert len(methods) == 1

    def test_search_entities(self, workspace_dir):
        kg = KnowledgeGraph(workspace_dir)
        kg.add_entity("attn", "method", "Self-Attention Mechanism")
        kg.add_entity("conv", "method", "Convolutional Neural Network")
        kg.add_entity("bert", "paper", "BERT: Pre-training")

        results = kg.search_entities("attention")
        assert len(results) == 1
        assert results[0]["id"] == "attn"

    def test_remove_entity(self, workspace_dir):
        kg = KnowledgeGraph(workspace_dir)
        kg.add_entity("rm-me", "paper", "Remove Me")
        assert kg.node_count == 1

        removed = kg.remove_entity("rm-me")
        assert removed is True
        assert kg.node_count == 0

    def test_remove_nonexistent_entity(self, workspace_dir):
        kg = KnowledgeGraph(workspace_dir)
        assert kg.remove_entity("nope") is False

    def test_add_relationship(self, workspace_dir):
        kg = KnowledgeGraph(workspace_dir)
        kg.add_entity("p1", "paper", "Paper 1")
        kg.add_entity("m1", "method", "Method 1")

        is_new = kg.add_relationship("p1", "m1", "proposes")
        assert is_new is True
        assert kg.edge_count == 1

    def test_add_relationship_missing_entity(self, workspace_dir):
        kg = KnowledgeGraph(workspace_dir)
        kg.add_entity("p1", "paper", "Paper 1")

        is_new = kg.add_relationship("p1", "missing", "proposes")
        assert is_new is False
        assert kg.edge_count == 0

    def test_get_neighbors(self, workspace_dir):
        kg = KnowledgeGraph(workspace_dir)
        kg.add_entity("p1", "paper", "Paper 1")
        kg.add_entity("m1", "method", "Method 1")
        kg.add_entity("m2", "method", "Method 2")
        kg.add_relationship("p1", "m1", "proposes")
        kg.add_relationship("p1", "m2", "proposes")

        neighbors = kg.get_neighbors("p1", direction="out")
        assert len(neighbors) == 2

        neighbors_in = kg.get_neighbors("m1", direction="in")
        assert len(neighbors_in) == 1

    def test_save_and_reload(self, workspace_dir):
        kg = KnowledgeGraph(workspace_dir)
        kg.add_entity("p1", "paper", "Paper 1", properties={"year": 2020})
        kg.add_entity("m1", "method", "Method 1")
        kg.add_relationship("p1", "m1", "proposes")
        kg.save()

        # Reload from disk
        kg2 = KnowledgeGraph(workspace_dir)
        assert kg2.node_count == 2
        assert kg2.edge_count == 1

        entity = kg2.get_entity("p1")
        assert entity["label"] == "Paper 1"
        assert entity["year"] == 2020

    def test_get_summary(self, workspace_dir):
        kg = KnowledgeGraph(workspace_dir)
        kg.add_entity("p1", "paper", "Paper 1")
        kg.add_entity("m1", "method", "Method 1")
        kg.add_relationship("p1", "m1", "proposes")

        summary = kg.get_summary()
        assert summary["total_nodes"] == 2
        assert summary["total_edges"] == 1
        assert "paper" in summary["type_counts"]
        assert "method" in summary["type_counts"]

    def test_get_context_for_conversation_empty(self, workspace_dir):
        kg = KnowledgeGraph(workspace_dir)
        context = kg.get_context_for_conversation()
        assert context == ""

    def test_get_context_for_conversation(self, workspace_dir):
        kg = KnowledgeGraph(workspace_dir)
        kg.add_entity("p1", "paper", "Attention Paper")
        kg.add_entity("m1", "method", "Self-Attention")
        kg.add_relationship("p1", "m1", "proposes")

        context = kg.get_context_for_conversation()
        assert "Attention Paper" in context
        assert "Self-Attention" in context
        assert "proposes" in context


# ── Workspace Persistence ────────────────────────────────


class TestWorkspacePersistence:
    def test_save_search_results(self, workspace_dir):
        wp = WorkspacePersistence(workspace_dir)
        filepath = wp.save_search_results(
            query="transformer attention",
            source="arxiv",
            results=[{"title": "Paper 1"}, {"title": "Paper 2"}],
        )
        assert filepath.exists()
        data = json.loads(filepath.read_text())
        assert data["query"] == "transformer attention"
        assert data["source"] == "arxiv"
        assert len(data["results"]) == 2

    def test_get_recent_searches(self, workspace_dir):
        wp = WorkspacePersistence(workspace_dir)
        wp.save_search_results("q1", "arxiv", [{"t": "r1"}])
        wp.save_search_results("q2", "openalex", [{"t": "r2"}])

        searches = wp.get_recent_searches(limit=10)
        assert len(searches) == 2

    def test_save_research_note(self, workspace_dir):
        wp = WorkspacePersistence(workspace_dir)
        filepath = wp.save_research_note(
            topic="Attention Mechanisms",
            content="Self-attention allows models to...",
        )
        assert filepath.exists()
        content = filepath.read_text()
        assert "Attention Mechanisms" in content
        assert "Self-attention allows" in content

    def test_get_research_notes(self, workspace_dir):
        wp = WorkspacePersistence(workspace_dir)
        wp.save_research_note("Note 1", "Content 1")
        wp.save_research_note("Note 2", "Content 2")

        notes = wp.get_research_notes()
        assert len(notes) == 2

    def test_save_paper(self, workspace_dir):
        wp = WorkspacePersistence(workspace_dir)
        filepath = wp.save_paper(
            paper_id="2301.12345",
            title="Test Paper",
            content="## Introduction\n\nThis paper...",
            metadata={"authors": "Smith et al.", "year": 2023},
        )
        assert filepath.exists()
        content = filepath.read_text()
        assert "Test Paper" in content
        assert "Introduction" in content

    def test_log_tool_failure(self, workspace_dir):
        wp = WorkspacePersistence(workspace_dir)
        filepath = wp.log_tool_failure(
            tool_name="papers",
            error="arXiv rate limit reached",
            args={"query": "test"},
        )
        assert filepath.exists()
        data = json.loads(filepath.read_text())
        assert data["tool"] == "papers"
        assert "rate limit" in data["error"]

    def test_get_recent_failures(self, workspace_dir):
        wp = WorkspacePersistence(workspace_dir)
        wp.log_tool_failure("papers", "Error 1")
        wp.log_tool_failure("web_search", "Error 2")

        failures = wp.get_recent_failures()
        assert len(failures) == 2

    def test_log_compute_probe(self, workspace_dir):
        wp = WorkspacePersistence(workspace_dir)
        filepath = wp.log_compute_probe(
            node_name="gpu-server",
            capabilities={"gpu": "A100", "ram_gb": 128},
        )
        assert filepath.exists()

    def test_log_experiment(self, workspace_dir):
        wp = WorkspacePersistence(workspace_dir)
        filepath = wp.log_experiment(
            name="train-bert",
            command="python train.py --lr 0.001",
            result={"loss": 0.05, "accuracy": 0.95},
        )
        assert filepath.exists()
        data = json.loads(filepath.read_text())
        assert data["name"] == "train-bert"
        assert data["result"]["accuracy"] == 0.95

    def test_state_persistence(self, workspace_dir):
        wp = WorkspacePersistence(workspace_dir)

        # Initial state
        state = wp.get_state()
        assert state.get("key_findings") == [] or state.get("key_findings") is None

        # Update state
        wp.update_state(
            key_findings=["Attention is effective for NLP"],
            open_questions=["Does it scale?"],
        )

        # Reload
        wp2 = WorkspacePersistence(workspace_dir)
        state2 = wp2.get_state()
        assert "Attention is effective for NLP" in state2["key_findings"]
        assert "Does it scale?" in state2["open_questions"]

    def test_save_plan(self, workspace_dir):
        wp = WorkspacePersistence(workspace_dir)
        filepath = wp.save_plan(
            plan_content="# Plan\n\n1. Read papers\n2. Train model",
            conversation_uuid="test-conv-uuid",
        )
        assert filepath.exists()
        assert "Read papers" in filepath.read_text()

    def test_get_workspace_summary(self, workspace_dir):
        wp = WorkspacePersistence(workspace_dir)

        # Add some files
        wp.save_search_results("q1", "arxiv", [])
        wp.save_research_note("Note", "Content")
        wp.log_tool_failure("test", "Error")

        summary = wp.get_workspace_summary()
        assert summary["search_results"] >= 1
        assert summary["research_notes"] >= 1
        assert summary["tool_failures"] >= 1
