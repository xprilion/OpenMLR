"""Tests for local tools — bash, read, write, edit, and path validation."""

import os
from pathlib import Path

import pytest

from openmlr.tools.local import (
    CONTAINER_PREFIX,
    DOCKER_IMAGE,
    _get_effective_root,
    _handle_edit,
    _handle_read,
    _handle_write,
    _running_in_container,
    _validate_path,
    create_local_tools,
    set_project_workspace,
)


class TestCreateLocalTools:
    def test_creates_all_tools(self):
        tools = create_local_tools()
        names = [t.name for t in tools]
        assert "bash" in names
        assert "read" in names
        assert "write" in names
        assert "edit" in names
        assert len(tools) == 4

    def test_bash_tool_spec(self):
        tools = create_local_tools()
        bash = [t for t in tools if t.name == "bash"][0]
        assert "command" in bash.parameters["properties"]
        assert "timeout" in bash.parameters["properties"]
        assert "workdir" in bash.parameters["properties"]
        assert "command" in bash.parameters["required"]

    def test_read_tool_spec(self):
        tools = create_local_tools()
        read_tool = [t for t in tools if t.name == "read"][0]
        assert read_tool.handler is not None
        assert "path" in read_tool.parameters["required"]

    def test_write_tool_spec(self):
        tools = create_local_tools()
        write_tool = [t for t in tools if t.name == "write"][0]
        assert "path" in write_tool.parameters["required"]
        assert "content" in write_tool.parameters["required"]

    def test_edit_tool_spec(self):
        tools = create_local_tools()
        edit_tool = [t for t in tools if t.name == "edit"][0]
        required = edit_tool.parameters["required"]
        assert "path" in required
        assert "old_string" in required
        assert "new_string" in required


class TestValidatePath:
    def test_resolves_relative_path(self):
        cwd = os.getcwd()
        path = Path(".", "test_file.txt")
        resolved, error = _validate_path(path)
        assert error is None
        assert resolved.is_absolute()

    def test_path_within_cwd_is_allowed(self):
        path = Path.cwd() / "test" / "file.py"
        resolved, error = _validate_path(path)
        assert error is None

    def test_blocked_system_path(self, monkeypatch):
        monkeypatch.setattr("openmlr.tools.local.WORKSPACE_ROOT", "/home/user/projects")
        path = Path("/etc", "passwd")
        resolved, error = _validate_path(path)
        assert error is not None
        assert "outside workspace" in error or "protected system directory" in error

    def test_blocked_root_path(self, monkeypatch):
        monkeypatch.setattr("openmlr.tools.local.WORKSPACE_ROOT", "/home/user/projects")
        path = Path("/root", "secret")
        resolved, error = _validate_path(path)
        assert error is not None

    def test_blocked_var_path(self, monkeypatch):
        monkeypatch.setattr("openmlr.tools.local.WORKSPACE_ROOT", "/home/user/projects")
        path = Path("/var", "log")
        resolved, error = _validate_path(path)
        assert error is not None

    def test_blocked_bin_path(self):
        path = Path("/bin", "bash")
        resolved, error = _validate_path(path)
        assert error is not None

    def test_with_workspace_root_set(self, monkeypatch):
        workspace = str(Path.cwd() / "workspace")
        monkeypatch.setattr("openmlr.tools.local.WORKSPACE_ROOT", workspace)
        within = Path(workspace) / "file.txt"
        resolved, error = _validate_path(within)
        assert error is None


class TestProjectWorkspace:
    """Tests for project workspace targeting (set_project_workspace, _get_effective_root)."""

    def test_get_effective_root_defaults_to_cwd(self):
        set_project_workspace(None)
        root = _get_effective_root()
        assert root == Path.cwd().resolve()

    def test_get_effective_root_uses_project_workspace(self, tmp_path):
        set_project_workspace(str(tmp_path))
        try:
            root = _get_effective_root()
            assert root == tmp_path.resolve()
        finally:
            set_project_workspace(None)

    def test_get_effective_root_prefers_project_over_env(self, tmp_path, monkeypatch):
        monkeypatch.setattr("openmlr.tools.local.WORKSPACE_ROOT", "/some/other/path")
        set_project_workspace(str(tmp_path))
        try:
            root = _get_effective_root()
            assert root == tmp_path.resolve()
        finally:
            set_project_workspace(None)

    def test_validate_path_allows_project_workspace(self, tmp_path):
        set_project_workspace(str(tmp_path))
        try:
            path = tmp_path / "code" / "train.py"
            resolved, error = _validate_path(path)
            assert error is None
        finally:
            set_project_workspace(None)

    def test_validate_path_blocks_outside_project_workspace(self, tmp_path, monkeypatch):
        other_dir = tmp_path / "other"
        other_dir.mkdir()
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        set_project_workspace(str(project_dir))
        # Also change cwd so the "also allow CWD" fallback doesn't save it
        monkeypatch.chdir(project_dir)
        try:
            path = other_dir / "secret.txt"
            resolved, error = _validate_path(path)
            assert error is not None
            assert "outside workspace" in error
        finally:
            set_project_workspace(None)

    def test_set_project_workspace_clears(self):
        set_project_workspace("/tmp/test-project")
        set_project_workspace(None)
        root = _get_effective_root()
        # Should fall back to CWD or WORKSPACE_ROOT, not /tmp/test-project
        assert str(root) != "/tmp/test-project"


