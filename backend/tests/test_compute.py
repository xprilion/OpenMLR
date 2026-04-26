"""Tests for the compute node ecosystem — KeyManager, WorkspaceManager,
ComputeCapabilities, SSHConnectionPool, compute tools, and routes."""

from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.asyncio

from openmlr.compute.capabilities import ComputeCapabilities, GPUInfo
from openmlr.compute.manager import ComputeManager
from openmlr.compute.workspace import WorkspaceManager
from openmlr.keys.manager import KeyManager
from openmlr.sandbox.ssh import SSHConnectionPool
from openmlr.tools.compute_tools import _validate_sync_path
from openmlr.tools.registry import MODE_TOOL_RESTRICTIONS, ToolRouter

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_keys_dir(tmp_path):
    keys_dir = tmp_path / ".keys"
    keys_dir.mkdir()
    return keys_dir


@pytest.fixture
def key_manager(tmp_keys_dir):
    return KeyManager(keys_dir=tmp_keys_dir)


@pytest.fixture
def tmp_workspace_dir(tmp_path):
    return tmp_path / ".openmlr"


@pytest.fixture
def workspace_manager(tmp_workspace_dir):
    return WorkspaceManager(base_dir=tmp_workspace_dir)


# ---------------------------------------------------------------------------
# KeyManager
# ---------------------------------------------------------------------------

class TestKeyManager:
    def test_init_creates_dir(self, tmp_keys_dir, key_manager):
        assert tmp_keys_dir.exists()
        assert oct(tmp_keys_dir.stat().st_mode)[-3:] == "700"

    def test_list_keys_empty(self, key_manager):
        assert key_manager.list_keys() == []

    def test_generate_key_pair_ed25519(self, key_manager):
        priv, pub = key_manager.generate_key_pair("id_test_ed", "ed25519", "test@host")
        assert priv.exists()
        assert pub.exists()
        assert "id_test_ed" in priv.name
        # Private key should be 0o600
        mode = oct(priv.stat().st_mode)[-3:]
        assert mode == "600"

    def test_generate_key_pair_rsa(self, key_manager):
        priv, pub = key_manager.generate_key_pair("id_test_rsa", "rsa", "test@host")
        assert priv.exists()
        assert pub.exists()

    def test_generate_unsupported_algorithm(self, key_manager):
        with pytest.raises(ValueError, match="Unsupported algorithm"):
            key_manager.generate_key_pair("id_bad", "dsa", "test")

    def test_key_exists(self, key_manager):
        key_manager.generate_key_pair("id_exist", "ed25519")
        assert key_manager.key_exists("id_exist") is True
        assert key_manager.key_exists("id_nope") is False

    def test_list_keys_after_generate(self, key_manager):
        key_manager.generate_key_pair("id_list_test", "ed25519")
        keys = key_manager.list_keys()
        assert len(keys) == 1
        assert keys[0]["filename"] == "id_list_test"
        assert keys[0]["has_public"] is True

    def test_delete_key(self, key_manager):
        key_manager.generate_key_pair("id_del", "ed25519")
        assert key_manager.key_exists("id_del")
        result = key_manager.delete_key("id_del")
        assert result is True
        assert not key_manager.key_exists("id_del")

    def test_delete_nonexistent(self, key_manager):
        result = key_manager.delete_key("nope")
        assert result is False

    def test_write_and_read_key(self, key_manager):
        key_manager.write_key("id_manual", "-----BEGIN FAKE KEY-----\ndata\n-----END FAKE KEY-----\n")
        content = key_manager.read_key("id_manual")
        assert "FAKE KEY" in content

    def test_read_nonexistent_key(self, key_manager):
        with pytest.raises(FileNotFoundError):
            key_manager.read_key("nope")

    def test_validate_key_ed25519(self, key_manager):
        key_manager.generate_key_pair("id_val", "ed25519", "comment")
        private = key_manager.read_key("id_val")
        meta = key_manager.validate_key(private)
        assert meta["algorithm"] == "ssh-ed25519"
        assert meta["fingerprint"].startswith("SHA256:")
        assert len(meta["fingerprint"]) > 10
        assert meta["public_key"].startswith("ssh-ed25519")

    def test_validate_key_rsa(self, key_manager):
        key_manager.generate_key_pair("id_val_rsa", "rsa")
        private = key_manager.read_key("id_val_rsa")
        meta = key_manager.validate_key(private)
        assert meta["algorithm"] == "ssh-rsa"
        assert meta["fingerprint"].startswith("SHA256:")

    def test_validate_invalid_key(self, key_manager):
        with pytest.raises(ValueError, match="Invalid private key"):
            key_manager.validate_key("not a key")

    def test_get_key_path(self, key_manager, tmp_keys_dir):
        path = key_manager.get_key_path("id_some")
        assert path == tmp_keys_dir / "id_some"


