"""Tests for inspect_files tool — parallel reading, relevance scoring, security."""

import pytest

from openmlr.tools.inspect import (
    _is_relative,
    _read_file_snippet,
    _score_relevance,
    create_inspect_tool,
)

pytestmark = pytest.mark.asyncio


class TestScoreRelevance:
    def test_full_match(self):
        score = _score_relevance("the training loop runs for epochs", "training loop")
        assert score == pytest.approx(1.0)

    def test_partial_match(self):
        score = _score_relevance("the training loop runs", "training loop optimizer")
        assert 0.3 < score < 1.0

    def test_no_match(self):
        score = _score_relevance("hello world", "gradient descent")
        assert score == pytest.approx(0.0)

    def test_short_query_terms_ignored(self):
        """Words <= 2 chars are excluded from scoring."""
        score = _score_relevance("hello world", "a b c")
        assert score == pytest.approx(0.5)  # fallback for no useful terms

    def test_case_insensitive(self):
        score = _score_relevance("Training Loop OPTIMIZER", "training loop optimizer")
        assert score == pytest.approx(1.0)

    def test_empty_content(self):
        score = _score_relevance("", "training")
        assert score == pytest.approx(0.0)


class TestReadFileSnippet:
    def test_small_file(self, tmp_path):
        f = tmp_path / "small.txt"
        f.write_text("line one\nline two\nline three")
        content, lines = _read_file_snippet(f)
        assert lines == 3
        assert "1: line one" in content
        assert "3: line three" in content

    def test_truncates_large_files(self, tmp_path):
        f = tmp_path / "large.txt"
        f.write_text("\n".join(f"line {i}" for i in range(500)))
        content, lines = _read_file_snippet(f)
        assert lines == 500
        assert "more lines truncated" in content

    def test_nonexistent_file(self, tmp_path):
        f = tmp_path / "missing.txt"
        content, lines = _read_file_snippet(f)
        assert content == ""
        assert lines == 0

    def test_large_file_skipped(self, tmp_path):
        f = tmp_path / "huge.bin"
        # Write a 3MB file (above _MAX_FILE_SIZE of 2MB)
        f.write_bytes(b"x" * (3 * 1024 * 1024))
        content, lines = _read_file_snippet(f)
        assert "too large" in content.lower()
        assert lines == 0

    def test_binary_file_graceful(self, tmp_path):
        f = tmp_path / "binary.dat"
        f.write_bytes(b"\x00\x01\x02\xff" * 100)
        content, _ = _read_file_snippet(f)
        # Should not crash — errors="replace" handles it
        assert isinstance(content, str)


class TestIsRelative:
    def test_relative(self, tmp_path):
        child = tmp_path / "sub" / "file.txt"
        assert _is_relative(child, tmp_path) is True

    def test_not_relative(self, tmp_path):
        from pathlib import Path

        assert _is_relative(Path("/etc/passwd"), tmp_path) is False


class TestCreateInspectTool:
    def test_creates_tool(self):
        tool = create_inspect_tool()
        assert tool.name == "inspect_files"
        assert tool.handler is not None
        assert "paths" in tool.parameters["properties"]
        assert "query" in tool.parameters["properties"]


class TestHandleInspectFiles:
    async def test_empty_paths(self):
        from openmlr.tools.inspect import _handle_inspect_files

        output, success = await _handle_inspect_files(paths=[], query="test")
        assert success is False
        assert "No paths" in output

    async def test_empty_query(self):
        from openmlr.tools.inspect import _handle_inspect_files

        output, success = await _handle_inspect_files(paths=["file.py"], query="")
        assert success is False
        assert "No query" in output

    async def test_reads_files_from_directory(self, tmp_path, monkeypatch):
        """inspect_files reads files from a directory and scores relevance."""
        from openmlr.tools.inspect import _handle_inspect_files
        from openmlr.tools.local import _project_workspace_var

        # Set workspace to tmp_path
        token = _project_workspace_var.set(str(tmp_path))
        try:
            # Create test files
            (tmp_path / "train.py").write_text("def training_loop():\n    pass")
            (tmp_path / "utils.py").write_text("def helper():\n    pass")

            output, success = await _handle_inspect_files(
                paths=[str(tmp_path)], query="training loop"
            )
            assert success is True
            assert "train.py" in output
        finally:
            _project_workspace_var.reset(token)

    async def test_respects_max_files(self, tmp_path, monkeypatch):
        """max_files limits how many files are read."""
        from openmlr.tools.inspect import _handle_inspect_files
        from openmlr.tools.local import _project_workspace_var

        token = _project_workspace_var.set(str(tmp_path))
        try:
            for i in range(10):
                (tmp_path / f"file_{i}.py").write_text(f"content {i}")

            output, success = await _handle_inspect_files(
                paths=[str(tmp_path)], query="content", max_files=3
            )
            assert success is True
            assert "Truncated" in output
        finally:
            _project_workspace_var.reset(token)

    async def test_negative_max_files_clamped(self, tmp_path):
        """Negative max_files is clamped to 1."""
        from openmlr.tools.inspect import _handle_inspect_files
        from openmlr.tools.local import _project_workspace_var

        token = _project_workspace_var.set(str(tmp_path))
        try:
            (tmp_path / "a.txt").write_text("hello")
            (tmp_path / "b.txt").write_text("world")

            _, success = await _handle_inspect_files(
                paths=[str(tmp_path)], query="hello", max_files=-5
            )
            assert success is True
            # Should not crash or read zero files
        finally:
            _project_workspace_var.reset(token)

    async def test_symlink_outside_workspace_blocked(self, tmp_path):
        """Symlinks pointing outside the workspace should be skipped."""
        import os

        from openmlr.tools.inspect import _handle_inspect_files
        from openmlr.tools.local import _project_workspace_var

        workspace = tmp_path / "workspace"
        workspace.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "secret.txt").write_text("sensitive data")

        # Create symlink from workspace to outside
        symlink = workspace / "link_to_outside.txt"
        try:
            os.symlink(outside / "secret.txt", symlink)
        except OSError:
            pytest.skip("Symlinks not supported on this platform")

        token = _project_workspace_var.set(str(workspace))
        try:
            output, success = await _handle_inspect_files(paths=[str(workspace)], query="sensitive")
            assert success is True
            assert "sensitive data" not in output
        finally:
            _project_workspace_var.reset(token)
