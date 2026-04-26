"""Tests for sandbox interface types and LocalSandbox."""

import tempfile
from pathlib import Path
import pytest

from openmlr.sandbox.interface import EnvironmentInfo, ExecutionResult, SandboxInterface
from openmlr.sandbox.local import LocalSandbox
from openmlr.sandbox.manager import SandboxManager


class TestEnvironmentInfo:
    def test_defaults(self):
        info = EnvironmentInfo()
        assert info.os == "unknown"
        assert info.python_version == "unknown"
        assert info.gpu_available is False
        assert info.gpu_info is None
        assert info.installed_packages == []
        assert info.available_disk_gb == 0.0
        assert info.available_ram_gb == 0.0

    def test_custom_values(self):
        info = EnvironmentInfo(
            os="Linux",
            python_version="3.12.0",
            gpu_available=True,
            gpu_info="NVIDIA A100",
            installed_packages=["torch", "numpy"],
            available_disk_gb=50.0,
            available_ram_gb=32.0,
        )
        assert info.os == "Linux"
        assert info.gpu_available is True
        assert "torch" in info.installed_packages


class TestExecutionResult:
    def test_defaults(self):
        r = ExecutionResult(output="done", success=True)
        assert r.output == "done"
        assert r.success is True
        assert r.exit_code == 0
        assert r.duration_seconds == 0.0

    def test_failure(self):
        r = ExecutionResult(output="error", success=False, exit_code=1, duration_seconds=2.5)
        assert r.success is False
        assert r.exit_code == 1
        assert r.duration_seconds == 2.5

    def test_truncation_handled_by_caller(self):
        # Truncation is done by the tools, not the dataclass
        r = ExecutionResult(output="x" * 100000, success=True)
        assert len(r.output) == 100000


class TestSandboxInterface:
    def test_is_abstract(self):
        with pytest.raises(TypeError):
            SandboxInterface()


@pytest.mark.asyncio
class TestLocalSandbox:
    async def test_create_default(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        sb = LocalSandbox()
        await sb.create({})
        assert sb.workdir == str(tmp_path)

    async def test_create_with_workdir(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        sb = LocalSandbox()
        await sb.create({"workdir": str(tmp_path)})
        assert sb.workdir == str(tmp_path)

    async def test_write_and_read_file(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        sb = LocalSandbox(str(tmp_path))
        await sb.create({})
        f = tmp_path / "test.txt"
        ok = await sb.write_file(str(f), "hello")
        assert ok is True
        content = await sb.read_file("test.txt")
        assert content == "hello"

    async def test_file_exists(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        sb = LocalSandbox(str(tmp_path))
        await sb.create({})
        f = tmp_path / "exists.txt"
        f.write_text("data")
        assert await sb.file_exists("exists.txt") is True
        assert await sb.file_exists("nope.txt") is False

    async def test_edit_file(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        sb = LocalSandbox(str(tmp_path))
        await sb.create({})
        f = tmp_path / "edit.txt"
        f.write_text("old text here")
        ok = await sb.edit_file("edit.txt", "old", "new")
        assert ok is True
        assert f.read_text() == "new text here"

    async def test_edit_nonexistent(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        sb = LocalSandbox(str(tmp_path))
        await sb.create({})
        # edit_file tries to read the file first, which raises FileNotFoundError
        with pytest.raises(FileNotFoundError):
            await sb.edit_file("nope.txt", "a", "b")

    async def test_list_files(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        sb = LocalSandbox(str(tmp_path))
        await sb.create({})
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        (tmp_path / "subdir").mkdir()
        files = await sb.list_files(".")
        assert "a.txt" in files
        assert "b.txt" in files
        assert "subdir/" in files

    async def test_destroy_is_noop(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        sb = LocalSandbox()
        await sb.create({})
        await sb.destroy()

    async def test_execute_simple_command(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        sb = LocalSandbox(str(tmp_path))
        await sb.create({})
        result = await sb.execute("echo hello", timeout=10)
        assert result.success is True
        assert "hello" in result.output