# ---------------------------------------------------------------------------
# WorkspaceManager
# ---------------------------------------------------------------------------

class TestWorkspaceManager:
    def test_create_workspace(self, workspace_manager):
        path = workspace_manager.create_workspace("test-uuid-123")
        assert path.exists()
        assert (path / "data").exists()
        assert (path / "models").exists()
        assert (path / "code").exists()
        assert (path / "outputs").exists()
        assert (path / ".openmlr-meta").exists()

    def test_get_workspace_path(self, workspace_manager):
        path = workspace_manager.get_workspace_path("abc")
        assert "workspace-abc" in str(path)

    def test_workspace_exists(self, workspace_manager):
        assert workspace_manager.workspace_exists("nope") is False
        workspace_manager.create_workspace("nope")
        assert workspace_manager.workspace_exists("nope") is True

    def test_delete_workspace_with_archive(self, workspace_manager):
        workspace_manager.create_workspace("del-test")
        ws_path = workspace_manager.get_workspace_path("del-test")
        (ws_path / "data" / "file.txt").write_text("hello")

        result = workspace_manager.delete_workspace("del-test", archive=True)
        assert result is True
        assert not ws_path.exists()
        # Check archive was created
        archives = list(workspace_manager.archive_dir.glob("*.tar.gz"))
        assert len(archives) == 1

    def test_delete_workspace_without_archive(self, workspace_manager):
        workspace_manager.create_workspace("del-no-archive")
        result = workspace_manager.delete_workspace("del-no-archive", archive=False)
        assert result is True
        archives = list(workspace_manager.archive_dir.glob("*.tar.gz"))
        assert len(archives) == 0

    def test_delete_nonexistent(self, workspace_manager):
        result = workspace_manager.delete_workspace("nonexistent")
        assert result is False

    def test_get_workspace_size(self, workspace_manager):
        workspace_manager.create_workspace("size-test")
        path = workspace_manager.get_workspace_path("size-test")
        (path / "data" / "big.bin").write_bytes(b"x" * 1024)
        size = workspace_manager.get_workspace_size("size-test")
        assert size >= 1024

    def test_list_workspaces(self, workspace_manager):
        workspace_manager.create_workspace("ws-a")
        workspace_manager.create_workspace("ws-b")
        ws_list = workspace_manager.list_workspaces()
        uuids = [w["uuid"] for w in ws_list]
        assert "ws-a" in uuids
        assert "ws-b" in uuids

    def test_cleanup_archives(self, workspace_manager):
        # Create and archive 3 workspaces
        for i in range(3):
            workspace_manager.create_workspace(f"cleanup-{i}")
            workspace_manager.archive_workspace(f"cleanup-{i}")

        result = workspace_manager.cleanup_archives(max_age_days=0, max_count=1)
        assert result["deleted"] >= 2
        remaining = list(workspace_manager.archive_dir.glob("*.tar.gz"))
        assert len(remaining) <= 1

    def test_cleanup_workspaces_orphaned(self, workspace_manager):
        workspace_manager.create_workspace("keep")
        workspace_manager.create_workspace("orphan")
        result = workspace_manager.cleanup_workspaces(
            conversation_uuids=["keep"],
            archive=False,
        )
        assert result["deleted"] == 1
        assert workspace_manager.workspace_exists("keep")
        assert not workspace_manager.workspace_exists("orphan")


# ---------------------------------------------------------------------------
# ComputeCapabilities
# ---------------------------------------------------------------------------

