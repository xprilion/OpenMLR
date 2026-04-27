"""Tests for workspace agent tools."""

import os
import tempfile

import pytest

from openmlr.tools.workspace_tools import (
    _handle_workspace,
    create_workspace_tools,
    set_workspace_context,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture
def workspace_dir():
    """Create a temporary workspace directory with standard structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
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
            ".project-meta",
            ".project-meta/plans",
        ]:
            os.makedirs(os.path.join(tmpdir, subdir), exist_ok=True)
        set_workspace_context(tmpdir)
        yield tmpdir
        set_workspace_context(None)


class TestWorkspaceTools:
    def test_create_workspace_tools(self):
        tools = create_workspace_tools()
        assert len(tools) == 1
        assert tools[0].name == "workspace"

    async def test_status_operation(self, workspace_dir):
        result, success = await _handle_workspace(operation="status")
        assert success is True
        assert "Workspace Status" in result

    async def test_note_operation(self, workspace_dir):
        result, success = await _handle_workspace(
            operation="note",
            topic="Test Topic",
            content="This is a test note.",
        )
        assert success is True
        assert "saved" in result.lower()

    async def test_note_missing_params(self, workspace_dir):
        result, success = await _handle_workspace(operation="note", topic="", content="")
        assert success is False

    async def test_knowledge_add_operation(self, workspace_dir):
        result, success = await _handle_workspace(
            operation="knowledge_add",
            entity_id="paper-1",
            entity_type="paper",
            label="Test Paper",
        )
        assert success is True
        assert "Added" in result

    async def test_knowledge_add_with_properties(self, workspace_dir):
        result, success = await _handle_workspace(
            operation="knowledge_add",
            entity_id="paper-2",
            entity_type="paper",
            label="Paper 2",
            properties='{"year": 2024, "venue": "NeurIPS"}',
        )
        assert success is True

    async def test_knowledge_add_missing_params(self, workspace_dir):
        result, success = await _handle_workspace(
            operation="knowledge_add",
            entity_id="",
            entity_type="",
            label="",
        )
        assert success is False

    async def test_knowledge_relate_operation(self, workspace_dir):
        # Add entities first
        await _handle_workspace(
            operation="knowledge_add",
            entity_id="p1",
            entity_type="paper",
            label="Paper 1",
        )
        await _handle_workspace(
            operation="knowledge_add",
            entity_id="m1",
            entity_type="method",
            label="Method 1",
        )

        result, success = await _handle_workspace(
            operation="knowledge_relate",
            source_id="p1",
            target_id="m1",
            relationship="proposes",
        )
        assert success is True
        assert "proposes" in result

    async def test_knowledge_relate_missing_entity(self, workspace_dir):
        await _handle_workspace(
            operation="knowledge_add",
            entity_id="p1",
            entity_type="paper",
            label="Paper 1",
        )
        result, success = await _handle_workspace(
            operation="knowledge_relate",
            source_id="p1",
            target_id="missing",
            relationship="proposes",
        )
        assert success is False

    async def test_knowledge_query_operation(self, workspace_dir):
        await _handle_workspace(
            operation="knowledge_add",
            entity_id="attn",
            entity_type="method",
            label="Self-Attention",
        )
        result, success = await _handle_workspace(
            operation="knowledge_query",
            query="attention",
        )
        assert success is True
        assert "Self-Attention" in result

    async def test_knowledge_query_no_results(self, workspace_dir):
        result, success = await _handle_workspace(
            operation="knowledge_query",
            query="nonexistent",
        )
        assert success is True
        assert "No entities found" in result

    async def test_knowledge_summary_empty(self, workspace_dir):
        result, success = await _handle_workspace(operation="knowledge_summary")
        assert success is True
        assert "empty" in result.lower()

    async def test_knowledge_summary_with_data(self, workspace_dir):
        await _handle_workspace(
            operation="knowledge_add",
            entity_id="p1",
            entity_type="paper",
            label="Test Paper",
        )
        result, success = await _handle_workspace(operation="knowledge_summary")
        assert success is True
        assert "Test Paper" in result

    async def test_recent_failures_empty(self, workspace_dir):
        result, success = await _handle_workspace(operation="recent_failures")
        assert success is True
        assert "No recent" in result

    async def test_search_operation(self, workspace_dir):
        # Create a test file
        test_file = os.path.join(workspace_dir, "code", "test.py")
        with open(test_file, "w") as f:
            f.write("import torch\nmodel = TransformerModel()")

        result, success = await _handle_workspace(
            operation="search",
            query="transformer",
        )
        assert success is True
        assert "test.py" in result

    async def test_search_no_results(self, workspace_dir):
        result, success = await _handle_workspace(
            operation="search",
            query="xyznonexistent",
        )
        assert success is True
        assert "No files found" in result

    async def test_unknown_operation(self, workspace_dir):
        result, success = await _handle_workspace(operation="unknown_op")
        assert success is False

    async def test_no_workspace_context(self):
        set_workspace_context(None)
        result, success = await _handle_workspace(operation="status")
        assert success is False
        assert "No project workspace" in result