@pytest.mark.asyncio
class TestHandleRead:
    async def test_reads_file_with_line_numbers(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        f = tmp_path / "test.txt"
        f.write_text("line one\nline two\nline three\n")
        result, success = await _handle_read("test.txt")
        assert success is True
        assert "1: line one" in result
        assert "2: line two" in result
        assert "3: line three" in result

    async def test_read_with_offset_and_limit(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        f = tmp_path / "test.txt"
        f.write_text("a\nb\nc\nd\ne\n")
        result, success = await _handle_read("test.txt", offset=3, limit=2)
        assert success is True
        assert "3: c" in result
        assert "4: d" in result
        assert "5: e" not in result

    async def test_read_nonexistent_file(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        result, success = await _handle_read("nonexistent_test_file.txt")
        assert success is False
        assert "File not found" in result

    async def test_read_directory(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        d = tmp_path / "testdir"
        d.mkdir()
        (d / "file1.txt").write_text("x")
        (d / "file2.txt").write_text("y")
        result, success = await _handle_read("testdir")
        assert success is True
        assert "file1.txt" in result
        assert "file2.txt" in result


@pytest.mark.asyncio
class TestHandleWrite:
    async def test_writes_file(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        f = tmp_path / "output.txt"
        result, success = await _handle_write("output.txt", content="hello world")
        assert success is True
        assert "Wrote" in result
        assert f.read_text() == "hello world"

    async def test_creates_parent_directories(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        f = tmp_path / "deeply" / "nested" / "dir" / "file.txt"
        result, success = await _handle_write("deeply/nested/dir/file.txt", content="deep")
        assert success is True
        assert f.read_text() == "deep"

    async def test_requires_path(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        result, success = await _handle_write(path="", content="test")
        assert success is False

    async def test_requires_content(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        result, success = await _handle_write(path="test.txt", content="")
        assert success is False


@pytest.mark.asyncio
class TestHandleEdit:
    async def test_replaces_string(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        f = tmp_path / "edit_test.txt"
        f.write_text("Hello World")
        result, success = await _handle_edit("edit_test.txt", "World", "Universe")
        assert success is True
        assert "Replaced" in result
        assert f.read_text() == "Hello Universe"

    async def test_old_string_not_found(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        f = tmp_path / "edit_test.txt"
        f.write_text("Hello World")
        result, success = await _handle_edit("edit_test.txt", "Mars", "Earth")
        assert success is False
        assert "old_string not found" in result

    async def test_multiple_matches_without_replace_all(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        f = tmp_path / "edit_test.txt"
        f.write_text("hello hello hello")
        result, success = await _handle_edit("edit_test.txt", "hello", "hi")
        assert success is False
        assert "Found 3 matches" in result

    async def test_replace_all(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        f = tmp_path / "edit_test.txt"
        f.write_text("hello hello hello")
        result, success = await _handle_edit("edit_test.txt", "hello", "hi", replace_all=True)
        assert success is True
        assert f.read_text() == "hi hi hi"

    async def test_nonexistent_file(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        result, success = await _handle_edit("nonexistent_edit_test.txt", "a", "b")
        assert success is False
        assert "File not found" in result


class TestModuleConstants:
    def test_docker_image_default(self):
        assert DOCKER_IMAGE == "python:3.12-slim"

    def test_container_prefix(self):
        assert CONTAINER_PREFIX == "openmlr-sandbox"

    def test_allow_direct_exec_default(self, monkeypatch):
        monkeypatch.delenv("OPENMLR_ALLOW_DIRECT_EXEC", raising=False)
        import openmlr.tools.local

        allow = openmlr.tools.local.ALLOW_DIRECT_EXEC
        assert allow is False


class TestRunningInContainer:
    def test_returns_bool(self):
        # Just verify it returns a boolean (actual detection depends on environment)
        result = _running_in_container()
        assert isinstance(result, bool)

    def test_kubernetes_env_detected(self, monkeypatch):
        # Simulate Kubernetes environment
        monkeypatch.setenv("KUBERNETES_SERVICE_HOST", "10.0.0.1")
        # Reload the function to pick up the env var
        assert _running_in_container() is True

    def test_dockerenv_file_not_present_outside_container(self, monkeypatch, tmp_path):
        # When /.dockerenv doesn't exist and no other indicators
        monkeypatch.delenv("KUBERNETES_SERVICE_HOST", raising=False)
        # The function checks for /.dockerenv at system root, so on a host system
        # this should return False (unless we're actually in a container)
        # This is more of a smoke test
        result = _running_in_container()
        # Can't assert specific value as it depends on actual runtime environment
        assert isinstance(result, bool)