class TestComputeCapabilities:
    def test_defaults(self):
        caps = ComputeCapabilities()
        assert caps.platform == "unknown"
        assert caps.cpu_cores == 0
        assert caps.gpu_available is False
        assert caps.gpu_info == []

    def test_to_dict(self):
        caps = ComputeCapabilities(
            cpu_cores=8,
            gpu_available=True,
            gpu_info=[GPUInfo(model="A100", vram_gb=80.0, cuda_version="12.4")],
        )
        d = caps.to_dict()
        assert d["cpu_cores"] == 8
        assert d["gpu_available"] is True
        assert len(d["gpu_info"]) == 1
        assert d["gpu_info"][0]["model"] == "A100"

    def test_from_dict(self):
        d = {
            "platform": "Linux",
            "cpu_cores": 4,
            "gpu_available": True,
            "gpu_info": [{"model": "RTX 4090", "vram_gb": 24, "cuda_version": "12.4", "driver_version": "545"}],
        }
        caps = ComputeCapabilities.from_dict(d)
        assert caps.platform == "Linux"
        assert caps.cpu_cores == 4
        assert len(caps.gpu_info) == 1
        assert caps.gpu_info[0].model == "RTX 4090"

    def test_roundtrip(self):
        original = ComputeCapabilities(
            platform="test",
            cpu_cores=16,
            available_ram_gb=32.5,
            gpu_available=True,
            gpu_count=2,
            gpu_info=[
                GPUInfo(model="A100", vram_gb=80),
                GPUInfo(model="A100", vram_gb=80),
            ],
            python_versions=["3.12", "3.11"],
            docker_available=True,
        )
        d = original.to_dict()
        restored = ComputeCapabilities.from_dict(d)
        assert restored.platform == "test"
        assert restored.cpu_cores == 16
        assert restored.available_ram_gb == 32.5
        assert len(restored.gpu_info) == 2
        assert restored.docker_available is True


# ---------------------------------------------------------------------------
# ComputeManager (validation)
# ---------------------------------------------------------------------------

class TestComputeManager:
    def test_validate_ssh_missing_host(self, key_manager):
        cm = ComputeManager(key_manager)
        ok, err = cm.validate_node_config("ssh", {"username": "user"})
        assert ok is False
        assert "host" in err

    def test_validate_ssh_missing_username(self, key_manager):
        cm = ComputeManager(key_manager)
        ok, err = cm.validate_node_config("ssh", {"host": "example.com"})
        assert ok is False
        assert "username" in err

    def test_validate_ssh_ok(self, key_manager):
        cm = ComputeManager(key_manager)
        ok, err = cm.validate_node_config("ssh", {"host": "example.com", "username": "user"})
        assert ok is True

    def test_validate_ssh_missing_key(self, key_manager):
        cm = ComputeManager(key_manager)
        ok, err = cm.validate_node_config("ssh", {
            "host": "x", "username": "u", "key_filename": "nonexistent",
        })
        assert ok is False
        assert "not found" in err

    def test_validate_local_ok(self, key_manager):
        cm = ComputeManager(key_manager)
        ok, err = cm.validate_node_config("local", {})
        assert ok is True

    def test_validate_local_file_not_dir(self, key_manager, tmp_path):
        f = tmp_path / "not_a_dir"
        f.write_text("data")
        cm = ComputeManager(key_manager)
        ok, err = cm.validate_node_config("local", {"workdir": str(f)})
        assert ok is False

    def test_validate_modal_ok(self, key_manager):
        cm = ComputeManager(key_manager)
        ok, err = cm.validate_node_config("modal", {})
        assert ok is True

    def test_validate_unknown_type(self, key_manager):
        cm = ComputeManager(key_manager)
        ok, err = cm.validate_node_config("kubernetes", {})
        assert ok is False
        assert "Unknown" in err


# ---------------------------------------------------------------------------
# SSHConnectionPool
# ---------------------------------------------------------------------------

class TestSSHConnectionPool:
    def test_singleton(self):
        pool1 = SSHConnectionPool.get_pool()
        pool2 = SSHConnectionPool.get_pool()
        assert pool1 is pool2

    def test_make_key(self):
        assert SSHConnectionPool._make_key("host", 22, "user") == "user@host:22"

    def test_get_empty(self):
        pool = SSHConnectionPool(ttl_seconds=300)
        assert pool.get("host", 22, "user") is None

    def test_put_and_get(self):
        pool = SSHConnectionPool(ttl_seconds=300)
        # Mock a client with active transport
        mock_client = MagicMock()
        mock_transport = MagicMock()
        mock_transport.is_active.return_value = True
        mock_client.get_transport.return_value = mock_transport
        mock_sftp = MagicMock()

        pool.put("host", 22, "user", mock_client, mock_sftp, "fp123")
        result = pool.get("host", 22, "user")
        assert result is not None
        client, sftp, fp = result
        assert client is mock_client
        assert sftp is mock_sftp
        assert fp == "fp123"

    def test_get_dead_connection(self):
        pool = SSHConnectionPool(ttl_seconds=300)
        mock_client = MagicMock()
        mock_transport = MagicMock()
        mock_transport.is_active.return_value = False
        mock_client.get_transport.return_value = mock_transport
        mock_sftp = MagicMock()

        pool.put("host", 22, "user", mock_client, mock_sftp, "fp")
        result = pool.get("host", 22, "user")
        assert result is None

    def test_cleanup_idle(self):
        pool = SSHConnectionPool(ttl_seconds=0)  # immediate expiry
        mock_client = MagicMock()
        mock_sftp = MagicMock()
        pool.put("host", 22, "user", mock_client, mock_sftp, "fp")
        pool._last_used["user@host:22"] = 0  # force stale
        pool.cleanup_idle()
        assert pool.get("host", 22, "user") is None
        mock_sftp.close.assert_called_once()
        mock_client.close.assert_called_once()

    def test_remove(self):
        pool = SSHConnectionPool(ttl_seconds=300)
        mock_client = MagicMock()
        mock_sftp = MagicMock()
        pool.put("host", 22, "user", mock_client, mock_sftp, "fp")
        pool.remove("host", 22, "user")
        assert pool.get("host", 22, "user") is None


# ---------------------------------------------------------------------------
# Path traversal validation
# ---------------------------------------------------------------------------

class TestPathTraversal:
    def test_valid_relative_path(self, tmp_path):
        ws = tmp_path / "workspace"
        ws.mkdir()
        path, err = _validate_sync_path(ws, "data/file.txt")
        assert err is None
        assert str(ws) in str(path)

    def test_traversal_blocked(self, tmp_path):
        ws = tmp_path / "workspace"
        ws.mkdir()
        path, err = _validate_sync_path(ws, "../../etc/passwd")
        assert err is not None
        assert "escapes" in err

    def test_absolute_path_blocked(self, tmp_path):
        ws = tmp_path / "workspace"
        ws.mkdir()
        path, err = _validate_sync_path(ws, "/etc/passwd")
        assert err is not None
        assert "escapes" in err

    def test_nested_valid_path(self, tmp_path):
        ws = tmp_path / "workspace"
        ws.mkdir()
        path, err = _validate_sync_path(ws, "data/subdir/deep/file.csv")
        assert err is None


# ---------------------------------------------------------------------------
# ToolRouter compute context injection
# ---------------------------------------------------------------------------

class TestToolRouterContext:
    def test_set_context(self):
        router = ToolRouter()
        router.set_context(user_id=42, db="fake_db")
        assert router._user_id == 42
        assert router._db == "fake_db"

    async def test_context_injected_into_handler(self):
        router = ToolRouter()
        router.set_context(user_id=42, db="fake_db")

        async def handler(user_id: int = None, db=None, arg: str = "") -> tuple[str, bool]:
            return f"uid={user_id},db={db},arg={arg}", True

        from openmlr.agent.types import ToolSpec
        tool = ToolSpec(
            name="ctx_test", description="test", parameters={"type": "object", "properties": {}},
            handler=handler,
        )
        router.register(tool)
        result, ok = await router.call_tool("ctx_test", {"arg": "hello"})
        assert ok is True
        assert "uid=42" in result
        assert "db=fake_db" in result
        assert "arg=hello" in result


# ---------------------------------------------------------------------------
# Plan mode allows compute tools
# ---------------------------------------------------------------------------

class TestPlanModeComputeTools:
    def test_compute_list_allowed(self):
        assert "compute_list" in MODE_TOOL_RESTRICTIONS["plan"]["allowed"]

    def test_compute_plan_allowed(self):
        assert "compute_plan" in MODE_TOOL_RESTRICTIONS["plan"]["allowed"]

    def test_compute_probe_allowed(self):
        assert "compute_probe" in MODE_TOOL_RESTRICTIONS["plan"]["allowed"]

    def test_compute_select_not_in_plan(self):
        assert "compute_select" not in MODE_TOOL_RESTRICTIONS["plan"]["allowed"]


# ---------------------------------------------------------------------------
# Config redaction (routes/compute.py)
# ---------------------------------------------------------------------------

class TestConfigRedaction:
    def test_redact_password(self):
        from openmlr.routes.compute import _redact_config
        config = {"host": "example.com", "password": "secret123", "username": "user"}
        redacted = _redact_config(config)
        assert redacted["host"] == "example.com"
        assert redacted["password"] == "***"
        assert redacted["username"] == "user"

    def test_redact_empty_config(self):
        from openmlr.routes.compute import _redact_config
        assert _redact_config({}) == {}
        assert _redact_config(None) == {}

    def test_redact_no_sensitive_fields(self):
        from openmlr.routes.compute import _redact_config
        config = {"host": "x", "port": 22}
        assert _redact_config(config) == config


# ---------------------------------------------------------------------------
# Routes (keys + compute) — integration via httpx
# ---------------------------------------------------------------------------

class TestKeyRoutes:
    async def test_list_keys_empty(self, auth_client):
        resp = await auth_client.get("/api/keys")
        assert resp.status_code == 200
        assert resp.json()["keys"] == []

    async def test_generate_key(self, auth_client):
        resp = await auth_client.post("/api/keys", json={
            "action": "generate",
            "filename": "id_test_route",
            "algorithm": "ed25519",
            "comment": "test",
        })
        assert resp.status_code == 200
        data = resp.json()["key"]
        assert data["filename"] == "id_test_route"
        assert data["algorithm"] == "ssh-ed25519"
        assert data["fingerprint"].startswith("SHA256:")

    async def test_generate_duplicate(self, auth_client):
        await auth_client.post("/api/keys", json={
            "action": "generate", "filename": "id_dup", "algorithm": "ed25519",
        })
        resp = await auth_client.post("/api/keys", json={
            "action": "generate", "filename": "id_dup", "algorithm": "ed25519",
        })
        assert resp.status_code == 409

    async def test_delete_key(self, auth_client):
        await auth_client.post("/api/keys", json={
            "action": "generate", "filename": "id_to_del", "algorithm": "ed25519",
        })
        resp = await auth_client.delete("/api/keys/id_to_del")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    async def test_delete_nonexistent_key(self, auth_client):
        resp = await auth_client.delete("/api/keys/id_nope")
        assert resp.status_code == 404

    async def test_create_key_missing_filename(self, auth_client):
        resp = await auth_client.post("/api/keys", json={"action": "generate"})
        assert resp.status_code == 400

    async def test_create_key_invalid_action(self, auth_client):
        resp = await auth_client.post("/api/keys", json={
            "action": "nope", "filename": "id_x",
        })
        assert resp.status_code == 400

    async def test_unauthenticated_keys(self, client):
        resp = await client.get("/api/keys")
        assert resp.status_code == 401


class TestComputeNodeRoutes:
    async def test_list_empty(self, auth_client):
        resp = await auth_client.get("/api/compute/nodes")
        assert resp.status_code == 200
        assert resp.json()["nodes"] == []

    async def test_create_local_node(self, auth_client):
        resp = await auth_client.post("/api/compute/nodes", json={
            "name": "My Laptop",
            "type": "local",
            "config": {},
        })
        assert resp.status_code == 200
        node = resp.json()["node"]
        assert node["name"] == "My Laptop"
        assert node["type"] == "local"
        assert node["health_status"] == "unknown"

    async def test_create_duplicate_name(self, auth_client):
        await auth_client.post("/api/compute/nodes", json={
            "name": "Dup", "type": "local", "config": {},
        })
        resp = await auth_client.post("/api/compute/nodes", json={
            "name": "Dup", "type": "local", "config": {},
        })
        assert resp.status_code == 409

    async def test_create_invalid_type(self, auth_client):
        resp = await auth_client.post("/api/compute/nodes", json={
            "name": "Bad", "type": "kubernetes", "config": {},
        })
        assert resp.status_code == 400

    async def test_get_node(self, auth_client):
        create_resp = await auth_client.post("/api/compute/nodes", json={
            "name": "Get Test", "type": "local", "config": {},
        })
        node_id = create_resp.json()["node"]["id"]
        resp = await auth_client.get(f"/api/compute/nodes/{node_id}")
        assert resp.status_code == 200
        assert resp.json()["node"]["name"] == "Get Test"

    async def test_update_node(self, auth_client):
        create_resp = await auth_client.post("/api/compute/nodes", json={
            "name": "Update Test", "type": "local", "config": {},
        })
        node_id = create_resp.json()["node"]["id"]
        resp = await auth_client.put(f"/api/compute/nodes/{node_id}", json={
            "name": "Updated Name",
        })
        assert resp.status_code == 200
        assert resp.json()["node"]["name"] == "Updated Name"

    async def test_delete_node(self, auth_client):
        create_resp = await auth_client.post("/api/compute/nodes", json={
            "name": "Delete Test", "type": "local", "config": {},
        })
        node_id = create_resp.json()["node"]["id"]
        resp = await auth_client.delete(f"/api/compute/nodes/{node_id}")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    async def test_set_default(self, auth_client):
        create_resp = await auth_client.post("/api/compute/nodes", json={
            "name": "Default Test", "type": "local", "config": {},
        })
        node_id = create_resp.json()["node"]["id"]
        resp = await auth_client.post(f"/api/compute/nodes/{node_id}/set-default")
        assert resp.status_code == 200

        # Verify it's now default
        get_resp = await auth_client.get(f"/api/compute/nodes/{node_id}")
        assert get_resp.json()["node"]["is_default"] is True

    async def test_config_redacted_in_response(self, auth_client):
        resp = await auth_client.post("/api/compute/nodes", json={
            "name": "Redact Test",
            "type": "ssh",
            "config": {"host": "x", "username": "u", "password": "secret"},
        })
        assert resp.status_code == 200
        node = resp.json()["node"]
        assert node["config"]["password"] == "***"
        assert node["config"]["host"] == "x"

    async def test_test_local_node(self, auth_client):
        create_resp = await auth_client.post("/api/compute/nodes", json={
            "name": "Test Local", "type": "local", "config": {},
        })
        node_id = create_resp.json()["node"]["id"]
        resp = await auth_client.post(f"/api/compute/nodes/{node_id}/test")
        assert resp.status_code == 200
        # Local test should pass (workspace will be CWD)
        assert resp.json()["ok"] is True

    async def test_test_config_endpoint(self, auth_client):
        resp = await auth_client.post("/api/compute/test", json={
            "type": "local",
            "config": {},
        })
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    async def test_test_config_invalid_type(self, auth_client):
        resp = await auth_client.post("/api/compute/test", json={
            "type": "kubernetes",
            "config": {},
        })
        assert resp.status_code == 200
        assert resp.json()["ok"] is False

    async def test_unauthenticated(self, client):
        resp = await client.get("/api/compute/nodes")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# System prompt includes compute_env
# ---------------------------------------------------------------------------

class TestSystemPromptCompute:
    def test_prompt_includes_compute_env(self):
        from openmlr.agent.prompts import build_system_prompt
        prompt = build_system_prompt(
            tool_specs=[],
            compute_env="## Active Compute: TestNode (ssh)\n- CPU: 8 cores",
        )
        assert "TestNode" in prompt
        assert "8 cores" in prompt

    def test_prompt_without_compute_env(self):
        from openmlr.agent.prompts import build_system_prompt
        prompt = build_system_prompt(tool_specs=[], compute_env="")
        assert "Active Compute" not in prompt
